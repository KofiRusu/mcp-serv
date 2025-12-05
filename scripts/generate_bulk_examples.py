#!/usr/bin/env python3
"""
Bulk Example Generator
======================
Generates thousands of trading examples using templates and variations.
"""

import json
import random
from datetime import datetime
from pathlib import Path

HOME = Path.home()
OUTPUT_DIR = HOME / "ChatOS-v0.2" / "data" / "persrm"


def create_example(instruction, output, category):
    return {
        "instruction": instruction.strip(),
        "output": output.strip(),
        "metadata": {"source": "bulk_gen", "category": category, "quality": 1.0}
    }


# ============================================================================
# INDICATOR COMBINATIONS
# ============================================================================

INDICATORS = [
    "RSI", "MACD", "Bollinger Bands", "Moving Average", "Stochastic",
    "ADX", "CCI", "ATR", "OBV", "MFI", "Williams %R", "ROC",
    "VWAP", "EMA", "SMA", "Ichimoku", "Parabolic SAR", "Pivot Points"
]

TIMEFRAMES = ["1-minute", "5-minute", "15-minute", "1-hour", "4-hour", "daily", "weekly"]

ASSETS = [
    "stocks", "forex", "crypto", "futures", "options", "ETFs",
    "commodities", "indices", "bonds"
]

MARKET_CONDITIONS = [
    "trending", "ranging", "volatile", "low volatility", "bullish", "bearish"
]

def generate_indicator_examples():
    examples = []
    
    for indicator in INDICATORS:
        for timeframe in TIMEFRAMES[:4]:  # Limit combinations
            examples.append(create_example(
                f"How do I use {indicator} on {timeframe} charts?",
                f"""<think>
Using {indicator} on {timeframe} charts requires specific parameter adjustments.
Shorter timeframes need faster settings, longer need slower.
</think>

<answer>
## {indicator} on {timeframe.title()} Charts

### Optimal Settings
- Period: {"faster" if "minute" in timeframe else "standard"}
- Adjust thresholds for timeframe volatility

### Signal Interpretation
- Buy signals more frequent on shorter timeframes
- Filter with trend confirmation
- Account for noise in {timeframe} data

### Implementation
```python
def {indicator.lower().replace(" ", "_")}_{timeframe.replace("-", "_")}(data):
    # Calculate {indicator} for {timeframe}
    period = {"7 if 'minute' in timeframe else 14" if "minute" in timeframe else "14"}
    return calculate_{indicator.lower().replace(" ", "_")}(data, period)
```

### Risk Management
- Tighter stops on {timeframe}
- Smaller position sizes for faster timeframes
</answer>""",
                "technical"
            ))
    
    # Indicator combinations
    for i, ind1 in enumerate(INDICATORS[:10]):
        for ind2 in INDICATORS[i+1:i+4]:  # Limit combinations
            examples.append(create_example(
                f"How do I combine {ind1} and {ind2} for better signals?",
                f"""<think>
Combining {ind1} with {ind2} can provide confirmation and reduce false signals.
Each indicator measures different aspects of price action.
</think>

<answer>
## Combining {ind1} + {ind2}

### Strategy
- Use {ind1} for primary signals
- Use {ind2} for confirmation
- Enter only when both agree

### Implementation
```python
def combined_signal(data):
    signal_1 = calculate_{ind1.lower().replace(" ", "_")}(data)
    signal_2 = calculate_{ind2.lower().replace(" ", "_")}(data)
    
    buy = signal_1['buy'] & signal_2['buy']
    sell = signal_1['sell'] & signal_2['sell']
    return buy, sell
```

### Advantages
- Reduced false signals
- Higher probability trades
- Multiple confirmation

### Disadvantages
- Fewer signals
- May miss fast moves
</answer>""",
                "technical"
            ))
    
    return examples


# ============================================================================
# TRADING SCENARIOS
# ============================================================================

