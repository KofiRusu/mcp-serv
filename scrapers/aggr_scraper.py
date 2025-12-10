#!/usr/bin/env python3
"""
AGGR Agent Scraper - Real-time Aggregated Trades
Connects to Binance WebSocket for live trade aggregation.
Similar to aggr.trade functionality.
"""

import asyncio
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from collections import deque
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('AGGRAgent')

# Try to import websockets
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    logger.warning("websockets not available, install with: pip install websockets")
    WEBSOCKETS_AVAILABLE = False

# Configuration
OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', '/home/kr/ChatOS-v2.0/sandbox-ui/data/aggr'))
INTERVAL = int(os.environ.get('INTERVAL_SECONDS', 1))  # Aggregate every 1 second
SYMBOLS = os.environ.get('SYMBOLS', 'BTCUSDT,ETHUSDT,SOLUSDT').split(',')

# Binance WebSocket endpoints
BINANCE_WS_BASE = 'wss://fstream.binance.com/ws'
BINANCE_WS_COMBINED = 'wss://fstream.binance.com/stream'


class TradeAggregator:
    """Aggregates trades over time windows for visualization."""
    
    def __init__(self, symbol: str, window_seconds: int = 1):
        self.symbol = symbol
        self.window_seconds = window_seconds
        self.current_window: List[Dict] = []
        self.window_start = time.time()
        self.aggregated_history = deque(maxlen=1000)  # Keep last 1000 aggregations
        
        # Running stats
        self.total_buy_volume = 0.0
        self.total_sell_volume = 0.0
        self.total_buy_count = 0
        self.total_sell_count = 0
        self.large_trades: List[Dict] = []  # Trades > threshold
        
    def add_trade(self, trade: Dict) -> Optional[Dict]:
        """Add a trade and return aggregation if window complete."""
        self.current_window.append(trade)
        
        # Check if window is complete
        current_time = time.time()
        if current_time - self.window_start >= self.window_seconds:
            aggregation = self._aggregate_window()
            self._reset_window()
            return aggregation
        return None
    
    def _aggregate_window(self) -> Dict:
        """Aggregate all trades in the current window."""
        if not self.current_window:
            return self._empty_aggregation()
        
        buys = [t for t in self.current_window if t['side'] == 'buy']
        sells = [t for t in self.current_window if t['side'] == 'sell']
        
        buy_volume = sum(t['quantity'] for t in buys)
        sell_volume = sum(t['quantity'] for t in sells)
        buy_value = sum(t['quantity'] * t['price'] for t in buys)
        sell_value = sum(t['quantity'] * t['price'] for t in sells)
        
        # Update running totals
        self.total_buy_volume += buy_volume
        self.total_sell_volume += sell_volume
        self.total_buy_count += len(buys)
        self.total_sell_count += len(sells)
        
        # Calculate VWAP
        total_value = buy_value + sell_value
        total_volume = buy_volume + sell_volume
        vwap = total_value / total_volume if total_volume > 0 else 0
        
        # Detect large trades (whales)
        large_threshold_usd = 100000  # $100k
        large_trades_in_window = [
            t for t in self.current_window 
            if t['quantity'] * t['price'] >= large_threshold_usd
        ]
        self.large_trades.extend(large_trades_in_window)
        self.large_trades = self.large_trades[-50:]  # Keep last 50
        
        # Price range
        prices = [t['price'] for t in self.current_window]
        
        aggregation = {
            'symbol': self.symbol,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'window_ms': self.window_seconds * 1000,
            
            # Volume data
            'buy_volume': round(buy_volume, 6),
            'sell_volume': round(sell_volume, 6),
            'total_volume': round(total_volume, 6),
            'buy_value_usd': round(buy_value, 2),
            'sell_value_usd': round(sell_value, 2),
            
            # Trade counts
            'buy_count': len(buys),
            'sell_count': len(sells),
            'total_count': len(self.current_window),
            
            # Price data
            'vwap': round(vwap, 2),
            'high': round(max(prices), 2),
            'low': round(min(prices), 2),
            'open': round(self.current_window[0]['price'], 2),
            'close': round(self.current_window[-1]['price'], 2),
            
            # Delta (buy pressure vs sell pressure)
            'delta': round(buy_volume - sell_volume, 6),
            'delta_pct': round((buy_volume - sell_volume) / total_volume * 100, 2) if total_volume > 0 else 0,
            
            # CVD (Cumulative Volume Delta) - running total
            'cvd': round(self.total_buy_volume - self.total_sell_volume, 6),
            
            # Large trades in this window
            'large_trade_count': len(large_trades_in_window),
            'large_trade_value': round(sum(t['quantity'] * t['price'] for t in large_trades_in_window), 2),
        }
        
        self.aggregated_history.append(aggregation)
        return aggregation
    
    def _empty_aggregation(self) -> Dict:
        """Return empty aggregation when no trades."""
        return {
            'symbol': self.symbol,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'window_ms': self.window_seconds * 1000,
            'buy_volume': 0, 'sell_volume': 0, 'total_volume': 0,
            'buy_value_usd': 0, 'sell_value_usd': 0,
            'buy_count': 0, 'sell_count': 0, 'total_count': 0,
            'vwap': 0, 'high': 0, 'low': 0, 'open': 0, 'close': 0,
            'delta': 0, 'delta_pct': 0, 'cvd': round(self.total_buy_volume - self.total_sell_volume, 6),
            'large_trade_count': 0, 'large_trade_value': 0,
        }
    
    def _reset_window(self):
        """Reset the current window."""
        self.current_window = []
        self.window_start = time.time()
    
    def get_stats(self) -> Dict:
        """Get overall statistics."""
        return {
            'symbol': self.symbol,
            'total_buy_volume': round(self.total_buy_volume, 6),
            'total_sell_volume': round(self.total_sell_volume, 6),
            'total_buy_count': self.total_buy_count,
            'total_sell_count': self.total_sell_count,
            'cvd': round(self.total_buy_volume - self.total_sell_volume, 6),
            'buy_sell_ratio': round(self.total_buy_volume / self.total_sell_volume, 3) if self.total_sell_volume > 0 else 0,
            'recent_large_trades': self.large_trades[-10:],
        }


