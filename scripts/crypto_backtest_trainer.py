#!/usr/bin/env python3
"""
Crypto Trading Strategy Backtesting & Training Data Generator
==============================================================

Continuously backtests crypto trading strategies and generates
high-quality training examples for PersRM model training.

Features:
- Multiple crypto strategy implementations
- Realistic backtest simulation with slippage, fees
- Automatic training data generation from results
- Continuous loop for ongoing dataset growth
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
from typing import Dict, List, Tuple

HOME = Path.home()
OUTPUT_DIR = HOME / "ChatOS-v0.2" / "data" / "persrm"
BACKTEST_LOG = HOME / "ChatOS-v0.2" / "logs" / "backtest.log"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BACKTEST_LOG.parent.mkdir(parents=True, exist_ok=True)


class CryptoPrice:
    """Simulated OHLCV price data for crypto."""
    def __init__(self, symbol="BTC/USDT", timeframe="1h"):
        self.symbol = symbol
        self.timeframe = timeframe
        self.current_price = self._initial_price()
        self.history = []
    
    def _initial_price(self):
        prices = {"BTC/USDT": 45000, "ETH/USDT": 2500, "SOL/USDT": 150}
        return prices.get(self.symbol, 100)
    
    def generate_candle(self):
        """Generate realistic OHLCV candle."""
        volatility = 0.02  # 2% volatility
        change = np.random.normal(0, volatility)
        
        open_price = self.current_price
        close_price = open_price * (1 + change)
        high_price = max(open_price, close_price) * (1 + abs(np.random.normal(0, volatility/2)))
        low_price = min(open_price, close_price) * (1 - abs(np.random.normal(0, volatility/2)))
        volume = np.random.uniform(100, 1000)
        
        candle = {
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": round(volume, 2)
        }
        
        self.history.append(candle)
        self.current_price = close_price
        return candle


class StrategyBacktester:
    """Backtests crypto trading strategies."""
    
    def __init__(self, symbol="BTC/USDT", initial_capital=10000):
        self.symbol = symbol
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.trades = []
        self.positions = []
        self.prices = CryptoPrice(symbol)
        self.fees = 0.001  # 0.1% fees
        self.slippage = 0.0005  # 0.05% slippage
    
    def execute_backtest(self, num_candles=100, strategy_type="momentum"):
        """Run backtest on simulated data."""
        for i in range(num_candles):
            candle = self.prices.generate_candle()
            
            # Generate trading signal
            signal = self._get_signal(strategy_type, i)
            
            # Execute if signal
            if signal == "BUY" and len(self.positions) == 0:
                self._open_position("LONG", candle)
            elif signal == "SELL" and len(self.positions) > 0:
                self._close_position("LONG", candle)
        
        return self._generate_backtest_result()
    
    def _get_signal(self, strategy_type, bar_index):
        """Generate trading signal based on strategy."""
        if strategy_type == "momentum":
            if bar_index < 2:
                return None
            recent = self.prices.history[-3:]
            if recent[-1]["close"] > recent[-2]["close"] > recent[-3]["close"]:
                return "BUY"
            elif recent[-1]["close"] < recent[-2]["close"] < recent[-3]["close"]:
                return "SELL"
        
        elif strategy_type == "mean_reversion":
            if len(self.prices.history) < 5:
                return None
            recent = self.prices.history[-5:]
            closes = [c["close"] for c in recent]
            avg = np.mean(closes)
            current = self.prices.current_price
            if current < avg * 0.98:
                return "BUY"
            elif current > avg * 1.02:
                return "SELL"
        
        elif strategy_type == "rsi":
            if len(self.prices.history) < 14:
                return None
            closes = [c["close"] for c in self.prices.history[-14:]]
            deltas = np.diff(closes)
            gains = np.mean([d for d in deltas if d > 0])
            losses = np.mean([-d for d in deltas if d < 0])
            rs = gains / (losses + 1e-6)
            rsi = 100 - (100 / (1 + rs))
            
            if rsi < 30:
                return "BUY"
            elif rsi > 70:
                return "SELL"
        
        return None
    
    def _open_position(self, side, candle):
        """Open a trading position."""
        entry_price = candle["close"] * (1 + self.slippage)
        qty = (self.capital * 0.95) / entry_price  # Use 95% of capital
        cost = qty * entry_price * (1 + self.fees)
        
        self.positions.append({
            "side": side,
            "entry_price": entry_price,
            "quantity": qty,
            "entry_time": len(self.prices.history),
            "status": "OPEN"
        })
        
        self.capital -= cost
        self.trades.append({
            "type": "OPEN",
            "side": side,
            "price": entry_price,
            "quantity": qty,
            "capital_after": self.capital
        })
    
    def _close_position(self, side, candle):
        """Close a trading position."""
        if not self.positions:
            return
        
        pos = self.positions[-1]
        if pos["side"] != side or pos["status"] != "OPEN":
            return
        
        exit_price = candle["close"] * (1 - self.slippage)
        proceeds = pos["quantity"] * exit_price * (1 - self.fees)
        profit = proceeds - (pos["quantity"] * pos["entry_price"])
        
        self.capital += proceeds
        pos["status"] = "CLOSED"
        pos["exit_price"] = exit_price
        pos["exit_time"] = len(self.prices.history)
        pos["profit"] = profit
        
        self.trades.append({
            "type": "CLOSE",
            "price": exit_price,
            "profit": profit,
            "roi": (profit / (pos["quantity"] * pos["entry_price"])) * 100,
            "capital_after": self.capital
        })
    
    def _generate_backtest_result(self):
        """Generate comprehensive backtest results."""
        closed_trades = [t for t in self.trades if t["type"] == "CLOSE"]
        
        if not closed_trades:
            return None
        
        profits = [t["profit"] for t in closed_trades]
        total_profit = sum(profits)
        win_count = len([p for p in profits if p > 0])
        
        return {
            "symbol": self.symbol,
            "initial_capital": self.initial_capital,
            "final_capital": self.capital,
            "total_profit": total_profit,
            "roi": (total_profit / self.initial_capital) * 100,
            "trades": len(closed_trades),
            "wins": win_count,
            "win_rate": (win_count / len(closed_trades)) * 100 if closed_trades else 0,
            "avg_profit": np.mean(profits) if profits else 0,
            "max_profit": max(profits) if profits else 0,
            "max_loss": min(profits) if profits else 0,
            "profit_factor": sum([p for p in profits if p > 0]) / abs(sum([p for p in profits if p < 0])) if any(p < 0 for p in profits) else float('inf')
        }


def generate_training_example_from_backtest(backtest_result: Dict, strategy_type: str) -> Dict:
    """Convert backtest result into training example."""
    
    roi = backtest_result["roi"]
    win_rate = backtest_result["win_rate"]
    trades = backtest_result["trades"]
    profit_factor = backtest_result["profit_factor"]
    
    instruction = f"Analyze {strategy_type} strategy backtest on {backtest_result['symbol']}"
    
    output = f"""<think>