def generate_scenario_examples():
    examples = []
    
    scenarios = [
        ("price breaks above resistance", "breakout", "bullish"),
        ("price breaks below support", "breakdown", "bearish"),
        ("RSI shows divergence with price", "reversal", "contra-trend"),
        ("MACD crosses above signal line", "momentum", "bullish"),
        ("volume spikes on up move", "confirmation", "bullish"),
        ("candlestick shows hammer at support", "reversal", "bullish"),
        ("double bottom forms on daily chart", "reversal", "bullish"),
        ("head and shoulders pattern completes", "reversal", "bearish"),
        ("price enters Bollinger Band squeeze", "volatility expansion", "breakout"),
        ("50 MA crosses above 200 MA", "golden cross", "bullish"),
        ("VIX spikes above 30", "fear extreme", "mean reversion"),
        ("earnings beat expectations", "catalyst", "bullish"),
        ("Fed announces rate decision", "macro event", "volatile"),
        ("stock gaps down on news", "gap trade", "reversal potential"),
        ("sector rotation into tech", "sector momentum", "bullish tech")
    ]
    
    for scenario, trade_type, bias in scenarios:
        for asset in ASSETS[:5]:
            examples.append(create_example(
                f"What should I do when {scenario} in {asset}?",
                f"""<think>
When {scenario} in {asset}, this signals a potential {trade_type} opportunity.
The bias is {bias}. Risk management is critical.
</think>

<answer>
## Trading {scenario.title()}

### Signal Type
{trade_type.title()} - {bias.title()}

### Action Plan
1. **Confirm**: Verify with additional indicators
2. **Plan**: Define entry, stop, target
3. **Size**: Calculate position based on risk
4. **Execute**: Enter at optimal price
5. **Manage**: Monitor and adjust

### Entry Criteria
- Primary: {scenario}
- Confirmation: Volume, momentum
- Filter: Market regime

### Risk Management
```python
def trade_{trade_type.replace("-", "_")}(price, stop_distance):
    risk_per_trade = account * 0.02
    position_size = risk_per_trade / stop_distance
    return position_size
```

### Target
- R:R minimum 2:1
- Scale out at levels
- Trail stop after 1R
</answer>""",
                "strategies"
            ))
    
    return examples


# ============================================================================
# ASSET-SPECIFIC EXAMPLES
# ============================================================================

def generate_asset_examples():
    examples = []
    
    asset_details = {
        "stocks": ("equities", "9:30-16:00 EST", "T+2"),
        "forex": ("currency pairs", "24/5", "T+2"),
        "crypto": ("digital assets", "24/7", "instant"),
        "futures": ("derivatives", "23/5", "varies"),
        "options": ("derivatives", "9:30-16:00 EST", "T+1"),
        "ETFs": ("funds", "9:30-16:00 EST", "T+2"),
        "commodities": ("physical", "varies", "varies")
    }
    
    for asset, (type_, hours, settlement) in asset_details.items():
        # General trading guide
        examples.append(create_example(
            f"How do I trade {asset} profitably?",
            f"""<think>
Trading {asset} ({type_}) requires understanding their unique characteristics.
Hours: {hours}, Settlement: {settlement}
</think>

<answer>
## Trading {asset.title()} Guide

### Characteristics
- Type: {type_.title()}
- Trading Hours: {hours}
- Settlement: {settlement}

### Key Strategies
1. Trend following
2. Mean reversion
3. Breakout trading
4. News-based trading

### Risk Factors
- Liquidity
- Volatility
- Leverage
- Correlation

### Best Practices
- Start with demo
- Keep position sizes small
- Use stop losses
- Journal trades
</answer>""",
            "strategies"
        ))
        
        # Specific strategies per asset
        for strategy in ["momentum", "mean reversion", "breakout", "scalping"]:
            examples.append(create_example(
                f"What is the best {strategy} strategy for {asset}?",
                f"""<think>
{strategy.title()} in {asset} needs to account for:
- Market hours ({hours})
- Typical volatility
- Liquidity conditions
</think>

<answer>
## {strategy.title()} Strategy for {asset.title()}

### Overview
Apply {strategy} principles to {asset} markets.

### Implementation
```python
def {asset}_{strategy.replace(" ", "_")}(data):
    # {strategy} logic for {asset}
    signals = calculate_{strategy.replace(" ", "_")}(data)
    return signals
```

### Parameters
- Lookback: Adjusted for {asset}
- Thresholds: Market-specific
- Timing: Based on {hours}

### Expected Performance
- Win rate: 45-55%
- R:R: 1.5-2.5
- Sharpe: 0.5-1.5
</answer>""",
                "strategies"
            ))
    
    return examples


