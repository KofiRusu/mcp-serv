"""
Automation Generator - Uses local LLMs to generate automation code from natural language.

Supports multiple automation types:
- Scrapers: Data collection from exchanges/APIs
- Trading Bots: Automated order execution
- Alert Systems: Notifications on conditions
- Signal Generators: Multi-factor signal scoring
- Risk Monitors: Exposure/drawdown tracking
- Analytics Pipelines: Data processing workflows
- Backtesting Systems: Historical strategy testing
"""

import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

from .automation_store import (
    Automation, AutomationBlock, AutomationType, BlockType, DeploymentType,
    get_automation_store
)


# =============================================================================
# SCRAPER TEMPLATES
# =============================================================================

SCRAPER_TEMPLATES = {
    "binance_ws": {
        "name": "Binance WebSocket",
        "description": "Real-time data from Binance WebSocket API",
        "deployment": DeploymentType.DOCKER,
        "code_template": '''"""
{name} - Generated Scraper
{description}
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import websockets

OUTPUT_DIR = Path("{output_dir}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOL = "{symbol}"
STREAM = "{stream}"

async def connect_and_stream():
    url = f"wss://fstream.binance.com/ws/{{STREAM}}"
    print(f"Connecting to {{url}}...")
    
    async with websockets.connect(url) as ws:
        print(f"Connected! Streaming {{STREAM}} data...")
        
        while True:
            try:
                message = await ws.recv()
                data = json.loads(message)
                
                timestamp = datetime.utcnow().isoformat()
                record = {{"timestamp": timestamp, "symbol": SYMBOL, "data": data}}
                
                output_file = OUTPUT_DIR / f"{{SYMBOL}}_{{STREAM.split('@')[1]}}.jsonl"
                with open(output_file, "a") as f:
                    f.write(json.dumps(record) + "\\n")
                
                print(f"[{{timestamp}}] Received {{STREAM}} update")
                
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed. Reconnecting in 5s...")
                await asyncio.sleep(5)
                break
            except Exception as e:
                print(f"Error: {{e}}")
                await asyncio.sleep(1)

async def main():
    while True:
        try:
            await connect_and_stream()
        except Exception as e:
            print(f"Fatal error: {{e}}. Restarting in 10s...")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())
''',
        "default_config": {
            "symbol": "BTCUSDT",
            "stream": "btcusdt@aggTrade",
            "output_dir": "/app/data"
        }
    },
    
    "rest_api": {
        "name": "REST API Poller",
        "description": "Periodically fetches data from a REST API",
        "deployment": DeploymentType.DOCKER,
        "code_template": '''"""
{name} - Generated REST API Scraper
{description}
"""

import asyncio
import json
import httpx
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("{output_dir}")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

API_URL = "{api_url}"
INTERVAL_SECONDS = {interval}
HEADERS = {headers}

async def fetch_data():
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(API_URL, headers=HEADERS, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching data: {{e}}")
            return None

async def main():
    print(f"Starting REST API poller for {{API_URL}}")
    print(f"Polling every {{INTERVAL_SECONDS}} seconds")
    
    while True:
        timestamp = datetime.utcnow().isoformat()
        data = await fetch_data()
        
        if data:
            record = {{"timestamp": timestamp, "url": API_URL, "data": data}}
            
            output_file = OUTPUT_DIR / "api_data.jsonl"
            with open(output_file, "a") as f:
                f.write(json.dumps(record) + "\\n")
            
            print(f"[{{timestamp}}] Fetched and saved data")
        
        await asyncio.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    asyncio.run(main())
''',
        "default_config": {
            "api_url": "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            "interval": 60,
            "output_dir": "/app/data",
            "headers": {}
        }
    },
}


# =============================================================================
# TRADING BOT TEMPLATES
# =============================================================================