Backtest results show:
- {trades} trades executed
- {win_rate:.1f}% win rate
- ROI: {roi:.2f}%
- Profit factor: {profit_factor:.2f}
- Average profit per trade: ${backtest_result['avg_profit']:.2f}

Analysis: {'Strategy profitable' if roi > 0 else 'Strategy unprofitable'}.
Key metrics indicate {'strong' if win_rate > 60 and roi > 5 else 'moderate' if roi > 0 else 'poor'} performance.
</think>

<answer>
## {strategy_type.title()} Strategy Analysis

### Performance Metrics
- **Total Trades**: {trades}
- **Win Rate**: {win_rate:.1f}%
- **ROI**: {roi:.2f}%
- **Profit Factor**: {profit_factor:.2f}x
- **Average Trade P&L**: ${backtest_result['avg_profit']:.2f}

### Risk Analysis
- **Best Trade**: +${backtest_result['max_profit']:.2f}
- **Worst Trade**: -${abs(backtest_result['max_loss']):.2f}
- **Capital Risk**: {(abs(backtest_result['max_loss']) / backtest_result['initial_capital']) * 100:.2f}%

### Insights
{'✅ Positive ROI - Strategy shows profitability' if roi > 0 else '❌ Negative ROI - Strategy needs refinement'}
{'✅ Above 50% win rate - More winners than losers' if win_rate > 50 else '❌ Below 50% win rate - Need better signal generation'}
{'✅ Profit factor > 1.5 - Good risk/reward' if profit_factor > 1.5 else '⚠️ Profit factor needs improvement'}

