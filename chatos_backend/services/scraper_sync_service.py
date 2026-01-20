#!/usr/bin/env python3
"""
scraper_sync_service.py - Continuous Scraper Data Synchronization

Watches all scraper output directories and continuously syncs
new data to the RealtimeDataStore for instant model access.

Ported from ChatOS v2.1 with adaptations for v2.2 architecture and macOS compatibility.

This service should run 24/7 alongside the scrapers to ensure
the data store always has the latest information.

Usage:
    python -m chatos_backend.services.scraper_sync_service
    
    # Or started via FastAPI lifespan
"""

import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class SyncConfig:
    """Configuration for scraper sync service."""
    
    scraped_data_dir: str = field(default_factory=lambda: os.environ.get(
        "SCRAPED_DATA_DIR",
        str(Path.home() / "ChatOS-Data" / "scraped")
    ))
    
    aggr_sync_interval: int = 5
    market_sync_interval: int = 30
    news_sync_interval: int = 60
    sentiment_sync_interval: int = 60
    derivatives_sync_interval: int = 30
    
    max_file_age_hours: int = 24
    processed_files_cache: str = field(default_factory=lambda: str(
        Path.home() / "ChatOS-Data" / "cache" / "processed_files.json"
    ))


class FileWatcher:
    """Watches directories for new/modified files."""
    
    def __init__(self, config: SyncConfig):
        self.config = config
        self._processed_files: Dict[str, float] = {}
        self._load_processed_cache()
    
    def _load_processed_cache(self):
        """Load cache of already processed files."""
        cache_path = Path(self.config.processed_files_cache)
        if cache_path.exists():
            try:
                with open(cache_path, 'r') as f:
                    self._processed_files = json.load(f)
            except Exception:
                self._processed_files = {}
    
    def _save_processed_cache(self):
        """Save processed files cache."""
        cache_path = Path(self.config.processed_files_cache)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        
        cutoff = time.time() - (self.config.max_file_age_hours * 3600)
        self._processed_files = {
            k: v for k, v in self._processed_files.items()
            if v > cutoff
        }
        
        try:
            with open(cache_path, 'w') as f:
                json.dump(self._processed_files, f)
        except Exception as e:
            logger.warning(f"Failed to save processed cache: {e}")
    
    def get_new_files(self, directory: Path, pattern: str = "*.json") -> List[Path]:
        """Get files that haven't been processed or have been modified."""
        if not directory.exists():
            return []
        
        new_files = []
        for file_path in directory.glob(pattern):
            file_key = str(file_path)
            try:
                mtime = file_path.stat().st_mtime
            except OSError:
                continue
            
            if file_key not in self._processed_files or mtime > self._processed_files[file_key]:
                new_files.append(file_path)
        
        return sorted(new_files, key=lambda f: f.stat().st_mtime, reverse=True)
    
    def mark_processed(self, file_path: Path):
        """Mark a file as processed."""
        self._processed_files[str(file_path)] = time.time()