TRADING_BOT_TEMPLATES = {
    "simple_dca": {
        "name": "DCA Bot",
        "description": "Dollar-cost averaging bot - buys at regular intervals",
        "deployment": DeploymentType.SCHEDULED,
        "code_template": '''"""
{name} - DCA Trading Bot
{description}

⚠️ Paper Trading Mode: {paper_trading}
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import ccxt.async_support as ccxt

# Configuration
EXCHANGE = "{exchange}"
SYMBOL = "{symbol}"
AMOUNT_USD = {amount_usd}
PAPER_TRADING = {paper_trading}

LOG_FILE = Path("/app/data/dca_trades.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

async def get_exchange():
    exchange_class = getattr(ccxt, EXCHANGE)
    if PAPER_TRADING:
        return exchange_class({{"sandbox": True}})
    return exchange_class({{{api_keys}}})

async def execute_dca():
    timestamp = datetime.utcnow().isoformat()
    exchange = await get_exchange()
    
    try:
        # Get current price
        ticker = await exchange.fetch_ticker(SYMBOL)
        price = ticker["last"]
        
        # Calculate amount to buy
        amount = AMOUNT_USD / price
        
        if PAPER_TRADING:
            # Simulate order
            order = {{
                "id": f"paper_{{timestamp}}",
                "symbol": SYMBOL,
                "side": "buy",
                "amount": amount,
                "price": price,
                "status": "filled",
                "paper": True
            }}
        else:
            # Execute real order
            order = await exchange.create_market_buy_order(SYMBOL, amount)
        
        # Log trade
        log_entry = {{
            "timestamp": timestamp,
            "order": order,
            "amount_usd": AMOUNT_USD,
            "price": price
        }}
        
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(log_entry) + "\\n")
        
        print(f"[{{timestamp}}] DCA executed: Bought {{amount:.6f}} {{SYMBOL}} at ${{price:,.2f}}")
        
    except Exception as e:
        print(f"Error executing DCA: {{e}}")
    finally:
        await exchange.close()

if __name__ == "__main__":
    asyncio.run(execute_dca())
''',
        "default_config": {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "amount_usd": 100,
            "paper_trading": True,
            "api_keys": ""
        }
    },
    
    "grid_bot": {
        "name": "Grid Trading Bot",
        "description": "Places buy/sell orders at price grid levels",
        "deployment": DeploymentType.REALTIME,
        "code_template": '''"""
{name} - Grid Trading Bot
{description}

⚠️ Paper Trading Mode: {paper_trading}
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from decimal import Decimal
import ccxt.async_support as ccxt

# Configuration
EXCHANGE = "{exchange}"
SYMBOL = "{symbol}"
GRID_LOWER = {grid_lower}
GRID_UPPER = {grid_upper}
GRID_LEVELS = {grid_levels}
AMOUNT_PER_GRID = {amount_per_grid}
PAPER_TRADING = {paper_trading}

LOG_FILE = Path("/app/data/grid_trades.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

class GridBot:
    def __init__(self):
        self.orders = {{}}
        self.exchange = None
        self.grid_prices = []
        
    def calculate_grid(self):
        step = (GRID_UPPER - GRID_LOWER) / (GRID_LEVELS - 1)
        self.grid_prices = [GRID_LOWER + i * step for i in range(GRID_LEVELS)]
        print(f"Grid levels: {{[f'${{p:,.2f}}' for p in self.grid_prices]}}")
        
    async def run(self):
        self.calculate_grid()
        exchange_class = getattr(ccxt, EXCHANGE)
        self.exchange = exchange_class({{"sandbox": PAPER_TRADING}})
        
        try:
            while True:
                await self.check_and_place_orders()
                await asyncio.sleep(5)
        finally:
            await self.exchange.close()
    
    async def check_and_place_orders(self):
        ticker = await self.exchange.fetch_ticker(SYMBOL)
        current_price = ticker["last"]
        timestamp = datetime.utcnow().isoformat()
        
        for i, grid_price in enumerate(self.grid_prices):
            grid_id = f"grid_{{i}}"
            
            if grid_id not in self.orders:
                # Place initial orders
                if grid_price < current_price:
                    # Buy order below current price
                    side = "buy"
                else:
                    # Sell order above current price
                    side = "sell"
                
                if PAPER_TRADING:
                    order = {{"id": grid_id, "side": side, "price": grid_price, "status": "open"}}
                else:
                    order = await self.exchange.create_limit_order(
                        SYMBOL, side, AMOUNT_PER_GRID, grid_price
                    )
                
                self.orders[grid_id] = order
                self.log_order(timestamp, order)
                
    def log_order(self, timestamp, order):
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps({{"timestamp": timestamp, "order": order}}) + "\\n")
        print(f"[{{timestamp}}] Grid order: {{order['side']}} at ${{order['price']:,.2f}}")

if __name__ == "__main__":
    bot = GridBot()
    asyncio.run(bot.run())
''',
        "default_config": {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "grid_lower": 40000,
            "grid_upper": 50000,
            "grid_levels": 10,
            "amount_per_grid": 0.001,
            "paper_trading": True
        }
    },
    
    "momentum_bot": {
        "name": "Momentum Trading Bot",
        "description": "Trades based on price momentum and RSI",
        "deployment": DeploymentType.REALTIME,
        "code_template": '''"""
{name} - Momentum Trading Bot
{description}

⚠️ Paper Trading Mode: {paper_trading}
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from collections import deque
import ccxt.async_support as ccxt

# Configuration
EXCHANGE = "{exchange}"
SYMBOL = "{symbol}"
RSI_PERIOD = {rsi_period}
RSI_OVERSOLD = {rsi_oversold}
RSI_OVERBOUGHT = {rsi_overbought}
POSITION_SIZE = {position_size}
PAPER_TRADING = {paper_trading}

LOG_FILE = Path("/app/data/momentum_trades.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

class MomentumBot:
    def __init__(self):
        self.exchange = None
        self.prices = deque(maxlen=RSI_PERIOD + 1)
        self.position = 0
        
    def calculate_rsi(self):
        if len(self.prices) < RSI_PERIOD + 1:
            return 50  # Neutral
        
        gains = []
        losses = []
        
        for i in range(1, len(self.prices)):
            change = self.prices[i] - self.prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-RSI_PERIOD:]) / RSI_PERIOD
        avg_loss = sum(losses[-RSI_PERIOD:]) / RSI_PERIOD
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    async def run(self):
        exchange_class = getattr(ccxt, EXCHANGE)
        self.exchange = exchange_class({{"sandbox": PAPER_TRADING}})
        
        try:
            print(f"Starting Momentum Bot for {{SYMBOL}}")
            print(f"RSI: Period={{RSI_PERIOD}}, Oversold={{RSI_OVERSOLD}}, Overbought={{RSI_OVERBOUGHT}}")
            
            while True:
                await self.tick()
                await asyncio.sleep(60)  # Check every minute
        finally:
            await self.exchange.close()
    
    async def tick(self):
        timestamp = datetime.utcnow().isoformat()
        ticker = await self.exchange.fetch_ticker(SYMBOL)
        price = ticker["last"]
        self.prices.append(price)
        
        rsi = self.calculate_rsi()
        
        signal = None
        if rsi < RSI_OVERSOLD and self.position <= 0:
            signal = "BUY"
            self.position = 1
        elif rsi > RSI_OVERBOUGHT and self.position >= 0:
            signal = "SELL"
            self.position = -1
        
        if signal:
            self.log_trade(timestamp, signal, price, rsi)
    
    def log_trade(self, timestamp, signal, price, rsi):
        trade = {{
            "timestamp": timestamp,
            "signal": signal,
            "price": price,
            "rsi": rsi,
            "position_size": POSITION_SIZE,
            "paper": PAPER_TRADING
        }}
        
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(trade) + "\\n")
        
        emoji = "🟢" if signal == "BUY" else "🔴"
        print(f"[{{timestamp}}] {{emoji}} {{signal}} at ${{price:,.2f}} (RSI: {{rsi:.1f}})")

if __name__ == "__main__":
    bot = MomentumBot()
    asyncio.run(bot.run())
''',
        "default_config": {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "rsi_period": 14,
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "position_size": 0.001,
            "paper_trading": True
        }
    }
}