# ============================================================================
# RISK MANAGEMENT SCENARIOS
# ============================================================================

def generate_risk_examples():
    examples = []
    
    risk_scenarios = [
        ("losing streak of 5 trades", "reduce size", "psychology"),
        ("account down 10%", "pause trading", "capital preservation"),
        ("single position up 50%", "take profits", "profit management"),
        ("correlation spike in portfolio", "hedge", "diversification"),
        ("VIX doubles overnight", "reduce exposure", "volatility"),
        ("margin call warning", "close positions", "leverage"),
        ("black swan event", "hedge tail risk", "crisis"),
        ("position gaps against", "accept loss", "gap risk")
    ]
    
    for scenario, action, category in risk_scenarios:
        examples.append(create_example(
            f"What should I do when {scenario}?",
            f"""<think>
When {scenario}, the appropriate response is to {action}.
This is a {category} risk management situation.
</think>

<answer>
## Handling: {scenario.title()}

### Situation
{scenario.capitalize()}

### Recommended Action
{action.capitalize()}

### Implementation
1. Assess current exposure
2. Calculate impact
3. Execute {action}
4. Document lesson

### Prevention
- Set limits in advance
- Monitor continuously
- Have contingency plan

### Recovery
- Review what happened
- Adjust strategy if needed
- Resume with smaller size
</answer>""",
            "risk"
        ))
    
    # Position sizing scenarios
    account_sizes = [1000, 10000, 50000, 100000, 500000]
    risk_levels = [0.5, 1, 2, 3]
    
    for account in account_sizes:
        for risk in risk_levels:
            examples.append(create_example(
                f"How should I size positions with ${account:,} account risking {risk}%?",
                f"""<think>
With ${account:,} account and {risk}% risk per trade:
Risk amount = ${account * risk / 100:,.2f}
Position size depends on stop distance.
</think>

<answer>
## Position Sizing: ${account:,} Account, {risk}% Risk

### Risk Per Trade
${account * risk / 100:,.2f}

### Position Calculator
```python
def calculate_size(entry, stop, risk_amount={account * risk / 100}):
    stop_distance = abs(entry - stop)
    shares = risk_amount / stop_distance
    return int(shares)

# Example
entry = 100
stop = 98
size = calculate_size(entry, stop)  # {int(account * risk / 100 / 2)} shares
```

### Guidelines
- Max {risk}% per trade
- Max {"10" if account < 50000 else "20"}% in correlated positions
- Keep {"20" if account < 50000 else "50"}% cash reserve

### Scaling
As account grows, consider:
- Same % risk (compound growth)
- Fixed $ risk (linear growth)
</answer>""",
                "risk"
            ))
    
    return examples


# ============================================================================
# EXECUTION SCENARIOS
# ============================================================================

def generate_execution_examples():
    examples = []
    
    order_sizes = ["100 shares", "1000 shares", "10000 shares", "100000 shares"]
    execution_urgencies = ["low", "medium", "high", "urgent"]
    
    for size in order_sizes:
        for urgency in execution_urgencies:
            examples.append(create_example(
                f"How do I execute {size} with {urgency} urgency?",
                f"""<think>
Executing {size} with {urgency} urgency requires balancing:
- Market impact
- Time risk
- Execution cost
</think>

<answer>
## Execution: {size}, {urgency.title()} Urgency

### Strategy
{"TWAP over extended period" if urgency == "low" else "VWAP matching volume" if urgency == "medium" else "Aggressive participation" if urgency == "high" else "Immediate market order"}

### Parameters
- Duration: {"4 hours" if urgency == "low" else "2 hours" if urgency == "medium" else "30 minutes" if urgency == "high" else "immediate"}
- Participation: {"5%" if urgency == "low" else "10%" if urgency == "medium" else "25%" if urgency == "high" else "100%"}
- Slippage budget: {"1bp" if urgency == "low" else "3bp" if urgency == "medium" else "10bp" if urgency == "high" else "market"}

### Implementation
```python
executor = OrderExecutor(
    size="{size.split()[0]}",
    urgency="{urgency}",
    algo="{"TWAP" if urgency == "low" else "VWAP" if urgency == "medium" else "POV" if urgency == "high" else "Market"}"
)
executor.run()
```
</answer>""",
                "execution"
            ))
    
    return examples