class ScraperDataSyncer:
    """Syncs data from various scrapers to RealtimeDataStore."""
    
    def __init__(self, config: Optional[SyncConfig] = None):
        self.config = config or SyncConfig()
        self.file_watcher = FileWatcher(self.config)
        self._running = False
        self._store = None
        self._event_bus = None
    
    @property
    def store(self):
        if self._store is None:
            from chatos_backend.services.realtime_data_store import get_realtime_store
            self._store = get_realtime_store()
        return self._store
    
    @property
    def event_bus(self):
        if self._event_bus is None:
            from chatos_backend.core.event_bus import get_event_bus
            self._event_bus = get_event_bus()
        return self._event_bus
    
    async def sync_aggr_trades(self):
        """Sync aggr.trade real-time data from AGGR scraper output."""
        data_dir = Path(self.config.scraped_data_dir)
        aggr_dir = data_dir / "aggr"
        
        if not aggr_dir.exists():
            return
        
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        today_dir = aggr_dir / today
        
        if not today_dir.exists():
            latest_file = aggr_dir / "latest.json"
            if latest_file.exists():
                await self._process_aggr_file(latest_file)
            return
        
        new_files = self.file_watcher.get_new_files(today_dir, "*.json")[:5]
        
        for file_path in new_files:
            await self._process_aggr_file(file_path)
            self.file_watcher.mark_processed(file_path)
    
    async def _process_aggr_file(self, file_path: Path):
        """Process an AGGR data file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                for item in data[-100:]:
                    await self._add_trade(item)
            elif isinstance(data, dict):
                if 'aggregations' in data:
                    for agg in data['aggregations'][-20:]:
                        await self._process_aggregation(agg)
                else:
                    await self._add_trade(data)
                    
        except Exception as e:
            logger.error(f"Error processing aggr file {file_path}: {e}")
    
    async def _add_trade(self, trade_data: dict):
        """Add a trade to the store."""
        from chatos_backend.services.realtime_data_store import TradeData
        
        try:
            trade = TradeData(
                symbol=trade_data.get('symbol', 'BTCUSDT'),
                price=float(trade_data.get('price', 0)),
                amount=float(trade_data.get('quantity', trade_data.get('amount', 0))),
                side=trade_data.get('side', 'buy'),
                timestamp=trade_data.get('timestamp', datetime.now(timezone.utc).isoformat()),
            )
            self.store.add_trade(trade)
            
            self.event_bus.publish_sync(
                "market.trade",
                {"symbol": trade.symbol, "price": trade.price, "side": trade.side, "amount": trade.amount},
                source="scraper_sync"
            )
        except Exception as e:
            logger.debug(f"Error adding trade: {e}")
    
    async def _process_aggregation(self, agg: dict):
        """Process an aggregation window."""
        symbol = agg.get('symbol', 'BTCUSDT')
        
        delta = agg.get('delta', 0)
        cvd = agg.get('cvd', 0)
        
        self.event_bus.publish_sync(
            "market.aggregation",
            {
                "symbol": symbol,
                "buy_volume": agg.get('buy_volume', 0),
                "sell_volume": agg.get('sell_volume', 0),
                "delta": delta,
                "cvd": cvd,
                "vwap": agg.get('vwap', 0),
                "large_trade_count": agg.get('large_trade_count', 0),
            },
            source="scraper_sync"
        )
    
    async def sync_market_data(self):
        """Sync market data from market scraper output."""
        data_dir = Path(self.config.scraped_data_dir)
        market_dir = data_dir / "market"
        
        if not market_dir.exists():
            return
        
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        today_dir = market_dir / today
        
        if not today_dir.exists():
            latest_file = market_dir / "latest.json"
            if latest_file.exists():
                await self._process_market_file(latest_file)
            return
        
        for symbol_dir in today_dir.iterdir():
            if not symbol_dir.is_dir():
                continue
            
            symbol = symbol_dir.name
            await self._sync_symbol_market_data(symbol, symbol_dir)
    
    async def _process_market_file(self, file_path: Path):
        """Process a market data file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                for symbol, ticker_data in data.items():
                    if isinstance(ticker_data, dict):
                        await self._update_ticker(symbol, ticker_data)
        except Exception as e:
            logger.error(f"Error processing market file {file_path}: {e}")
    
    async def _sync_symbol_market_data(self, symbol: str, symbol_dir: Path):
        """Sync market data for a specific symbol."""
        from chatos_backend.services.realtime_data_store import MarketTicker
        
        ticker_file = symbol_dir / "tickers.json"
        if ticker_file.exists():
            try:
                with open(ticker_file, 'r') as f:
                    tickers = json.load(f)
                
                if tickers and isinstance(tickers, list):
                    latest = tickers[-1]
                    await self._update_ticker(symbol, latest)
            except Exception as e:
                logger.error(f"Error loading ticker for {symbol}: {e}")
    
    async def _update_ticker(self, symbol: str, data: dict):
        """Update a ticker in the store."""
        from chatos_backend.services.realtime_data_store import MarketTicker
        
        try:
            ticker = MarketTicker(
                symbol=symbol,
                price=float(data.get('last', data.get('price', 0))),
                change_24h=float(data.get('percentage', data.get('change', data.get('change_24h', 0)))),
                volume_24h=float(data.get('volume', data.get('volume_24h', 0))),
                timestamp=data.get('timestamp', datetime.now(timezone.utc).isoformat()),
            )
            self.store.update_ticker(ticker)
            
            self.event_bus.publish_sync(
                "market.tick",
                {"symbol": symbol, "price": ticker.price, "change_24h": ticker.change_24h},
                source="scraper_sync"
            )
        except Exception as e:
            logger.debug(f"Error updating ticker {symbol}: {e}")
    
    async def sync_news(self):
        """Sync news data from news scraper output."""
        data_dir = Path(self.config.scraped_data_dir)
        news_dir = data_dir / "news"
        
        if not news_dir.exists():
            return
        
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        news_file = news_dir / f"{today}.json"
        
        if not news_file.exists():
            news_file = news_dir / "latest.json"
        
        if not news_file.exists():
            return
        
        try:
            with open(news_file, 'r') as f:
                news_data = json.load(f)
            
            from chatos_backend.services.realtime_data_store import NewsItem
            
            items = news_data if isinstance(news_data, list) else news_data.get('items', [])
            
            for item in items[-30:]:
                try:
                    news_item = NewsItem(
                        id=str(item.get('id', hash(item.get('title', '')))),
                        title=item.get('title', ''),
                        content=item.get('content'),
                        source=item.get('source', 'unknown'),
                        url=item.get('url'),
                        timestamp=item.get('timestamp', datetime.now(timezone.utc).isoformat()),
                        symbols=item.get('symbols', []),
                        sentiment=item.get('sentiment', 'neutral'),
                    )
                    self.store.add_news(news_item)
                except Exception as e:
                    logger.debug(f"Error adding news item: {e}")
            
            logger.debug(f"Synced {len(items)} news items")
        except Exception as e:
            logger.error(f"Error syncing news: {e}")
    
    async def sync_sentiment(self):
        """Sync sentiment data from sentiment scraper output."""
        data_dir = Path(self.config.scraped_data_dir)
        sentiment_file = data_dir / "sentiment" / "latest.json"
        
        if not sentiment_file.exists():
            return
        
        try:
            with open(sentiment_file, 'r') as f:
                data = json.load(f)
            
            from chatos_backend.services.realtime_data_store import SentimentData
            
            value = float(data.get('fear_greed_index', data.get('value', 50)))
            sentiment = SentimentData.from_value(value)
            self.store.update_sentiment(sentiment)
            
            self.event_bus.publish_sync(
                "market.sentiment",
                {"value": value, "label": sentiment.label},
                source="scraper_sync"
            )
            
            logger.debug(f"Synced sentiment: {value:.0f} ({sentiment.label})")
        except Exception as e:
            logger.error(f"Error syncing sentiment: {e}")
    
    async def sync_derivatives(self):
        """Sync derivatives data from CoinGlass scraper output."""
        data_dir = Path(self.config.scraped_data_dir)
        derivatives_dir = data_dir / "coinglass"
        
        if not derivatives_dir.exists():
            return
        
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        today_dir = derivatives_dir / today
        
        if not today_dir.exists():
            latest_file = derivatives_dir / "latest.json"
            if latest_file.exists():
                await self._process_derivatives_file(latest_file)
            return
        
        new_files = self.file_watcher.get_new_files(today_dir, "*.json")[:5]
        
        for file_path in new_files:
            await self._process_derivatives_file(file_path)
            self.file_watcher.mark_processed(file_path)
    
    async def _process_derivatives_file(self, file_path: Path):
        """Process a derivatives data file."""
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            if 'open_interest' in data:
                for symbol, oi_data in data['open_interest'].items():
                    self.event_bus.publish_sync(
                        "market.oi_update",
                        {"symbol": symbol, "oi": oi_data.get('open_interest', 0)},
                        source="scraper_sync"
                    )
            
            if 'liquidations' in data:
                liq_data = data['liquidations']
                if isinstance(liq_data, dict):
                    for symbol, liq in liq_data.items():
                        if isinstance(liq, dict):
                            self.event_bus.publish_sync(
                                "market.liquidation",
                                {
                                    "symbol": symbol,
                                    "long_liquidations": liq.get('long', 0),
                                    "short_liquidations": liq.get('short', 0),
                                },
                                source="scraper_sync"
                            )
            
            if 'funding_rates' in data:
                for symbol, rate in data['funding_rates'].items():
                    self.event_bus.publish_sync(
                        "market.funding",
                        {"symbol": symbol, "rate": rate},
                        source="scraper_sync"
                    )
                    
        except Exception as e:
            logger.error(f"Error processing derivatives file {file_path}: {e}")
    
    async def sync_loop(self):
        """Main sync loop - runs all sync tasks on their intervals."""
        logger.info("Starting sync loop...")
        
        last_aggr_sync = 0
        last_market_sync = 0
        last_news_sync = 0
        last_sentiment_sync = 0
        last_derivatives_sync = 0
        
        while self._running:
            now = time.time()
            
            try:
                if now - last_aggr_sync >= self.config.aggr_sync_interval:
                    await self.sync_aggr_trades()
                    last_aggr_sync = now
                
                if now - last_market_sync >= self.config.market_sync_interval:
                    await self.sync_market_data()
                    last_market_sync = now
                
                if now - last_news_sync >= self.config.news_sync_interval:
                    await self.sync_news()
                    last_news_sync = now
                
                if now - last_sentiment_sync >= self.config.sentiment_sync_interval:
                    await self.sync_sentiment()
                    last_sentiment_sync = now
                
                if now - last_derivatives_sync >= self.config.derivatives_sync_interval:
                    await self.sync_derivatives()
                    last_derivatives_sync = now
                
                self.file_watcher._save_processed_cache()
                
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
            
            await asyncio.sleep(1)
    
    async def run(self):
        """Start the sync service."""
        self._running = True
        logger.info("ScraperSyncService started")
        
        logger.info("Running initial sync...")
        await self.sync_market_data()
        await self.sync_news()
        await self.sync_sentiment()
        await self.sync_aggr_trades()
        await self.sync_derivatives()
        logger.info("Initial sync complete")
        
        await self.sync_loop()
    
    def stop(self):
        """Stop the sync service."""
        self._running = False
        self.file_watcher._save_processed_cache()
        logger.info("ScraperSyncService stopped")