# =============================================================================
# ALERT SYSTEM TEMPLATES
# =============================================================================

ALERT_TEMPLATES = {
    "price_alert": {
        "name": "Price Alert",
        "description": "Sends alerts when price crosses a threshold",
        "deployment": DeploymentType.REALTIME,
        "code_template": '''"""
{name} - Price Alert System
{description}
"""

import asyncio
import json
import httpx
from datetime import datetime
from pathlib import Path
import ccxt.async_support as ccxt

# Configuration
EXCHANGE = "{exchange}"
SYMBOL = "{symbol}"
ALERT_ABOVE = {alert_above}
ALERT_BELOW = {alert_below}
WEBHOOK_URL = "{webhook_url}"
CHECK_INTERVAL = {check_interval}

LOG_FILE = Path("/app/data/price_alerts.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

class PriceAlertMonitor:
    def __init__(self):
        self.exchange = None
        self.last_alert_time = None
        self.cooldown_seconds = 300  # 5 minute cooldown between alerts
        
    async def send_alert(self, alert_type: str, price: float):
        timestamp = datetime.utcnow()
        
        # Check cooldown
        if self.last_alert_time:
            elapsed = (timestamp - self.last_alert_time).total_seconds()
            if elapsed < self.cooldown_seconds:
                return
        
        message = f"🚨 PRICE ALERT: {{SYMBOL}} {{alert_type}} ${{price:,.2f}}"
        
        # Send webhook if configured
        if WEBHOOK_URL:
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(WEBHOOK_URL, json={{
                        "text": message,
                        "symbol": SYMBOL,
                        "price": price,
                        "alert_type": alert_type,
                        "timestamp": timestamp.isoformat()
                    }})
                except Exception as e:
                    print(f"Webhook error: {{e}}")
        
        # Log alert
        alert_log = {{
            "timestamp": timestamp.isoformat(),
            "symbol": SYMBOL,
            "alert_type": alert_type,
            "price": price
        }}
        
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(alert_log) + "\\n")
        
        print(message)
        self.last_alert_time = timestamp
        
    async def run(self):
        exchange_class = getattr(ccxt, EXCHANGE)
        self.exchange = exchange_class()
        
        try:
            print(f"Starting Price Alert Monitor for {{SYMBOL}}")
            print(f"Alert above: ${{ALERT_ABOVE:,.2f}}, Alert below: ${{ALERT_BELOW:,.2f}}")
            
            while True:
                ticker = await self.exchange.fetch_ticker(SYMBOL)
                price = ticker["last"]
                
                if ALERT_ABOVE and price > ALERT_ABOVE:
                    await self.send_alert(f"ABOVE {{ALERT_ABOVE}}", price)
                elif ALERT_BELOW and price < ALERT_BELOW:
                    await self.send_alert(f"BELOW {{ALERT_BELOW}}", price)
                else:
                    print(f"Current price: ${{price:,.2f}}")
                
                await asyncio.sleep(CHECK_INTERVAL)
        finally:
            await self.exchange.close()

if __name__ == "__main__":
    monitor = PriceAlertMonitor()
    asyncio.run(monitor.run())
''',
        "default_config": {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "alert_above": 100000,
            "alert_below": 50000,
            "webhook_url": "",
            "check_interval": 30
        }
    },
    
    "indicator_alert": {
        "name": "Technical Indicator Alert",
        "description": "Alerts based on technical indicators (RSI, MACD, etc.)",
        "deployment": DeploymentType.REALTIME,
        "code_template": '''"""
{name} - Technical Indicator Alert
{description}
"""

import asyncio
import json
import httpx
from datetime import datetime
from pathlib import Path
from collections import deque
import ccxt.async_support as ccxt

# Configuration
EXCHANGE = "{exchange}"
SYMBOL = "{symbol}"
INDICATOR = "{indicator}"  # rsi, macd, bb
RSI_OVERSOLD = {rsi_oversold}
RSI_OVERBOUGHT = {rsi_overbought}
WEBHOOK_URL = "{webhook_url}"

LOG_FILE = Path("/app/data/indicator_alerts.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

class IndicatorAlertMonitor:
    def __init__(self):
        self.exchange = None
        self.prices = deque(maxlen=100)
        self.last_alert = None
        
    def calculate_rsi(self, period=14):
        if len(self.prices) < period + 1:
            return 50
        
        gains, losses = [], []
        prices = list(self.prices)
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        return 100 - (100 / (1 + avg_gain / avg_loss))
    
    async def send_alert(self, condition: str, value: float, price: float):
        timestamp = datetime.utcnow().isoformat()
        message = f"📊 {{INDICATOR.upper()}} ALERT: {{SYMBOL}} - {{condition}} (Value: {{value:.2f}}, Price: ${{price:,.2f}})"
        
        if WEBHOOK_URL:
            async with httpx.AsyncClient() as client:
                try:
                    await client.post(WEBHOOK_URL, json={{
                        "text": message,
                        "indicator": INDICATOR,
                        "value": value,
                        "price": price,
                        "condition": condition
                    }})
                except Exception as e:
                    print(f"Webhook error: {{e}}")
        
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps({{
                "timestamp": timestamp,
                "indicator": INDICATOR,
                "condition": condition,
                "value": value,
                "price": price
            }}) + "\\n")
        
        print(message)
        
    async def run(self):
        exchange_class = getattr(ccxt, EXCHANGE)
        self.exchange = exchange_class()
        
        try:
            print(f"Starting Indicator Alert Monitor for {{SYMBOL}} ({{INDICATOR}})")
            
            while True:
                ohlcv = await self.exchange.fetch_ohlcv(SYMBOL, "1m", limit=100)
                for candle in ohlcv:
                    self.prices.append(candle[4])  # Close price
                
                price = self.prices[-1] if self.prices else 0
                
                if INDICATOR == "rsi":
                    rsi = self.calculate_rsi()
                    if rsi < RSI_OVERSOLD:
                        await self.send_alert("OVERSOLD", rsi, price)
                    elif rsi > RSI_OVERBOUGHT:
                        await self.send_alert("OVERBOUGHT", rsi, price)
                    else:
                        print(f"RSI: {{rsi:.1f}}, Price: ${{price:,.2f}}")
                
                await asyncio.sleep(60)
        finally:
            await self.exchange.close()

if __name__ == "__main__":
    monitor = IndicatorAlertMonitor()
    asyncio.run(monitor.run())
''',
        "default_config": {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "indicator": "rsi",
            "rsi_oversold": 30,
            "rsi_overbought": 70,
            "webhook_url": ""
        }
    }
}