# ============================================================================
# BACKTESTING SCENARIOS
# ============================================================================

def generate_backtest_examples():
    examples = []
    
    strategies = [
        "moving average crossover",
        "RSI mean reversion",
        "breakout",
        "momentum",
        "pairs trading",
        "mean reversion"
    ]
    
    periods = ["2010-2023", "2015-2023", "2018-2023", "2020-2023"]
    
    for strategy in strategies:
        for period in periods[:2]:
            examples.append(create_example(
                f"How do I backtest a {strategy} strategy from {period}?",
                f"""<think>
Backtesting {strategy} over {period} requires:
- Clean historical data
- Realistic assumptions
- Proper validation
</think>

<answer>
## Backtesting {strategy.title()} ({period})

### Data Requirements
- Daily OHLCV data
- Adjusted for splits/dividends
- Point-in-time universe

### Implementation
```python
from backtester import Backtester

class {strategy.title().replace(" ", "")}Strategy:
    def generate_signals(self, data):
        # {strategy} logic
        return signals

bt = Backtester(
    strategy={strategy.title().replace(" ", "")}Strategy(),
    start="{period.split("-")[0]}-01-01",
    end="{period.split("-")[1]}-12-31"
)
results = bt.run()
```

### Key Metrics
- Total return
- Sharpe ratio
- Max drawdown
- Win rate

### Validation
- Out-of-sample test
- Walk-forward analysis
- Parameter sensitivity
</answer>""",
                "backtesting"
            ))
    
    return examples


# ============================================================================
# CODING EXAMPLES
# ============================================================================

def generate_coding_examples():
    examples = []
    
    # Data operations
    operations = [
        ("load CSV data", "pandas read_csv"),
        ("calculate returns", "pct_change"),
        ("resample to weekly", "resample"),
        ("fill missing values", "fillna"),
        ("merge datasets", "merge/join"),
        ("filter by date", "loc/query"),
        ("calculate rolling statistics", "rolling"),
        ("pivot data", "pivot_table")
    ]
    
    for operation, method in operations:
        examples.append(create_example(
            f"How do I {operation} in Python for trading?",
            f"""<think>
To {operation} in trading applications, use {method}.
This is a common operation in quantitative finance.
</think>

<answer>
## {operation.title()} in Python

### Using {method}
```python
import pandas as pd
import numpy as np

# {operation.title()}
def {operation.replace(" ", "_")}(data):
    result = data.{method.split("/")[0]}()  # or appropriate method
    return result

# Example
df = pd.read_csv('data.csv', parse_dates=['date'], index_col='date')
result = {operation.replace(" ", "_")}(df)
```

### Best Practices
- Handle missing data
- Verify data types
- Check for outliers
- Document transformations
</answer>""",
            "code"
        ))
    
    # Visualization
    charts = [
        "candlestick chart",
        "price with indicators",
        "equity curve",
        "drawdown chart",
        "correlation heatmap",
        "returns distribution",
        "rolling Sharpe",
        "position heatmap"
    ]
    
    for chart in charts:
        examples.append(create_example(
            f"How do I create a {chart} in Python?",
            f"""<think>
Creating a {chart} requires appropriate visualization library.
matplotlib, plotly, or mplfinance depending on chart type.
</think>

<answer>
## Creating {chart.title()}

### Implementation
```python
import matplotlib.pyplot as plt
import plotly.graph_objects as go

def plot_{chart.replace(" ", "_")}(data):
    fig = go.Figure()
    
    # Add traces for {chart}
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        name='{chart}'
    ))
    
    fig.update_layout(
        title='{chart.title()}',
        xaxis_title='Date',
        yaxis_title='Value'
    )
    
    return fig

# Usage
fig = plot_{chart.replace(" ", "_")}(my_data)
fig.show()
```

### Customization
- Add annotations
- Multiple subplots
- Interactive features
</answer>""",
            "code"
        ))
    
    return examples


# ============================================================================
# PSYCHOLOGY EXAMPLES
# ============================================================================