_syncer: Optional[ScraperDataSyncer] = None
_sync_task: Optional[asyncio.Task] = None


def get_syncer() -> ScraperDataSyncer:
    """Get the scraper syncer singleton."""
    global _syncer
    if _syncer is None:
        _syncer = ScraperDataSyncer()
    return _syncer


async def start_scraper_sync():
    """Start the scraper sync service as a background task."""
    global _sync_task
    syncer = get_syncer()
    _sync_task = asyncio.create_task(syncer.run())
    return _sync_task


async def stop_scraper_sync():
    """Stop the scraper sync service."""
    global _syncer, _sync_task
    if _syncer:
        _syncer.stop()
    if _sync_task:
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass
    _syncer = None
    _sync_task = None


async def main():
    """Main entry point."""
    syncer = ScraperDataSyncer()
    
    def shutdown_handler(signum, frame):
        logger.info("Shutdown signal received")
        syncer.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    logger.info("=" * 60)
    logger.info("Scraper Sync Service")
    logger.info("=" * 60)
    logger.info(f"Data directory: {syncer.config.scraped_data_dir}")
    logger.info(f"Sync intervals: aggr={syncer.config.aggr_sync_interval}s, market={syncer.config.market_sync_interval}s")
    logger.info("=" * 60)
    
    try:
        await syncer.run()
    except KeyboardInterrupt:
        syncer.stop()


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    asyncio.run(main())