# =============================================================================
# SIGNAL GENERATOR TEMPLATES
# =============================================================================

SIGNAL_TEMPLATES = {
    "multi_factor_signal": {
        "name": "Multi-Factor Signal Generator",
        "description": "Combines multiple indicators into a single signal score",
        "deployment": DeploymentType.REALTIME,
        "code_template": '''"""
{name} - Multi-Factor Signal Generator
{description}
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from collections import deque
import ccxt.async_support as ccxt

# Configuration
EXCHANGE = "{exchange}"
SYMBOL = "{symbol}"
RSI_WEIGHT = {rsi_weight}
MOMENTUM_WEIGHT = {momentum_weight}
VOLUME_WEIGHT = {volume_weight}

OUTPUT_FILE = Path("/app/data/signals.jsonl")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

class MultiFactorSignal:
    def __init__(self):
        self.exchange = None
        self.prices = deque(maxlen=100)
        self.volumes = deque(maxlen=100)
        
    def calculate_rsi(self, period=14):
        if len(self.prices) < period + 1:
            return 50
        
        prices = list(self.prices)
        gains = [max(0, prices[i] - prices[i-1]) for i in range(1, len(prices))]
        losses = [max(0, prices[i-1] - prices[i]) for i in range(1, len(prices))]
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        return 100 - (100 / (1 + avg_gain / avg_loss))
    
    def calculate_momentum(self, period=20):
        if len(self.prices) < period:
            return 0
        
        prices = list(self.prices)
        return (prices[-1] - prices[-period]) / prices[-period] * 100
    
    def calculate_volume_signal(self, period=20):
        if len(self.volumes) < period:
            return 0
        
        volumes = list(self.volumes)
        avg_vol = sum(volumes[-period:]) / period
        current_vol = volumes[-1]
        
        return (current_vol - avg_vol) / avg_vol * 100 if avg_vol > 0 else 0
    
    def calculate_composite_signal(self):
        rsi = self.calculate_rsi()
        momentum = self.calculate_momentum()
        volume = self.calculate_volume_signal()
        
        # Normalize RSI to -1 to 1 scale
        rsi_score = (50 - rsi) / 50  # Negative when overbought, positive when oversold
        
        # Normalize momentum
        momentum_score = max(-1, min(1, momentum / 10))
        
        # Normalize volume
        volume_score = max(-1, min(1, volume / 100))
        
        # Weighted composite
        total_weight = RSI_WEIGHT + MOMENTUM_WEIGHT + VOLUME_WEIGHT
        composite = (
            rsi_score * RSI_WEIGHT +
            momentum_score * MOMENTUM_WEIGHT +
            volume_score * VOLUME_WEIGHT
        ) / total_weight
        
        return {{
            "composite": round(composite, 4),
            "rsi": round(rsi, 2),
            "rsi_score": round(rsi_score, 4),
            "momentum": round(momentum, 4),
            "momentum_score": round(momentum_score, 4),
            "volume_change": round(volume, 2),
            "volume_score": round(volume_score, 4),
            "signal": "BUY" if composite > 0.3 else "SELL" if composite < -0.3 else "NEUTRAL"
        }}
    
    async def run(self):
        exchange_class = getattr(ccxt, EXCHANGE)
        self.exchange = exchange_class()
        
        try:
            print(f"Starting Multi-Factor Signal Generator for {{SYMBOL}}")
            
            while True:
                ohlcv = await self.exchange.fetch_ohlcv(SYMBOL, "1m", limit=100)
                for candle in ohlcv:
                    self.prices.append(candle[4])   # Close
                    self.volumes.append(candle[5])  # Volume
                
                signal = self.calculate_composite_signal()
                signal["timestamp"] = datetime.utcnow().isoformat()
                signal["symbol"] = SYMBOL
                signal["price"] = self.prices[-1] if self.prices else 0
                
                with open(OUTPUT_FILE, "a") as f:
                    f.write(json.dumps(signal) + "\\n")
                
                emoji = "🟢" if signal["signal"] == "BUY" else "🔴" if signal["signal"] == "SELL" else "⚪"
                print(f"[{{signal['timestamp']}}] {{emoji}} Signal: {{signal['signal']}} (Score: {{signal['composite']:.2f}})")
                
                await asyncio.sleep(60)
        finally:
            await self.exchange.close()

if __name__ == "__main__":
    generator = MultiFactorSignal()
    asyncio.run(generator.run())
''',
        "default_config": {
            "exchange": "binance",
            "symbol": "BTC/USDT",
            "rsi_weight": 0.4,
            "momentum_weight": 0.3,
            "volume_weight": 0.3
        }
    }
}


# =============================================================================
# RISK MONITOR TEMPLATES
# =============================================================================

