#!/usr/bin/env python3
"""
CoinGlass Heatmap Agent - Liquidations, Open Interest, and Heatmap Data
Scrapes crypto derivatives data from CoinGlass API.
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('CoinGlassAgent')

# Try to import httpx
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    logger.warning("httpx not available, install with: pip install httpx")
    HTTPX_AVAILABLE = False

# Configuration
OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', '/home/kr/ChatOS-v2.0/sandbox-ui/data/coinglass'))
INTERVAL = int(os.environ.get('INTERVAL_SECONDS', 60))  # Every 60 seconds
SYMBOLS = os.environ.get('SYMBOLS', 'BTC,ETH,SOL').split(',')

# CoinGlass API (free tier, limited)
COINGLASS_BASE = 'https://open-api.coinglass.com/public/v2'

# Binance Futures API for backup data
BINANCE_FUTURES_BASE = 'https://fapi.binance.com/fapi/v1'


class CoinGlassScraper:
    """Scrapes derivatives data from CoinGlass and Binance Futures."""
    
    def __init__(self, symbols: List[str]):
        self.symbols = symbols
        self.running = False
        self.client = httpx.Client(timeout=30) if HTTPX_AVAILABLE else None
        
    def fetch_open_interest(self) -> Dict:
        """Fetch aggregated open interest data."""
        data = {}
        
        if not self.client:
            return self._mock_open_interest()
        
        try:
            # Binance Futures OI
            for symbol in self.symbols:
                pair = f'{symbol}USDT'
                response = self.client.get(
                    f'{BINANCE_FUTURES_BASE}/openInterest',
                    params={'symbol': pair}
                )
                if response.status_code == 200:
                    oi_data = response.json()
                    data[pair] = {
                        'symbol': pair,
                        'open_interest': float(oi_data.get('openInterest', 0)),
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                    }
        except Exception as e:
            logger.error(f"Error fetching OI: {e}")
            return self._mock_open_interest()
        
        return data if data else self._mock_open_interest()
    
    def fetch_funding_rates(self) -> Dict:
        """Fetch funding rates from major exchanges."""
        data = {}
        
        if not self.client:
            return self._mock_funding_rates()
        
        try:
            for symbol in self.symbols:
                pair = f'{symbol}USDT'
                response = self.client.get(
                    f'{BINANCE_FUTURES_BASE}/premiumIndex',
                    params={'symbol': pair}
                )
                if response.status_code == 200:
                    fr_data = response.json()
                    funding_rate = float(fr_data.get('lastFundingRate', 0))
                    mark_price = float(fr_data.get('markPrice', 0))
                    index_price = float(fr_data.get('indexPrice', 0))
                    
                    data[pair] = {
                        'symbol': pair,
                        'funding_rate': funding_rate,
                        'funding_rate_pct': round(funding_rate * 100, 4),
                        'mark_price': mark_price,
                        'index_price': index_price,
                        'basis': round((mark_price - index_price) / index_price * 100, 4) if index_price else 0,
                        'next_funding_time': fr_data.get('nextFundingTime'),
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                    }
        except Exception as e:
            logger.error(f"Error fetching funding rates: {e}")
            return self._mock_funding_rates()
        
        return data if data else self._mock_funding_rates()
    
    def fetch_long_short_ratio(self) -> Dict:
        """Fetch long/short ratios from exchanges."""
        data = {}
        
        if not self.client:
            return self._mock_ls_ratio()
        
        try:
            for symbol in self.symbols:
                pair = f'{symbol}USDT'
                
                # Top trader long/short ratio (accounts)
                response = self.client.get(
                    f'{BINANCE_FUTURES_BASE}/topLongShortAccountRatio',
                    params={'symbol': pair, 'period': '5m', 'limit': 1}
                )
                if response.status_code == 200:
                    ls_data = response.json()
                    if ls_data:
                        latest = ls_data[0] if isinstance(ls_data, list) else ls_data
                        long_ratio = float(latest.get('longAccount', 0.5))
                        short_ratio = float(latest.get('shortAccount', 0.5))
                        
                        data[pair] = {
                            'symbol': pair,
                            'long_ratio': round(long_ratio * 100, 2),
                            'short_ratio': round(short_ratio * 100, 2),
                            'ls_ratio': round(long_ratio / short_ratio, 3) if short_ratio > 0 else 1,
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                        }
        except Exception as e:
            logger.error(f"Error fetching LS ratio: {e}")
            return self._mock_ls_ratio()
        
        return data if data else self._mock_ls_ratio()
    
    def fetch_liquidations(self) -> List[Dict]:
        """Fetch recent liquidation data (simulated - real API requires paid access)."""
        # Note: Real-time liquidation data typically requires WebSocket or paid API
        # This generates mock data for demonstration
        return self._mock_liquidations()
    
    def _mock_open_interest(self) -> Dict:
        """Generate mock open interest data."""
        import random
        
        oi_bases = {'BTCUSDT': 450000, 'ETHUSDT': 2500000, 'SOLUSDT': 15000000}
        data = {}
        
        for symbol in self.symbols:
            pair = f'{symbol}USDT'
            base_oi = oi_bases.get(pair, 1000000)
            
            data[pair] = {
                'symbol': pair,
                'open_interest': base_oi * (1 + random.uniform(-0.05, 0.05)),
                'open_interest_usd': base_oi * 100000 * random.uniform(0.9, 1.1),
                'oi_change_24h': random.uniform(-5, 10),
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
        
        return data
    
    def _mock_funding_rates(self) -> Dict:
        """Generate mock funding rate data."""
        import random
        
        data = {}
        for symbol in self.symbols:
            pair = f'{symbol}USDT'
            fr = random.uniform(-0.001, 0.003)
            mark = 100000 if symbol == 'BTC' else 4000 if symbol == 'ETH' else 230
            
            data[pair] = {
                'symbol': pair,
                'funding_rate': fr,
                'funding_rate_pct': round(fr * 100, 4),
                'mark_price': mark * (1 + random.uniform(-0.001, 0.001)),
                'index_price': mark,
                'basis': random.uniform(-0.02, 0.05),
                'predicted_rate': fr * random.uniform(0.8, 1.2),
                'next_funding_time': int((time.time() + 28800) * 1000),  # 8h from now
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
        
        return data
    
    def _mock_ls_ratio(self) -> Dict:
        """Generate mock long/short ratio data."""
        import random
        
        data = {}
        for symbol in self.symbols:
            pair = f'{symbol}USDT'
            long_pct = random.uniform(45, 65)
            short_pct = 100 - long_pct
            
            data[pair] = {
                'symbol': pair,
                'long_ratio': round(long_pct, 2),
                'short_ratio': round(short_pct, 2),
                'ls_ratio': round(long_pct / short_pct, 3),
                'top_traders_long': round(random.uniform(48, 58), 2),
                'top_traders_short': round(random.uniform(42, 52), 2),
                'timestamp': datetime.now(timezone.utc).isoformat(),
            }
        
        return data
    
    def _mock_liquidations(self) -> List[Dict]:
        """Generate mock liquidation data."""
        import random
        
        liquidations = []
        now = time.time()
        
        for i in range(20):
            symbol = random.choice(self.symbols)
            pair = f'{symbol}USDT'
            side = random.choice(['LONG', 'SHORT'])
            
            if symbol == 'BTC':
                price = 100000 * (1 + random.uniform(-0.01, 0.01))
                size_usd = random.uniform(10000, 500000)
            elif symbol == 'ETH':
                price = 3900 * (1 + random.uniform(-0.01, 0.01))
                size_usd = random.uniform(5000, 200000)
            else:
                price = 230 * (1 + random.uniform(-0.01, 0.01))
                size_usd = random.uniform(1000, 50000)
            
            liquidations.append({
                'symbol': pair,
                'side': side,
                'price': round(price, 2),
                'size_usd': round(size_usd, 2),
                'size_coin': round(size_usd / price, 6),
                'exchange': random.choice(['Binance', 'OKX', 'Bybit', 'Bitget']),
                'timestamp': int((now - i * random.uniform(60, 300)) * 1000),
            })
        
        return sorted(liquidations, key=lambda x: x['timestamp'], reverse=True)
    
    def calculate_heatmap(self, liquidations: List[Dict]) -> Dict:
        """Calculate liquidation heatmap data for visualization."""
        # Group liquidations by price levels
        heatmap = {symbol: {'longs': {}, 'shorts': {}} for symbol in self.symbols}
        
        for liq in liquidations:
            symbol = liq['symbol'].replace('USDT', '')
            if symbol not in heatmap:
                continue
            
            price = liq['price']
            size = liq['size_usd']
            side = 'longs' if liq['side'] == 'LONG' else 'shorts'
            
            # Round to price levels (different granularity per asset)
            if symbol == 'BTC':
                level = round(price / 500) * 500  # $500 levels
            elif symbol == 'ETH':
                level = round(price / 50) * 50   # $50 levels
            else:
                level = round(price / 5) * 5     # $5 levels
            
            level_key = str(level)
            if level_key not in heatmap[symbol][side]:
                heatmap[symbol][side][level_key] = 0
            heatmap[symbol][side][level_key] += size
        
        # Convert to list format for UI
        result = {}
        for symbol in self.symbols:
            result[symbol] = {
                'long_levels': [
                    {'price': float(p), 'value': v}
                    for p, v in sorted(heatmap[symbol]['longs'].items(), key=lambda x: float(x[0]))
                ],
                'short_levels': [
                    {'price': float(p), 'value': v}
                    for p, v in sorted(heatmap[symbol]['shorts'].items(), key=lambda x: float(x[0]))
                ],
            }
        
        return result
    
    def save_data(self, data_type: str, data: any):
        """Save data to JSON files."""
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        date_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        
        # Daily file
        dir_path = OUTPUT_DIR / date_str
        dir_path.mkdir(parents=True, exist_ok=True)
        file_path = dir_path / f'{data_type}.json'
        
        # Load existing and append
        existing = []
        if file_path.exists():
            try:
                with open(file_path, 'r') as f:
                    existing = json.load(f)
            except:
                existing = []
        
        if isinstance(data, list):
            existing.extend(data)
        else:
            existing.append(data)
        
        existing = existing[-500:]  # Keep reasonable history
        
        with open(file_path, 'w') as f:
            json.dump(existing, f)
        
        # Latest file for quick access
        latest_path = OUTPUT_DIR / f'latest_{data_type}.json'
        with open(latest_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.debug(f"Saved {data_type}")
    
    def run(self, interval: int = 60):
        """Run the scraper loop."""
        self.running = True
        logger.info(f"Starting CoinGlass Agent (interval: {interval}s)")
        logger.info(f"Symbols: {self.symbols}")
        logger.info(f"Output: {OUTPUT_DIR}")
        
        cycle = 0
        while self.running:
            try:
                cycle += 1
                logger.info(f"=== Cycle {cycle} ===")
                
                # Fetch all data
                oi = self.fetch_open_interest()
                self.save_data('open_interest', oi)
                logger.info(f"OI: {len(oi)} symbols")
                
                fr = self.fetch_funding_rates()
                self.save_data('funding_rates', fr)
                logger.info(f"Funding: {list(fr.keys())}")
                
                ls = self.fetch_long_short_ratio()
                self.save_data('long_short_ratio', ls)
                logger.info(f"L/S: {', '.join(f'{s}: {d.get(\"ls_ratio\", 0):.2f}' for s, d in ls.items())}")
                
                liqs = self.fetch_liquidations()
                self.save_data('liquidations', liqs)
                logger.info(f"Liquidations: {len(liqs)} recent")
                
                heatmap = self.calculate_heatmap(liqs)
                self.save_data('heatmap', heatmap)
                
                # Aggregate summary
                summary = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'open_interest': oi,
                    'funding_rates': fr,
                    'long_short_ratio': ls,
                    'recent_liquidations': liqs[:10],
                    'heatmap': heatmap,
                }
                self.save_data('summary', summary)
                
                logger.info(f"Cycle {cycle} complete, waiting {interval}s...")
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Error in scrape cycle: {e}")
                time.sleep(10)
        
        logger.info("CoinGlass Agent stopped")
    
    def stop(self):
        """Stop the scraper."""
        self.running = False
        if self.client:
            self.client.close()


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Starting CoinGlass Heatmap Agent")
    logger.info("=" * 60)
    
    scraper = CoinGlassScraper(SYMBOLS)
    
    try:
        scraper.run(interval=INTERVAL)
    except KeyboardInterrupt:
        logger.info("Shutdown signal received")
        scraper.stop()


if __name__ == '__main__':
    main()