def generate_psychology_examples():
    examples = []
    
    biases = [
        ("loss aversion", "holding losers too long", "set hard stops"),
        ("overconfidence", "trading too large", "use systematic sizing"),
        ("recency bias", "overweighting recent data", "use longer lookbacks"),
        ("confirmation bias", "seeking confirming info", "actively seek contrary views"),
        ("anchoring", "fixating on entry price", "focus on current setup"),
        ("FOMO", "chasing after missing move", "wait for pullbacks"),
        ("revenge trading", "trying to recover losses", "take break after losses"),
        ("analysis paralysis", "unable to pull trigger", "use systematic rules")
    ]
    
    for bias, symptom, solution in biases:
        examples.append(create_example(
            f"How do I overcome {bias} in trading?",
            f"""<think>
{bias.title()} manifests as {symptom}.
The solution is to {solution}.
</think>

<answer>
## Overcoming {bias.title()}

### Symptom
{symptom.capitalize()}

### Impact
- Poor risk management
- Suboptimal returns
- Emotional stress

### Solution
{solution.capitalize()}

### Implementation
1. Recognize the bias
2. Create rules to counter
3. Use systematic approach
4. Review regularly

### Prevention
- Trading journal
- Predefined rules
- Accountability partner
- Regular self-assessment
</answer>""",
            "psychology"
        ))
    
    return examples


def main():
    print("\n" + "="*60)
    print("📚 Bulk Example Generator")
    print("="*60 + "\n")
    
    all_examples = []
    
    print("📊 Generating indicator examples...")
    indicator_ex = generate_indicator_examples()
    all_examples.extend(indicator_ex)
    print(f"  ✓ {len(indicator_ex)} examples")
    
    print("📈 Generating scenario examples...")
    scenario_ex = generate_scenario_examples()
    all_examples.extend(scenario_ex)
    print(f"  ✓ {len(scenario_ex)} examples")
    
    print("💹 Generating asset examples...")
    asset_ex = generate_asset_examples()
    all_examples.extend(asset_ex)
    print(f"  ✓ {len(asset_ex)} examples")
    
    print("⚠️ Generating risk examples...")
    risk_ex = generate_risk_examples()
    all_examples.extend(risk_ex)
    print(f"  ✓ {len(risk_ex)} examples")
    
    print("⚡ Generating execution examples...")
    exec_ex = generate_execution_examples()
    all_examples.extend(exec_ex)
    print(f"  ✓ {len(exec_ex)} examples")
    
    print("🔬 Generating backtest examples...")
    backtest_ex = generate_backtest_examples()
    all_examples.extend(backtest_ex)
    print(f"  ✓ {len(backtest_ex)} examples")
    
    print("💻 Generating coding examples...")
    code_ex = generate_coding_examples()
    all_examples.extend(code_ex)
    print(f"  ✓ {len(code_ex)} examples")
    
    print("🧠 Generating psychology examples...")
    psych_ex = generate_psychology_examples()
    all_examples.extend(psych_ex)
    print(f"  ✓ {len(psych_ex)} examples")
    
    print(f"\n📊 Total new: {len(all_examples)} examples")
    
    # Save bulk examples
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    bulk_file = OUTPUT_DIR / "bulk_examples.jsonl"
    with open(bulk_file, 'w', encoding='utf-8') as f:
        for ex in all_examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    print(f"\n✅ Saved to {bulk_file}")
    
    # Load all existing examples
    existing = []
    for fname in OUTPUT_DIR.glob("*.jsonl"):
        if fname.name != "bulk_examples.jsonl":
            with open(fname, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            existing.append(json.loads(line))
                        except:
                            pass
    
    # Combine
    all_combined = all_examples + existing
    
    # Deduplicate
    seen = set()
    unique = []
    for ex in all_combined:
        key = ex.get('instruction', '')[:80]
        if key and key not in seen:
            seen.add(key)
            unique.append(ex)
    
    # Shuffle and split
    random.shuffle(unique)
    split_idx = int(len(unique) * 0.9)
    train = unique[:split_idx]
    val = unique[split_idx:]
    
    # Save final combined files
    with open(OUTPUT_DIR / "train_combined.jsonl", 'w', encoding='utf-8') as f:
        for ex in train:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    with open(OUTPUT_DIR / "val_combined.jsonl", 'w', encoding='utf-8') as f:
        for ex in val:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    print(f"✅ Final combined: {len(train)} train + {len(val)} val = {len(unique)} total unique")


if __name__ == "__main__":
    main()