RISK_TEMPLATES = {
    "portfolio_risk": {
        "name": "Portfolio Risk Monitor",
        "description": "Monitors portfolio exposure, drawdown, and risk metrics",
        "deployment": DeploymentType.REALTIME,
        "code_template": '''"""
{name} - Portfolio Risk Monitor
{description}
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
import ccxt.async_support as ccxt

# Configuration
EXCHANGE = "{exchange}"
SYMBOLS = {symbols}
MAX_DRAWDOWN_PERCENT = {max_drawdown}
MAX_POSITION_PERCENT = {max_position}
ALERT_WEBHOOK = "{webhook_url}"

LOG_FILE = Path("/app/data/risk_monitor.jsonl")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

class RiskMonitor:
    def __init__(self):
        self.exchange = None
        self.peak_equity = 0
        
    async def get_portfolio_value(self):
        balance = await self.exchange.fetch_balance()
        total = balance["total"]
        
        portfolio_usd = 0
        for asset, amount in total.items():
            if amount > 0:
                if asset == "USDT" or asset == "USD":
                    portfolio_usd += amount
                else:
                    try:
                        ticker = await self.exchange.fetch_ticker(f"{{asset}}/USDT")
                        portfolio_usd += amount * ticker["last"]
                    except:
                        pass
        
        return portfolio_usd
    
    async def calculate_metrics(self):
        equity = await self.get_portfolio_value()
        
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        drawdown = ((self.peak_equity - equity) / self.peak_equity * 100) if self.peak_equity > 0 else 0
        
        # Get positions
        positions = await self.exchange.fetch_positions() if hasattr(self.exchange, "fetch_positions") else []
        
        # Calculate position sizes
        position_exposures = []
        for pos in positions:
            if pos.get("contracts", 0) > 0:
                exposure = abs(pos.get("notional", 0))
                pct = (exposure / equity * 100) if equity > 0 else 0
                position_exposures.append({{
                    "symbol": pos["symbol"],
                    "exposure_usd": exposure,
                    "exposure_pct": pct
                }})
        
        return {{
            "equity": equity,
            "peak_equity": self.peak_equity,
            "drawdown_pct": drawdown,
            "positions": position_exposures,
            "risk_alerts": []
        }}
    
    async def check_risk_limits(self, metrics):
        alerts = []
        
        if metrics["drawdown_pct"] > MAX_DRAWDOWN_PERCENT:
            alerts.append(f"⚠️ DRAWDOWN ALERT: {{metrics['drawdown_pct']:.2f}}% exceeds limit of {{MAX_DRAWDOWN_PERCENT}}%")
        
        for pos in metrics["positions"]:
            if pos["exposure_pct"] > MAX_POSITION_PERCENT:
                alerts.append(f"⚠️ POSITION ALERT: {{pos['symbol']}} at {{pos['exposure_pct']:.2f}}% exceeds limit of {{MAX_POSITION_PERCENT}}%")
        
        metrics["risk_alerts"] = alerts
        return alerts
    
    async def run(self):
        exchange_class = getattr(ccxt, EXCHANGE)
        self.exchange = exchange_class({{"sandbox": True}})  # Use sandbox for testing
        
        try:
            print(f"Starting Portfolio Risk Monitor")
            print(f"Max Drawdown: {{MAX_DRAWDOWN_PERCENT}}%, Max Position: {{MAX_POSITION_PERCENT}}%")
            
            while True:
                metrics = await self.calculate_metrics()
                alerts = await self.check_risk_limits(metrics)
                
                metrics["timestamp"] = datetime.utcnow().isoformat()
                
                with open(LOG_FILE, "a") as f:
                    f.write(json.dumps(metrics) + "\\n")
                
                # Print status
                print(f"[{{metrics['timestamp']}}] Equity: ${{metrics['equity']:,.2f}}, Drawdown: {{metrics['drawdown_pct']:.2f}}%")
                
                for alert in alerts:
                    print(alert)
                
                await asyncio.sleep(30)
        finally:
            await self.exchange.close()

if __name__ == "__main__":
    monitor = RiskMonitor()
    asyncio.run(monitor.run())
''',
        "default_config": {
            "exchange": "binance",
            "symbols": ["BTC/USDT", "ETH/USDT"],
            "max_drawdown": 10,
            "max_position": 25,
            "webhook_url": ""
        }
    }
}


# =============================================================================
# BACKTEST TEMPLATES
# =============================================================================