class AGGRScraper:
    """Real-time aggregated trade scraper using Binance WebSocket."""
    
    def __init__(self, symbols: List[str]):
        self.symbols = [s.lower() for s in symbols]
        self.aggregators: Dict[str, TradeAggregator] = {
            s.upper(): TradeAggregator(s.upper(), window_seconds=1)
            for s in symbols
        }
        self.running = False
        self.websocket = None
        
    async def connect(self):
        """Connect to Binance WebSocket."""
        if not WEBSOCKETS_AVAILABLE:
            logger.error("websockets library not available")
            return False
        
        # Build combined stream URL
        streams = '/'.join([f'{s}@aggTrade' for s in self.symbols])
        url = f'{BINANCE_WS_COMBINED}?streams={streams}'
        
        try:
            self.websocket = await websockets.connect(url, ping_interval=30)
            logger.info(f"Connected to Binance WebSocket for {len(self.symbols)} symbols")
            return True
        except Exception as e:
            logger.error(f"Failed to connect: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
    
    def parse_trade(self, data: Dict) -> Dict:
        """Parse Binance aggTrade message."""
        return {
            'symbol': data['s'],
            'price': float(data['p']),
            'quantity': float(data['q']),
            'timestamp': data['T'],
            'side': 'sell' if data['m'] else 'buy',  # m = maker is buyer
            'trade_id': data['a'],
        }
    
    async def save_aggregation(self, agg: Dict):
        """Save aggregation to file."""
        symbol = agg['symbol']
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        dir_path = OUTPUT_DIR / date_str / symbol
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Append to daily file
        file_path = dir_path / 'aggr.json'
        
        existing = []
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    existing = json.load(f)
            except:
                existing = []
        
        existing.append(agg)
        existing = existing[-3600:]  # Keep last hour at 1s intervals
        
        with open(file_path, 'w') as f:
            json.dump(existing, f)
        
        # Also save latest for quick access
        latest_path = OUTPUT_DIR / 'latest' / f'{symbol}.json'
        latest_path.parent.mkdir(parents=True, exist_ok=True)
        with open(latest_path, 'w') as f:
            json.dump(agg, f, indent=2)
    
    async def save_stats(self):
        """Save overall statistics."""
        stats = {s: agg.get_stats() for s, agg in self.aggregators.items()}
        stats_path = OUTPUT_DIR / 'stats.json'
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
        with open(stats_path, 'w') as f:
            json.dump({
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'symbols': stats,
            }, f, indent=2)
    
    async def run(self):
        """Run the scraper."""
        self.running = True
        logger.info(f"Starting AGGR Agent for symbols: {self.symbols}")
        
        while self.running:
            try:
                connected = await self.connect()
                if not connected:
                    logger.warning("Connection failed, retrying in 5s...")
                    await asyncio.sleep(5)
                    continue
                
                async for message in self.websocket:
                    if not self.running:
                        break
                    
                    try:
                        data = json.loads(message)
                        
                        # Handle combined stream format
                        if 'stream' in data:
                            trade_data = data['data']
                        else:
                            trade_data = data
                        
                        trade = self.parse_trade(trade_data)
                        symbol = trade['symbol']
                        
                        if symbol in self.aggregators:
                            agg = self.aggregators[symbol].add_trade(trade)
                            
                            if agg:
                                await self.save_aggregation(agg)
                                logger.debug(f"{symbol}: Vol={agg['total_volume']:.4f} Delta={agg['delta_pct']:+.1f}%")
                        
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("WebSocket connection closed, reconnecting...")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                await asyncio.sleep(5)
            finally:
                await self.disconnect()
        
        logger.info("AGGR Agent stopped")
    
    async def run_with_stats(self):
        """Run with periodic stats saving."""
        stats_task = asyncio.create_task(self._stats_loop())
        try:
            await self.run()
        finally:
            stats_task.cancel()
    
    async def _stats_loop(self):
        """Periodically save stats."""
        while True:
            await asyncio.sleep(60)  # Every minute
            await self.save_stats()
            logger.info("Saved AGGR stats")
    
    def stop(self):
        """Stop the scraper."""
        self.running = False


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Starting AGGR Agent Scraper")
    logger.info(f"Symbols: {SYMBOLS}")
    logger.info(f"Output: {OUTPUT_DIR}")
    logger.info("=" * 60)
    
    scraper = AGGRScraper(SYMBOLS)
    
    try:
        await scraper.run_with_stats()
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
        scraper.stop()


if __name__ == '__main__':
    asyncio.run(main())