### Recommendations
- {'Increase position sizing - strategy profitable' if roi > 5 else 'Optimize signal parameters'}
- {'Add stop losses - max drawdown ${:.2f}'.format(abs(backtest_result['max_loss'])) if backtest_result['max_loss'] < -1000 else 'Risk management adequate'}
- {'Consider scaling strategy' if win_rate > 55 else 'Add confirmation filters'}
</answer>"""
    
    return {
        "instruction": instruction,
        "output": output,
        "metadata": {
            "source": "crypto_backtest",
            "category": "strategy_analysis",
            "strategy_type": strategy_type,
            "roi": roi,
            "win_rate": win_rate,
            "quality": 1.0
        }
    }


def run_continuous_backtesting(num_runs=5):
    """Run continuous backtesting loop."""
    
    print("\n" + "="*60)
    print("Crypto Trading Backtesting & Training Data Generator")
    print("="*60 + "\n")
    
    all_examples = []
    strategies = ["momentum", "mean_reversion", "rsi"]
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
    
    for run in range(num_runs):
        print(f"📊 Run {run+1}/{num_runs}")
        
        for strategy in strategies:
            for symbol in symbols:
                # Run backtest
                backtester = StrategyBacktester(symbol=symbol, initial_capital=10000)
                result = backtester.execute_backtest(num_candles=100, strategy_type=strategy)
                
                if result:
                    # Generate training example
                    example = generate_training_example_from_backtest(result, strategy)
                    all_examples.append(example)
                    
                    # Log result
                    print(f"  ✓ {strategy} on {symbol}: ROI {result['roi']:.2f}%, WR {result['win_rate']:.1f}%")
    
    print(f"\n✅ Generated {len(all_examples)} training examples")
    
    # Save to training data
    if all_examples:
        output_file = OUTPUT_DIR / "backtest_training.jsonl"
        with open(output_file, 'w') as f:
            for ex in all_examples:
                f.write(json.dumps(ex) + "\n")
        
        print(f"✅ Saved to {output_file}")
        
        # Merge with existing training data
        merge_with_existing(all_examples, output_file)
    
    return all_examples


def merge_with_existing(new_examples: List[Dict], output_file: Path):
    """Merge backtest examples with existing training data."""
    
    all_examples = list(new_examples)
    
    # Load existing
    for fname in OUTPUT_DIR.glob("train*.jsonl"):
        if fname.name not in ["train_final.jsonl", "train_combined.jsonl"]:
            try:
                with open(fname) as f:
                    for line in f:
                        if line.strip():
                            all_examples.append(json.loads(line))
            except:
                pass
    
    # Deduplicate
    seen = set()
    unique = []
    for ex in all_examples:
        key = ex.get('instruction', '')[:50]
        if key and key not in seen:
            seen.add(key)
            unique.append(ex)
    
    # Save merged
    random.shuffle(unique)
    split = int(len(unique) * 0.9)
    
    with open(OUTPUT_DIR / "train_with_backtest.jsonl", 'w') as f:
        for ex in unique[:split]:
            f.write(json.dumps(ex) + "\n")
    
    with open(OUTPUT_DIR / "val_with_backtest.jsonl", 'w') as f:
        for ex in unique[split:]:
            f.write(json.dumps(ex) + "\n")
    
    print(f"📊 Merged dataset: {len(unique)} total examples ({split} train, {len(unique)-split} val)")


if __name__ == "__main__":
    # Run 5 cycles of backtesting
    examples = run_continuous_backtesting(num_runs=5)
    
    print("\n" + "="*60)
    print("✅ Backtest Training Data Generation Complete")
    print("="*60)