BACKTEST_TEMPLATES = {
    "simple_backtest": {
        "name": "Simple Strategy Backtest",
        "description": "Backtest a simple moving average crossover strategy",
        "deployment": DeploymentType.PROCESS,
        "code_template": '''"""
{name} - Strategy Backtest
{description}
"""

import json
from datetime import datetime
from pathlib import Path
import pandas as pd
import numpy as np

# Configuration
DATA_FILE = "{data_file}"
SYMBOL = "{symbol}"
FAST_MA = {fast_ma}
SLOW_MA = {slow_ma}
INITIAL_CAPITAL = {initial_capital}

OUTPUT_DIR = Path("/app/data/backtest_results")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_data():
    """Load historical OHLCV data."""
    df = pd.read_json(DATA_FILE, lines=True)
    if "data" in df.columns:
        # Extract from nested structure
        df = pd.json_normalize(df["data"])
    return df

def calculate_signals(df):
    """Calculate MA crossover signals."""
    df["fast_ma"] = df["close"].rolling(FAST_MA).mean()
    df["slow_ma"] = df["close"].rolling(SLOW_MA).mean()
    
    df["signal"] = 0
    df.loc[df["fast_ma"] > df["slow_ma"], "signal"] = 1
    df.loc[df["fast_ma"] < df["slow_ma"], "signal"] = -1
    
    df["position"] = df["signal"].shift(1)  # Enter on next bar
    return df

def run_backtest(df):
    """Execute backtest and calculate returns."""
    df["returns"] = df["close"].pct_change()
    df["strategy_returns"] = df["returns"] * df["position"]
    
    # Calculate cumulative returns
    df["cumulative_market"] = (1 + df["returns"]).cumprod() * INITIAL_CAPITAL
    df["cumulative_strategy"] = (1 + df["strategy_returns"]).cumprod() * INITIAL_CAPITAL
    
    # Calculate metrics
    total_return = (df["cumulative_strategy"].iloc[-1] / INITIAL_CAPITAL - 1) * 100
    market_return = (df["cumulative_market"].iloc[-1] / INITIAL_CAPITAL - 1) * 100
    
    # Sharpe ratio (annualized)
    sharpe = np.sqrt(252) * df["strategy_returns"].mean() / df["strategy_returns"].std()
    
    # Max drawdown
    rolling_max = df["cumulative_strategy"].expanding().max()
    drawdown = (df["cumulative_strategy"] - rolling_max) / rolling_max
    max_drawdown = drawdown.min() * 100
    
    # Win rate
    winning_trades = (df["strategy_returns"] > 0).sum()
    total_trades = (df["position"] != 0).sum()
    win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
    
    return {{
        "total_return_pct": round(total_return, 2),
        "market_return_pct": round(market_return, 2),
        "alpha_pct": round(total_return - market_return, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown_pct": round(max_drawdown, 2),
        "win_rate_pct": round(win_rate, 2),
        "total_trades": int(total_trades),
        "final_equity": round(df["cumulative_strategy"].iloc[-1], 2),
        "start_date": str(df.index[0]) if hasattr(df.index[0], '__str__') else df.index[0],
        "end_date": str(df.index[-1]) if hasattr(df.index[-1], '__str__') else df.index[-1]
    }}

def main():
    print(f"Running backtest for {{SYMBOL}}")
    print(f"Strategy: MA Crossover (Fast={{FAST_MA}}, Slow={{SLOW_MA}})")
    print(f"Initial Capital: ${{INITIAL_CAPITAL:,}}")
    print("-" * 50)
    
    # Load and process data
    df = load_data()
    df = calculate_signals(df)
    
    # Run backtest
    results = run_backtest(df)
    results["symbol"] = SYMBOL
    results["strategy"] = f"MA_{{FAST_MA}}_{{SLOW_MA}}"
    results["timestamp"] = datetime.utcnow().isoformat()
    
    # Save results
    output_file = OUTPUT_DIR / f"backtest_{{SYMBOL.replace('/', '_')}}_{{datetime.now().strftime('%Y%m%d_%H%M%S')}}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    # Print results
    print(f"\\n📊 BACKTEST RESULTS")
    print(f"Strategy Return: {{results['total_return_pct']}}%")
    print(f"Market Return: {{results['market_return_pct']}}%")
    print(f"Alpha: {{results['alpha_pct']}}%")
    print(f"Sharpe Ratio: {{results['sharpe_ratio']}}")
    print(f"Max Drawdown: {{results['max_drawdown_pct']}}%")
    print(f"Win Rate: {{results['win_rate_pct']}}%")
    print(f"Total Trades: {{results['total_trades']}}")
    print(f"Final Equity: ${{results['final_equity']:,.2f}}")
    print(f"\\nResults saved to: {{output_file}}")

if __name__ == "__main__":
    main()
''',
        "default_config": {
            "data_file": "/app/data/btc_1h.jsonl",
            "symbol": "BTC/USDT",
            "fast_ma": 10,
            "slow_ma": 30,
            "initial_capital": 10000
        }
    }
}


# =============================================================================
# TEMPLATE REGISTRY
# =============================================================================

ALL_TEMPLATES = {
    AutomationType.SCRAPER: SCRAPER_TEMPLATES,
    AutomationType.TRADING_BOT: TRADING_BOT_TEMPLATES,
    AutomationType.ALERT: ALERT_TEMPLATES,
    AutomationType.SIGNAL: SIGNAL_TEMPLATES,
    AutomationType.RISK: RISK_TEMPLATES,
    AutomationType.BACKTEST: BACKTEST_TEMPLATES,
}


# =============================================================================
# GENERATOR CLASS
# =============================================================================

class AutomationGenerator:
    """Generates automation code from natural language using local LLMs."""
    
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_base_url
    
    async def generate_from_prompt(
        self,
        prompt: str,
        automation_type: Optional[AutomationType] = None
    ) -> Dict[str, Any]:
        """
        Generate automation config and code from a natural language prompt.
        """
        # Auto-detect type if not specified
        if automation_type is None:
            automation_type = self._detect_type(prompt)
        
        # Get templates for this type
        templates = ALL_TEMPLATES.get(automation_type, SCRAPER_TEMPLATES)
        
        # Analyze prompt and select template
        analysis = self._analyze_prompt(prompt, automation_type)
        template_key = analysis.get("template", list(templates.keys())[0])
        template = templates.get(template_key, list(templates.values())[0])
        
        # Merge configs
        config = {**template["default_config"], **analysis.get("config", {})}
        
        # Generate code
        code = self._generate_code(template["code_template"], {
            "name": analysis.get("name", "Custom Automation"),
            "description": analysis.get("description", prompt),
            **config
        })
        
        # Build visual blocks
        blocks = self._build_blocks(automation_type, template_key, config)
        
        return {
            "name": analysis.get("name", "Custom Automation"),
            "description": analysis.get("description", prompt),
            "type": automation_type,
            "deployment_type": template.get("deployment", DeploymentType.DOCKER),
            "blocks": blocks,
            "config": config,
            "generated_code": code,
            "template_used": template_key,
            "paper_trading": config.get("paper_trading", True)
        }
    
    def _detect_type(self, prompt: str) -> AutomationType:
        """Detect automation type from prompt."""
        prompt_lower = prompt.lower()
        
        # Trading bot keywords
        if any(kw in prompt_lower for kw in ["trading bot", "dca", "grid", "auto trade", "execute order", "buy and sell"]):
            return AutomationType.TRADING_BOT
        
        # Alert keywords
        if any(kw in prompt_lower for kw in ["alert", "notify", "notification", "when price", "send message"]):
            return AutomationType.ALERT
        
        # Signal keywords
        if any(kw in prompt_lower for kw in ["signal", "score", "confluence", "multi-factor"]):
            return AutomationType.SIGNAL
        
        # Risk keywords
        if any(kw in prompt_lower for kw in ["risk", "drawdown", "exposure", "portfolio", "position size"]):
            return AutomationType.RISK
        
        # Backtest keywords
        if any(kw in prompt_lower for kw in ["backtest", "historical", "test strategy", "simulate"]):
            return AutomationType.BACKTEST
        
        # Default to scraper
        return AutomationType.SCRAPER
    
    def _analyze_prompt(self, prompt: str, auto_type: AutomationType) -> Dict[str, Any]:
        """Analyze user prompt to extract configuration."""
        prompt_lower = prompt.lower()
        result = {
            "name": "Custom Automation",
            "description": prompt,
            "template": None,
            "config": {}
        }
        
        # Extract common elements
        symbols = ["btc", "eth", "sol", "bnb", "xrp", "ada", "doge", "avax"]
        for sym in symbols:
            if sym in prompt_lower:
                result["config"]["symbol"] = f"{sym.upper()}/USDT"
                break
        
        # Extract interval
        interval_patterns = [
            (r"every\s*(\d+)\s*second", 1),
            (r"every\s*(\d+)\s*minute", 60),
            (r"every\s*(\d+)\s*hour", 3600),
        ]
        for pattern, multiplier in interval_patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                result["config"]["interval"] = int(match.group(1)) * multiplier
                break
        
        # Type-specific analysis
        if auto_type == AutomationType.SCRAPER:
            result = self._analyze_scraper_prompt(prompt_lower, result)
        elif auto_type == AutomationType.TRADING_BOT:
            result = self._analyze_trading_prompt(prompt_lower, result)
        elif auto_type == AutomationType.ALERT:
            result = self._analyze_alert_prompt(prompt_lower, result)
        elif auto_type == AutomationType.SIGNAL:
            result["template"] = "multi_factor_signal"
            result["name"] = "Signal Generator"
        elif auto_type == AutomationType.RISK:
            result["template"] = "portfolio_risk"
            result["name"] = "Risk Monitor"
        elif auto_type == AutomationType.BACKTEST:
            result["template"] = "simple_backtest"
            result["name"] = "Strategy Backtest"
        
        return result
    
    def _analyze_scraper_prompt(self, prompt_lower: str, result: Dict) -> Dict:
        """Analyze scraper-specific prompt."""
        if "binance" in prompt_lower:
            result["template"] = "binance_ws"
            result["name"] = "Binance Data Scraper"
            
            symbol = result["config"].get("symbol", "BTC/USDT").replace("/", "").lower()
            
            if "orderbook" in prompt_lower or "depth" in prompt_lower:
                result["config"]["stream"] = f"{symbol}@depth@100ms"
            elif "trade" in prompt_lower:
                result["config"]["stream"] = f"{symbol}@aggTrade"
            elif "ticker" in prompt_lower:
                result["config"]["stream"] = f"{symbol}@ticker"
            else:
                result["config"]["stream"] = f"{symbol}@aggTrade"
        else:
            result["template"] = "rest_api"
            result["name"] = "REST API Scraper"
        
        return result
    
    def _analyze_trading_prompt(self, prompt_lower: str, result: Dict) -> Dict:
        """Analyze trading bot prompt."""
        if "dca" in prompt_lower or "dollar cost" in prompt_lower:
            result["template"] = "simple_dca"
            result["name"] = "DCA Bot"
        elif "grid" in prompt_lower:
            result["template"] = "grid_bot"
            result["name"] = "Grid Trading Bot"
        elif "momentum" in prompt_lower or "rsi" in prompt_lower:
            result["template"] = "momentum_bot"
            result["name"] = "Momentum Bot"
        else:
            result["template"] = "simple_dca"
            result["name"] = "Trading Bot"
        
        # Extract amounts
        amount_match = re.search(r"\$?(\d+)\s*(usd|dollar)?", prompt_lower)
        if amount_match:
            result["config"]["amount_usd"] = int(amount_match.group(1))
        
        return result
    
    def _analyze_alert_prompt(self, prompt_lower: str, result: Dict) -> Dict:
        """Analyze alert prompt."""
        if "indicator" in prompt_lower or "rsi" in prompt_lower or "macd" in prompt_lower:
            result["template"] = "indicator_alert"
            result["name"] = "Indicator Alert"
        else:
            result["template"] = "price_alert"
            result["name"] = "Price Alert"
        
        # Extract price thresholds
        above_match = re.search(r"above\s*\$?(\d+[\d,]*)", prompt_lower)
        if above_match:
            result["config"]["alert_above"] = int(above_match.group(1).replace(",", ""))
        
        below_match = re.search(r"below\s*\$?(\d+[\d,]*)", prompt_lower)
        if below_match:
            result["config"]["alert_below"] = int(below_match.group(1).replace(",", ""))
        
        return result
    
    def _generate_code(self, template: str, values: Dict[str, Any]) -> str:
        """Generate code from template with values."""
        code = template
        for key, value in values.items():
            placeholder = "{" + key + "}"
            if isinstance(value, (list, dict)):
                code = code.replace(placeholder, json.dumps(value))
            elif isinstance(value, bool):
                code = code.replace(placeholder, str(value))
            else:
                code = code.replace(placeholder, str(value))
        return code
    
    def _build_blocks(self, auto_type: AutomationType, template_key: str, config: Dict) -> List[Dict]:
        """Build visual blocks for the automation flow."""
        blocks = []
        
        if auto_type == AutomationType.SCRAPER:
            blocks = [
                {"id": "src-1", "type": "source", "name": template_key.replace("_", " ").title(),
                 "config": config, "position": {"x": 100, "y": 100}, "connections": ["out-1"]},
                {"id": "out-1", "type": "output", "name": "JSON File",
                 "config": {"output_dir": config.get("output_dir", "/app/data")},
                 "position": {"x": 400, "y": 100}, "connections": []}
            ]
        
        elif auto_type == AutomationType.TRADING_BOT:
            blocks = [
                {"id": "src-1", "type": "source", "name": "Price Feed",
                 "config": {"symbol": config.get("symbol", "BTC/USDT")},
                 "position": {"x": 100, "y": 100}, "connections": ["ind-1"]},
                {"id": "ind-1", "type": "indicator", "name": "Signal Logic",
                 "config": {}, "position": {"x": 300, "y": 100}, "connections": ["risk-1"]},
                {"id": "risk-1", "type": "risk_check", "name": "Risk Check",
                 "config": {"paper_trading": config.get("paper_trading", True)},
                 "position": {"x": 500, "y": 100}, "connections": ["order-1"]},
                {"id": "order-1", "type": "order", "name": "Order Execution",
                 "config": {"exchange": config.get("exchange", "binance")},
                 "position": {"x": 700, "y": 100}, "connections": []}
            ]
        
        elif auto_type == AutomationType.ALERT:
            blocks = [
                {"id": "src-1", "type": "source", "name": "Price Monitor",
                 "config": {"symbol": config.get("symbol", "BTC/USDT")},
                 "position": {"x": 100, "y": 100}, "connections": ["cond-1"]},
                {"id": "cond-1", "type": "condition", "name": "Price Condition",
                 "config": config, "position": {"x": 300, "y": 100}, "connections": ["notif-1"]},
                {"id": "notif-1", "type": "notification", "name": "Send Alert",
                 "config": {"webhook": config.get("webhook_url", "")},
                 "position": {"x": 500, "y": 100}, "connections": []}
            ]
        
        elif auto_type == AutomationType.SIGNAL:
            blocks = [
                {"id": "src-1", "type": "source", "name": "OHLCV Data",
                 "config": {"symbol": config.get("symbol", "BTC/USDT")},
                 "position": {"x": 100, "y": 100}, "connections": ["ind-1", "ind-2", "ind-3"]},
                {"id": "ind-1", "type": "indicator", "name": "RSI",
                 "config": {"period": 14}, "position": {"x": 300, "y": 50}, "connections": ["agg-1"]},
                {"id": "ind-2", "type": "indicator", "name": "Momentum",
                 "config": {"period": 20}, "position": {"x": 300, "y": 150}, "connections": ["agg-1"]},
                {"id": "ind-3", "type": "indicator", "name": "Volume",
                 "config": {}, "position": {"x": 300, "y": 250}, "connections": ["agg-1"]},
                {"id": "agg-1", "type": "aggregate", "name": "Confluence Score",
                 "config": config, "position": {"x": 550, "y": 150}, "connections": ["out-1"]},
                {"id": "out-1", "type": "signal", "name": "Signal Output",
                 "config": {}, "position": {"x": 750, "y": 150}, "connections": []}
            ]
        
        elif auto_type == AutomationType.RISK:
            blocks = [
                {"id": "src-1", "type": "source", "name": "Portfolio Feed",
                 "config": {"exchange": config.get("exchange", "binance")},
                 "position": {"x": 100, "y": 100}, "connections": ["risk-1", "risk-2"]},
                {"id": "risk-1", "type": "risk_check", "name": "Drawdown Check",
                 "config": {"max_drawdown": config.get("max_drawdown", 10)},
                 "position": {"x": 350, "y": 50}, "connections": ["notif-1"]},
                {"id": "risk-2", "type": "risk_check", "name": "Exposure Check",
                 "config": {"max_position": config.get("max_position", 25)},
                 "position": {"x": 350, "y": 200}, "connections": ["notif-1"]},
                {"id": "notif-1", "type": "notification", "name": "Risk Alert",
                 "config": {}, "position": {"x": 600, "y": 125}, "connections": []}
            ]
        
        elif auto_type == AutomationType.BACKTEST:
            blocks = [
                {"id": "src-1", "type": "source", "name": "Historical Data",
                 "config": {"file": config.get("data_file", "")},
                 "position": {"x": 100, "y": 100}, "connections": ["strat-1"]},
                {"id": "strat-1", "type": "indicator", "name": "Strategy Logic",
                 "config": config, "position": {"x": 350, "y": 100}, "connections": ["sim-1"]},
                {"id": "sim-1", "type": "transform", "name": "Trade Simulation",
                 "config": {}, "position": {"x": 600, "y": 100}, "connections": ["out-1"]},
                {"id": "out-1", "type": "output", "name": "Results Report",
                 "config": {}, "position": {"x": 850, "y": 100}, "connections": []}
            ]
        
        return blocks
    
    def get_available_templates(self, auto_type: Optional[AutomationType] = None) -> List[Dict]:
        """Get list of available templates."""
        templates = []
        
        types_to_check = [auto_type] if auto_type else list(ALL_TEMPLATES.keys())
        
        for atype in types_to_check:
            type_templates = ALL_TEMPLATES.get(atype, {})
            for key, tpl in type_templates.items():
                templates.append({
                    "key": key,
                    "name": tpl["name"],
                    "description": tpl["description"],
                    "type": atype.value,
                    "deployment": tpl.get("deployment", DeploymentType.DOCKER).value
                })
        
        return templates
    
    def get_automation_types(self) -> List[Dict]:
        """Get all supported automation types with descriptions."""
        return [
            {"type": "scraper", "name": "Data Scraper", "description": "Collect data from exchanges and APIs", "icon": "📊"},
            {"type": "trading_bot", "name": "Trading Bot", "description": "Automated trading strategies", "icon": "🤖"},
            {"type": "alert", "name": "Alert System", "description": "Price and indicator notifications", "icon": "🔔"},
            {"type": "signal", "name": "Signal Generator", "description": "Multi-factor trading signals", "icon": "📈"},
            {"type": "risk", "name": "Risk Monitor", "description": "Portfolio risk tracking", "icon": "🛡️"},
            {"type": "backtest", "name": "Backtest", "description": "Test strategies on historical data", "icon": "📜"},
        ]


# Singleton
_generator: Optional[AutomationGenerator] = None

def get_automation_generator() -> AutomationGenerator:
    global _generator
    if _generator is None:
        _generator = AutomationGenerator()
    return _generator
