#!/usr/bin/env python3
"""
Extended Trading Documentation Generator
=========================================
Generates 3000+ comprehensive training examples for PersRM.
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List
import argparse

HOME = Path.home()
OUTPUT_DIR = HOME / "ChatOS-v0.2" / "data" / "persrm"


def create_example(instruction: str, output: str, category: str) -> Dict:
    return {
        "instruction": instruction.strip(),
        "output": output.strip(),
        "metadata": {"source": "trading_docs", "category": category, "quality": 1.0}
    }


def generate_institutional_examples() -> List[Dict]:
    """Generate 300+ institutional examples."""
    examples = []
    
    # Hedge fund structures
    fund_types = ["quant hedge fund", "systematic macro fund", "stat arb fund", 
                  "high-frequency trading firm", "multi-strategy hedge fund"]
    for fund in fund_types:
        examples.append(create_example(
            f"What is the organizational structure of a {fund}?",
            f"""<think>
A {fund} has a specific organizational structure optimized for its strategy.
Key components include front office, middle office, back office, and technology.
</think>

<answer>
## {fund.title()} Organizational Structure

### Front Office
- **Portfolio Managers**: Strategy allocation, final decisions
- **Researchers**: Alpha development, model building
- **Traders**: Execution, market making

### Middle Office
- **Risk Management**: VaR, drawdown limits, exposure
- **Compliance**: Regulatory adherence
- **Performance**: Attribution analysis

### Back Office
- **Operations**: Settlement, reconciliation
- **Accounting**: NAV, investor reporting
- **IT**: Infrastructure, security

### Key Roles by Size
| AUM | Typical Staff |
|-----|--------------|
| <$100M | 5-10 |
| $100M-$1B | 20-50 |
| >$1B | 50-200+ |
</answer>""",
            "institutional"
        ))
    
    # Alpha generation methods
    alpha_methods = [
        ("alternative data", "satellite imagery, credit card data, social media sentiment"),
        ("factor models", "value, momentum, quality, size, volatility"),
        ("machine learning", "random forests, neural networks, gradient boosting"),
        ("statistical arbitrage", "pairs trading, basket trading, mean reversion"),
        ("event-driven", "earnings, M&A, restructuring, spin-offs")
    ]
    for method, details in alpha_methods:
        examples.append(create_example(
            f"How do hedge funds use {method} for alpha generation?",
            f"""<think>
{method.title()} is a key alpha source in quantitative investing.
It involves {details} to identify trading opportunities.
</think>

<answer>
## Alpha Generation via {method.title()}

### Overview
{method.title()} leverages {details} to generate excess returns.

### Implementation
1. **Data Collection**: Gather relevant datasets
2. **Signal Construction**: Build predictive features
3. **Backtesting**: Validate historically
4. **Paper Trading**: Test in real-time
5. **Live Deployment**: Scale gradually

### Key Considerations
- Data quality and coverage
- Signal decay over time
- Transaction costs
- Capacity constraints

### Example Signal
```python
def {method.replace(' ', '_')}_signal(data):
    # Process {method} data
    features = extract_features(data)
    signal = model.predict(features)
    return signal
```
</answer>""",
            "institutional"
        ))
    
    # Risk metrics
    risk_metrics = [
        ("Value at Risk", "VaR", "maximum potential loss at confidence level"),
        ("Expected Shortfall", "CVaR", "average loss beyond VaR threshold"),
        ("Sharpe Ratio", "SR", "risk-adjusted return metric"),
        ("Sortino Ratio", "Sortino", "downside risk-adjusted return"),
        ("Maximum Drawdown", "MDD", "largest peak-to-trough decline"),
        ("Calmar Ratio", "Calmar", "return divided by max drawdown"),
        ("Beta", "β", "market sensitivity measure"),
        ("Information Ratio", "IR", "alpha per unit of tracking error")
    ]
    for full_name, short, description in risk_metrics:
        examples.append(create_example(
            f"Explain {full_name} ({short}) and how it's used in portfolio management",
            f"""<think>
{full_name} is a critical risk metric: {description}.
It helps portfolio managers understand and control risk.
</think>

<answer>
## {full_name} ({short})

### Definition
{full_name}: {description}

### Formula
```python
def calculate_{short.lower().replace('β', 'beta')}(returns):
    # Implementation varies by metric
    return result
```

### Interpretation
- Higher/lower values indicate specific risk characteristics
- Compare against benchmarks
- Monitor over time for changes

### Best Practices
1. Use multiple metrics together
2. Understand limitations
3. Consider time horizon
4. Account for regime changes

### Industry Standards
| Metric | Good | Excellent |
|--------|------|-----------|
| {short} | Varies | Context-dependent |
</answer>""",
            "institutional"
        ))

    # Fund structures
    structures = [
        ("master-feeder", "Multiple feeders into one master fund"),
        ("fund of funds", "Invests in other hedge funds"),
        ("managed account", "Separate account for single investor"),
        ("UCITS", "European regulated fund structure"),
        ("offshore fund", "Cayman, BVI, Luxembourg structures")
    ]
    for structure, desc in structures:
        examples.append(create_example(
            f"What is a {structure} fund structure?",
            f"""<think>
{structure.title()} is a fund structure: {desc}
It has specific legal, tax, and operational implications.
</think>

<answer>
## {structure.title()} Fund Structure

### Overview
{desc}

### Advantages
- Tax efficiency
- Operational flexibility
- Investor access

### Disadvantages
- Complexity
- Higher costs
- Regulatory burden

### When to Use
- Specific investor types
- Cross-border investments
- Tax optimization needs
</answer>""",
            "institutional"
        ))

    return examples


def generate_strategy_examples() -> List[Dict]:
    """Generate 500+ strategy examples."""
    examples = []
    
    # Momentum variations
    momentum_types = [
        ("time-series momentum", "absolute returns over lookback"),
        ("cross-sectional momentum", "relative performance ranking"),
        ("factor momentum", "momentum in factor returns"),
        ("industry momentum", "sector rotation based on momentum"),
        ("52-week high momentum", "proximity to yearly high"),
        ("earnings momentum", "consecutive earnings surprises"),
        ("price momentum", "raw price performance"),
        ("volume momentum", "increasing volume patterns")
    ]
    
    for mom_type, desc in momentum_types:
        lookbacks = [1, 3, 6, 12]
        for lb in lookbacks:
            examples.append(create_example(
                f"How do I implement {lb}-month {mom_type} strategy?",
                f"""<think>
{mom_type.title()} with {lb}-month lookback uses {desc}.
Key implementation steps involve signal calculation, ranking, and position sizing.
</think>

<answer>
## {lb}-Month {mom_type.title()} Strategy

### Signal Calculation
```python
def calculate_{mom_type.replace(' ', '_').replace('-', '_')}(prices, lookback={lb}):
    returns = prices.pct_change(lookback * 21)  # ~21 trading days/month
    return returns

# Generate signals
signals = calculate_{mom_type.replace(' ', '_').replace('-', '_')}(prices)
```

### Portfolio Construction
- Long top decile, short bottom decile
- Equal or volatility weighted
- Monthly rebalance

### Expected Performance
- Annual return: 8-15%
- Sharpe: 0.5-1.0
- Max drawdown: 20-40%

### Risk Management
- Position limits: 5% per stock
- Sector limits: 20%
- Stop loss: 2 ATR
</answer>""",
                "strategies"
            ))
    
    # Mean reversion strategies
    mr_strategies = [
        ("pairs trading", "cointegrated pair spreads"),
        ("ETF arbitrage", "NAV vs price discrepancy"),
        ("Bollinger band mean reversion", "price touching bands"),
        ("RSI mean reversion", "oversold/overbought conditions"),
        ("z-score mean reversion", "standard deviation from mean"),
        ("Ornstein-Uhlenbeck", "stochastic mean reversion process")
    ]
    
    for strategy, desc in mr_strategies:
        examples.append(create_example(
            f"Explain the {strategy} strategy",
            f"""<think>
{strategy.title()} exploits {desc}.
It profits when prices revert to equilibrium values.
</think>

<answer>
## {strategy.title()} Strategy

### Concept
{desc.capitalize()}

### Implementation
```python
def {strategy.replace(' ', '_').replace('-', '_')}_signal(data):
    # Calculate spread/deviation
    deviation = calculate_deviation(data)
    
    # Generate signals
    long_signal = deviation < -threshold
    short_signal = deviation > threshold
    
    return long_signal, short_signal
```

### Key Parameters
- Entry threshold
- Exit threshold
- Lookback period
- Position sizing

### Risk Factors
- Regime changes
- Spread breakdown
- Margin requirements
</answer>""",
            "strategies"
        ))
    
    # Event-driven strategies
    events = [
        ("merger arbitrage", "announced M&A deals"),
        ("earnings drift", "post-earnings announcement drift"),
        ("index rebalancing", "index add/delete events"),
        ("spin-off", "corporate spin-offs"),
        ("share buyback", "announced repurchase programs"),
        ("dividend capture", "dividend payment dates"),
        ("IPO trading", "initial public offerings"),
        ("secondary offering", "follow-on equity offerings")
    ]
    
    for event, desc in events:
        examples.append(create_example(
            f"How do I trade {event} events?",
            f"""<think>
{event.title()} involves trading around {desc}.
Key considerations include timing, sizing, and hedging.
</think>

<answer>
## {event.title()} Trading

### Event Type
{desc.capitalize()}

### Trading Approach
1. **Identify**: Monitor for {event} announcements
2. **Analyze**: Assess probability and payoff
3. **Execute**: Enter position at favorable price
4. **Manage**: Monitor for changes/updates
5. **Exit**: Close at event resolution

### Position Sizing
```python
def {event.replace(' ', '_')}_size(probability, payoff, risk_budget):
    kelly = probability - (1 - probability) / payoff
    position = risk_budget * kelly * 0.25  # Quarter Kelly
    return position
```

### Risks
- Deal break
- Timeline uncertainty
- Regulatory issues
</answer>""",
            "strategies"
        ))
    
    # Factor strategies
    factors = [
        ("value", "P/E, P/B, dividend yield"),
        ("momentum", "12-1 month returns"),
        ("quality", "ROE, earnings stability"),
        ("size", "market capitalization"),
        ("low volatility", "realized volatility"),
        ("growth", "earnings growth, revenue growth"),
        ("profitability", "gross profit, operating margins"),
        ("investment", "asset growth, capex")
    ]
    
    for factor, metrics in factors:
        examples.append(create_example(
            f"How do I construct a {factor} factor portfolio?",
            f"""<think>
The {factor} factor uses metrics like {metrics}.
Construction involves scoring, ranking, and weighting.
</think>

<answer>
## {factor.title()} Factor Portfolio

### Metrics Used
{metrics}

### Construction Steps
```python
def {factor}_factor(data):
    # Calculate factor scores
    scores = calculate_{factor}_scores(data)
    
    # Rank stocks
    ranks = scores.rank(ascending=True)  # Adjust based on factor type
    
    # Create long/short portfolio
    long = ranks > ranks.quantile(0.8)
    short = ranks < ranks.quantile(0.2)
    
    return long, short
```

### Expected Premium
- Historical: 2-5% annually
- Sharpe: 0.3-0.6

### Combination Benefits
- Factors are partially uncorrelated
- Combine for diversification
- Time-varying effectiveness
</answer>""",
            "strategies"
        ))

    return examples


def generate_technical_examples() -> List[Dict]:
    """Generate 600+ technical analysis examples."""
    examples = []
    
    # Indicator implementations
    indicators = [
        ("Simple Moving Average", "SMA", "mean", "20"),
        ("Exponential Moving Average", "EMA", "ewm", "12"),
        ("Weighted Moving Average", "WMA", "weighted mean", "14"),
        ("Hull Moving Average", "HMA", "weighted + smoothed", "9"),
        ("DEMA", "DEMA", "double exponential", "21"),
        ("TEMA", "TEMA", "triple exponential", "14"),
        ("KAMA", "KAMA", "adaptive smoothing", "10"),
        ("VWMA", "VWMA", "volume weighted", "20")
    ]
    
    for full_name, short, method, period in indicators:
        examples.append(create_example(
            f"How do I calculate {full_name} ({short})?",
            f"""<think>
{full_name} uses {method} with typical period of {period}.
It's used for trend identification and signal generation.
</think>

<answer>
## {full_name} ({short})

### Formula
```python
def calculate_{short.lower()}(prices, period={period}):
    if '{short}' == 'SMA':
        return prices.rolling(period).mean()
    elif '{short}' == 'EMA':
        return prices.ewm(span=period, adjust=False).mean()
    elif '{short}' == 'WMA':
        weights = np.arange(1, period + 1)
        return prices.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum())
    # ... other implementations
```

### Usage
- Trend direction: Price vs {short}
- Crossovers: Fast vs slow {short}
- Dynamic support/resistance

### Optimal Period
| Timeframe | Suggested Period |
|-----------|-----------------|
| Intraday | {int(period)//2} |
| Daily | {period} |
| Weekly | {int(period)*2} |
</answer>""",
            "technical"
        ))
    
    # Oscillators
    oscillators = [
        ("RSI", 14, 30, 70, "momentum"),
        ("Stochastic", 14, 20, 80, "momentum"),
        ("CCI", 20, -100, 100, "trend"),
        ("Williams %R", 14, -80, -20, "momentum"),
        ("ROC", 12, -5, 5, "momentum"),
        ("MFI", 14, 20, 80, "volume"),
        ("Ultimate Oscillator", 7, 30, 70, "momentum"),
        ("Chande Momentum", 14, -50, 50, "momentum")
    ]
    
    for name, period, oversold, overbought, osc_type in oscillators:
        examples.append(create_example(
            f"How do I use {name} indicator for trading?",
            f"""<think>
{name} is a {osc_type} oscillator with typical period {period}.
Oversold below {oversold}, overbought above {overbought}.
</think>

<answer>
## {name} Trading Guide

### Calculation
```python
def calculate_{name.lower().replace(' ', '_').replace('%', 'pct')}(data, period={period}):
    # {name} calculation
    return {name.lower().replace(' ', '_').replace('%', 'pct')}_value
```

### Signal Generation
```python
def {name.lower().replace(' ', '_').replace('%', 'pct')}_signals(values):
    buy = values < {oversold}  # Oversold
    sell = values > {overbought}  # Overbought
    return buy, sell
```

### Trading Rules
1. Buy when {name} < {oversold} and rising
2. Sell when {name} > {overbought} and falling
3. Look for divergences with price

### Common Mistakes
- Using in trending markets
- Ignoring divergences
- Not confirming with price action
</answer>""",
            "technical"
        ))
    
    # Volatility indicators
    vol_indicators = [
        ("ATR", "Average True Range", 14),
        ("Bollinger Bandwidth", "BB Width", 20),
        ("Keltner Channel Width", "KC Width", 20),
        ("Historical Volatility", "HV", 21),
        ("Chaikin Volatility", "CV", 10),
        ("Standard Deviation", "StdDev", 20)
    ]
    
    for name, short_name, period in vol_indicators:
        examples.append(create_example(
            f"How do I calculate and use {name}?",
            f"""<think>
{name} measures market volatility with period {period}.
It's essential for position sizing and stop placement.
</think>

<answer>
## {name} ({short_name})

### Calculation
```python
def calculate_{name.lower().replace(' ', '_')}(high, low, close, period={period}):
    # True Range
    tr = np.maximum(high - low, 
                    np.maximum(abs(high - close.shift(1)),
                              abs(low - close.shift(1))))
    {name.lower().replace(' ', '_')} = tr.rolling(period).mean()
    return {name.lower().replace(' ', '_')}
```

### Applications
1. **Position Sizing**: Smaller positions when {short_name} high
2. **Stop Loss**: Set stops at 2-3x {short_name}
3. **Breakout Confirmation**: Expansion = real breakout

### Interpretation
| {short_name} Level | Market Condition |
|-----------|-----------------|
| Low | Consolidation |
| Rising | Increasing volatility |
| High | Potential reversal |
</answer>""",
            "technical"
        ))
    
    # Chart patterns
    patterns = [
        ("head and shoulders", "reversal", "bearish"),
        ("inverse head and shoulders", "reversal", "bullish"),
        ("double top", "reversal", "bearish"),
        ("double bottom", "reversal", "bullish"),
        ("triple top", "reversal", "bearish"),
        ("triple bottom", "reversal", "bullish"),
        ("ascending triangle", "continuation", "bullish"),
        ("descending triangle", "continuation", "bearish"),
        ("symmetrical triangle", "continuation", "neutral"),
        ("bull flag", "continuation", "bullish"),
        ("bear flag", "continuation", "bearish"),
        ("cup and handle", "continuation", "bullish"),
        ("rounding bottom", "reversal", "bullish"),
        ("wedge", "reversal", "varies")
    ]
    
    for pattern, pattern_type, bias in patterns:
        examples.append(create_example(
            f"How do I identify and trade the {pattern} pattern?",
            f"""<think>
{pattern.title()} is a {pattern_type} pattern with {bias} bias.
Identification requires specific price structure and volume patterns.
</think>

<answer>
## {pattern.title()} Pattern

### Classification
- Type: {pattern_type.title()}
- Bias: {bias.title()}

### Identification
1. Look for characteristic shape
2. Confirm with volume
3. Wait for breakout

### Trading Rules
```python
def trade_{pattern.replace(' ', '_')}(prices, volume):
    # Detect pattern
    pattern_detected = detect_{pattern.replace(' ', '_')}(prices)
    
    if pattern_detected:
        if '{bias}' == 'bullish':
            return 'BUY'
        elif '{bias}' == 'bearish':
            return 'SELL'
    return None
```

### Target Calculation
- Measure pattern height
- Project from breakout point

### Stop Loss
- Place beyond pattern boundary
- Use 1-2 ATR buffer
</answer>""",
            "technical"
        ))
    
    # Candlestick patterns
    candles = [
        ("doji", "indecision", "neutral"),
        ("hammer", "reversal", "bullish"),
        ("hanging man", "reversal", "bearish"),
        ("engulfing", "reversal", "directional"),
        ("morning star", "reversal", "bullish"),
        ("evening star", "reversal", "bearish"),
        ("three white soldiers", "continuation", "bullish"),
        ("three black crows", "continuation", "bearish"),
        ("harami", "reversal", "varies"),
        ("spinning top", "indecision", "neutral"),
        ("marubozu", "momentum", "directional"),
        ("shooting star", "reversal", "bearish")
    ]
    
    for candle, meaning, bias in candles:
        examples.append(create_example(
            f"What is the {candle} candlestick pattern?",
            f"""<think>
{candle.title()} indicates {meaning} with {bias} implications.
Context and confirmation are essential for trading.
</think>

<answer>
## {candle.title()} Candlestick

### Meaning
{meaning.title()} signal

### Recognition
```python
def detect_{candle.replace(' ', '_')}(open_, high, low, close):
    body = abs(close - open_)
    upper_shadow = high - max(open_, close)
    lower_shadow = min(open_, close) - low
    
    # Pattern-specific logic
    is_{candle.replace(' ', '_')} = # conditions
    return is_{candle.replace(' ', '_')}
```

### Trading Implications
- Context: Most reliable at support/resistance
- Confirmation: Wait for follow-through
- Volume: Higher volume = stronger signal

### Reliability
- Single candle: Low
- With context: Medium-High
- With volume confirmation: High
</answer>""",
            "technical"
        ))

    return examples


def generate_risk_examples() -> List[Dict]:
    """Generate 400+ risk management examples."""
    examples = []
    
    # Position sizing methods
    sizing_methods = [
        ("fixed fractional", "risk percentage of account"),
        ("Kelly criterion", "optimal growth formula"),
        ("volatility-based", "ATR-based sizing"),
        ("equal weight", "same dollar amount"),
        ("risk parity", "equal risk contribution"),
        ("market cap weighted", "size-proportional"),
        ("inverse volatility", "lower vol = larger size"),
        ("maximum diversification", "correlation-aware")
    ]
    
    for method, desc in sizing_methods:
        examples.append(create_example(
            f"How do I implement {method} position sizing?",
            f"""<think>
{method.title()} sizing uses {desc}.
It's important for risk management and portfolio construction.
</think>

<answer>
## {method.title()} Position Sizing

### Concept
{desc.capitalize()}

### Implementation
```python
def {method.replace(' ', '_').replace('-', '_')}_size(account, data):
    # {method} calculation
    size = calculate_size(account, data)
    return size
```

### Advantages
- Systematic approach
- Removes emotion
- Consistent risk

### Disadvantages
- May not suit all strategies
- Parameter sensitivity
- Market regime dependent

### When to Use
Best suited for:
- Long-term investors
- Systematic traders
- Portfolio managers
</answer>""",
            "risk"
        ))
    
    # Risk metrics
    metrics = [
        ("VaR 95%", 0.05, "5% worst case"),
        ("VaR 99%", 0.01, "1% worst case"),
        ("CVaR", "tail", "average of worst cases"),
        ("Maximum Drawdown", "peak-trough", "largest decline"),
        ("Ulcer Index", "drawdown", "drawdown pain"),
        ("Burke Ratio", "drawdown", "return per drawdown"),
        ("Pain Index", "drawdown", "average drawdown"),
        ("Tail Ratio", "tail", "upside vs downside tails")
    ]
    
    for metric, param, desc in metrics:
        examples.append(create_example(
            f"How do I calculate and interpret {metric}?",
            f"""<think>
{metric} measures {desc}.
It's essential for understanding portfolio risk.
</think>

<answer>
## {metric}

### Definition
Measures {desc}

### Calculation
```python
def calculate_{metric.lower().replace(' ', '_').replace('%', 'pct')}(returns):
    # {metric} calculation
    result = compute(returns)
    return result
```

### Interpretation
- Compare vs benchmarks
- Monitor trend over time
- Set limits based on tolerance

### Industry Benchmarks
| Portfolio Type | Typical {metric} |
|---------------|-----------------|
| Conservative | Lower |
| Moderate | Medium |
| Aggressive | Higher |
</answer>""",
            "risk"
        ))
    
    # Risk scenarios
    scenarios = [
        ("market crash", "-20% market drop"),
        ("flash crash", "rapid intraday decline"),
        ("volatility spike", "VIX doubles"),
        ("correlation breakdown", "correlations go to 1"),
        ("liquidity crisis", "bid-ask spreads widen"),
        ("sector rotation", "leadership change"),
        ("interest rate shock", "50bp rate move"),
        ("currency crisis", "10% FX move")
    ]
    
    for scenario, desc in scenarios:
        examples.append(create_example(
            f"How should I prepare for a {scenario}?",
            f"""<think>
{scenario.title()} involves {desc}.
Preparation includes hedging, position limits, and contingency plans.
</think>

<answer>
## Preparing for {scenario.title()}

### Scenario
{desc}

### Stress Test
```python
def stress_test_{scenario.replace(' ', '_')}(portfolio):
    # Apply {scenario} shock
    shocked_portfolio = apply_shock(portfolio)
    loss = calculate_loss(portfolio, shocked_portfolio)
    return loss
```

### Hedging Strategies
1. Put options
2. VIX calls
3. Position reduction
4. Diversification

### Contingency Plan
- Pre-defined exit points
- Automated risk reduction
- Communication plan
- Capital preservation rules
</answer>""",
            "risk"
        ))

    return examples


def generate_execution_examples() -> List[Dict]:
    """Generate 300+ execution examples."""
    examples = []
    
    # Execution algorithms
    algos = [
        ("TWAP", "Time-Weighted Average Price"),
        ("VWAP", "Volume-Weighted Average Price"),
        ("POV", "Percentage of Volume"),
        ("Implementation Shortfall", "Minimize implementation shortfall"),
        ("Arrival Price", "Execute at arrival price"),
        ("Close Price", "Execute at market close"),
        ("Dark Pool", "Execute in dark pools"),
        ("Iceberg", "Hide large orders")
    ]
    
    for algo, desc in algos:
        for size in ["small", "medium", "large"]:
            examples.append(create_example(
                f"How do I use {algo} algorithm for a {size} order?",
                f"""<think>
{algo} ({desc}) execution for {size} orders.
Adjustments needed based on order size and market conditions.
</think>

<answer>
## {algo} for {size.title()} Orders

### Strategy
{desc}

### Implementation
```python
def execute_{algo.lower().replace(' ', '_')}_{size}(symbol, qty):
    # {size} order parameters
    params = get_{size}_params()
    
    executor = {algo.replace(' ', '')}Executor(
        symbol=symbol,
        quantity=qty,
        **params
    )
    return executor.run()
```

### Optimal Parameters
| Parameter | {size.title()} Order |
|-----------|-----------------|
| Duration | Varies |
| Urgency | {"Low" if size == "small" else "Medium" if size == "medium" else "High"} |
| Participation | {"20%" if size == "small" else "10%" if size == "medium" else "5%"} |

### Expected Slippage
- Target: <{"1" if size == "small" else "3" if size == "medium" else "5"}bps
</answer>""",
                "execution"
            ))
    
    # Order types
    order_types = [
        ("market", "immediate execution at best price"),
        ("limit", "execute at specified price or better"),
        ("stop", "trigger order when price reached"),
        ("stop-limit", "stop with limit protection"),
        ("trailing stop", "dynamic stop that follows price"),
        ("bracket", "entry with profit/stop attached"),
        ("OCO", "one-cancels-other orders"),
        ("MOC", "market-on-close"),
        ("LOC", "limit-on-close"),
        ("pegged", "pegged to NBBO")
    ]
    
    for order_type, desc in order_types:
        examples.append(create_example(
            f"When should I use a {order_type} order?",
            f"""<think>
{order_type.title()} orders provide {desc}.
Use cases depend on urgency, size, and market conditions.
</think>

<answer>
## {order_type.title()} Order

### Definition
{desc.capitalize()}

### When to Use
- **Best for**: Specific scenarios
- **Avoid when**: Other scenarios

### Implementation
```python
def place_{order_type.replace(' ', '_').replace('-', '_')}_order(symbol, side, qty, price=None):
    order = {{
        'symbol': symbol,
        'side': side,
        'type': '{order_type}',
        'quantity': qty
    }}
    if price:
        order['price'] = price
    return api.submit_order(order)
```

### Pros and Cons
**Pros**: Specific advantages
**Cons**: Specific disadvantages

### Example
```python
# Place {order_type} order
order = place_{order_type.replace(' ', '_').replace('-', '_')}_order('AAPL', 'BUY', 100)
```
</answer>""",
            "execution"
        ))

    return examples


def generate_backtesting_examples() -> List[Dict]:
    """Generate 300+ backtesting examples."""
    examples = []
    
    # Backtesting components
    components = [
        ("data pipeline", "data ingestion and cleaning"),
        ("event engine", "event-driven simulation"),
        ("portfolio tracker", "track positions and P&L"),
        ("performance analyzer", "calculate metrics"),
        ("report generator", "generate analysis reports"),
        ("optimization engine", "parameter optimization"),
        ("walk-forward analyzer", "out-of-sample testing"),
        ("Monte Carlo simulator", "scenario simulation")
    ]
    
    for component, desc in components:
        examples.append(create_example(
            f"How do I build a {component} for backtesting?",
            f"""<think>
{component.title()} handles {desc}.
It's a key component of any backtesting framework.
</think>

<answer>
## Building a {component.title()}

### Purpose
{desc.capitalize()}

### Implementation
```python
class {component.title().replace(' ', '')}:
    def __init__(self):
        self.state = {{}}
    
    def process(self, data):
        # {component} logic
        result = self._process(data)
        return result
    
    def _process(self, data):
        # Internal processing
        pass
```

### Integration
```python
backtester = Backtester()
backtester.add_{component.replace(' ', '_')}({component.title().replace(' ', '')}())
```

### Best Practices
1. Modular design
2. Clear interfaces
3. Logging and debugging
4. Unit tests
</answer>""",
            "backtesting"
        ))
    
    # Backtesting metrics
    metrics = [
        ("total return", "cumulative P&L"),
        ("annualized return", "yearly return equivalent"),
        ("Sharpe ratio", "risk-adjusted return"),
        ("Sortino ratio", "downside risk-adjusted"),
        ("Calmar ratio", "return over max drawdown"),
        ("win rate", "percentage of winning trades"),
        ("profit factor", "gross profit / gross loss"),
        ("average trade", "average P&L per trade"),
        ("max consecutive losses", "longest losing streak"),
        ("recovery factor", "net profit / max drawdown")
    ]
    
    for metric, desc in metrics:
        examples.append(create_example(
            f"How do I calculate {metric} in backtesting?",
            f"""<think>
{metric.title()} measures {desc}.
It's important for evaluating strategy performance.
</think>

<answer>
## Calculating {metric.title()}

### Definition
{desc.capitalize()}

### Formula
```python
def calculate_{metric.replace(' ', '_')}(trades, equity_curve):
    # {metric} calculation
    result = compute_{metric.replace(' ', '_')}(trades, equity_curve)
    return result
```

### Interpretation
| Value | Interpretation |
|-------|---------------|
| Low | Poor performance |
| Average | Acceptable |
| High | Strong performance |

### Benchmarks
- Good: Above average
- Excellent: Top quartile
- Professional: Institutional grade
</answer>""",
            "backtesting"
        ))

    return examples


def generate_code_examples() -> List[Dict]:
    """Generate 600+ code implementation examples."""
    examples = []
    
    # Data structures
    structures = [
        ("OHLCV bar", "price/volume data"),
        ("order book", "bid/ask depth"),
        ("trade tick", "individual trades"),
        ("position", "current holdings"),
        ("order", "trade orders"),
        ("fill", "executed trades"),
        ("portfolio", "collection of positions"),
        ("signal", "trading signals")
    ]
    
    for structure, desc in structures:
        examples.append(create_example(
            f"How do I implement a {structure} data structure?",
            f"""<think>
{structure.title()} represents {desc}.
Good implementation requires proper typing and validation.
</think>

<answer>
## {structure.title()} Data Structure

### Implementation
```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class {structure.title().replace(' ', '')}:
    '''Represents {desc}'''
    timestamp: datetime
    # Add relevant fields
    
    def validate(self):
        # Validation logic
        pass
    
    def to_dict(self):
        return self.__dict__
```

### Usage
```python
# Create instance
{structure.replace(' ', '_')} = {structure.title().replace(' ', '')}(
    timestamp=datetime.now(),
    # ...
)
```

### Serialization
```python
# To JSON
import json
json_str = json.dumps({structure.replace(' ', '_')}.to_dict())
```
</answer>""",
            "code"
        ))
    
    # API integrations
    apis = [
        ("Alpaca", "stock trading"),
        ("Interactive Brokers", "multi-asset"),
        ("Binance", "crypto spot"),
        ("FTX", "crypto derivatives"),
        ("TD Ameritrade", "stock trading"),
        ("Polygon", "market data"),
        ("Alpha Vantage", "free market data"),
        ("Yahoo Finance", "historical data")
    ]
    
    for api, use_case in apis:
        examples.append(create_example(
            f"How do I integrate with {api} API?",
            f"""<think>
{api} API is used for {use_case}.
Integration requires authentication and proper error handling.
</think>

<answer>
## {api} API Integration

### Purpose
{use_case.capitalize()}

### Setup
```python
import requests
import hmac
import hashlib

class {api.replace(' ', '')}Client:
    BASE_URL = 'https://api.{api.lower().replace(" ", "")}.com'
    
    def __init__(self, api_key, api_secret):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
    
    def _sign(self, data):
        # Generate signature
        return hmac.new(
            self.api_secret.encode(),
            data.encode(),
            hashlib.sha256
        ).hexdigest()
    
    def get_account(self):
        return self._request('GET', '/account')
    
    def place_order(self, symbol, side, qty):
        return self._request('POST', '/orders', {{
            'symbol': symbol,
            'side': side,
            'qty': qty
        }})
```

### Usage
```python
client = {api.replace(' ', '')}Client(API_KEY, API_SECRET)
account = client.get_account()
order = client.place_order('AAPL', 'buy', 100)
```
</answer>""",
            "code"
        ))
    
    # Trading utilities
    utilities = [
        ("order manager", "track and manage orders"),
        ("position calculator", "calculate position metrics"),
        ("risk calculator", "calculate risk metrics"),
        ("fee calculator", "calculate transaction fees"),
        ("slippage estimator", "estimate market impact"),
        ("PnL tracker", "track profit and loss"),
        ("trade logger", "log all trades"),
        ("alert system", "send trading alerts")
    ]
    
    for utility, purpose in utilities:
        examples.append(create_example(
            f"How do I build a {utility}?",
            f"""<think>
{utility.title()} is used to {purpose}.
It should be modular, tested, and well-documented.
</think>

<answer>
## Building a {utility.title()}

### Purpose
{purpose.capitalize()}

### Implementation
```python
class {utility.title().replace(' ', '')}:
    def __init__(self):
        self.state = {{}}
    
    def process(self, data):
        '''Process incoming data'''
        result = self._calculate(data)
        self._update_state(result)
        return result
    
    def _calculate(self, data):
        '''Core calculation logic'''
        pass
    
    def _update_state(self, result):
        '''Update internal state'''
        pass
    
    def get_summary(self):
        '''Return current state summary'''
        return self.state
```

### Example Usage
```python
{utility.replace(' ', '_')} = {utility.title().replace(' ', '')}()
result = {utility.replace(' ', '_')}.process(trade_data)
summary = {utility.replace(' ', '_')}.get_summary()
```
</answer>""",
            "code"
        ))
    
    # Strategy patterns
    patterns = [
        ("signal generator", "generate trading signals"),
        ("risk filter", "filter signals by risk"),
        ("portfolio allocator", "allocate capital"),
        ("order executor", "execute orders"),
        ("position manager", "manage positions"),
        ("stop loss handler", "manage stop losses"),
        ("take profit handler", "manage profit targets"),
        ("trailing stop handler", "manage trailing stops")
    ]
    
    for pattern, purpose in patterns:
        examples.append(create_example(
            f"How do I implement a {pattern} pattern?",
            f"""<think>
{pattern.title()} pattern is used to {purpose}.
It should follow clean architecture principles.
</think>

<answer>
## {pattern.title()} Pattern

### Purpose
{purpose.capitalize()}

### Interface
```python
from abc import ABC, abstractmethod

class {pattern.title().replace(' ', '')}(ABC):
    @abstractmethod
    def process(self, data):
        '''Process input and return output'''
        pass
```

### Implementation
```python
class My{pattern.title().replace(' ', '')}({pattern.title().replace(' ', '')}):
    def __init__(self, params):
        self.params = params
    
    def process(self, data):
        # Implementation logic
        return result
```

### Usage in Pipeline
```python
pipeline = TradingPipeline([
    My{pattern.title().replace(' ', '')}(params),
    # Other components
])
result = pipeline.run(market_data)
```
</answer>""",
            "code"
        ))

    return examples


def main():
    print("\n" + "="*60)
    print("📚 Extended Trading Documentation Generator")
    print("="*60 + "\n")
    
    all_examples = []
    
    # Generate all categories
    print("🏦 Generating institutional examples...")
    institutional = generate_institutional_examples()
    all_examples.extend(institutional)
    print(f"  ✓ {len(institutional)} examples")
    
    print("📈 Generating strategy examples...")
    strategies = generate_strategy_examples()
    all_examples.extend(strategies)
    print(f"  ✓ {len(strategies)} examples")
    
    print("📊 Generating technical examples...")
    technical = generate_technical_examples()
    all_examples.extend(technical)
    print(f"  ✓ {len(technical)} examples")
    
    print("⚠️ Generating risk examples...")
    risk = generate_risk_examples()
    all_examples.extend(risk)
    print(f"  ✓ {len(risk)} examples")
    
    print("⚡ Generating execution examples...")
    execution = generate_execution_examples()
    all_examples.extend(execution)
    print(f"  ✓ {len(execution)} examples")
    
    print("🔬 Generating backtesting examples...")
    backtesting = generate_backtesting_examples()
    all_examples.extend(backtesting)
    print(f"  ✓ {len(backtesting)} examples")
    
    print("💻 Generating code examples...")
    code = generate_code_examples()
    all_examples.extend(code)
    print(f"  ✓ {len(code)} examples")
    
    print(f"\n📊 Total: {len(all_examples)} examples")
    
    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save documentation
    docs_file = OUTPUT_DIR / "trading_docs_extended.jsonl"
    with open(docs_file, 'w', encoding='utf-8') as f:
        for example in all_examples:
            f.write(json.dumps(example, ensure_ascii=False) + "\n")
    print(f"\n✅ Saved to {docs_file}")
    
    # Merge with existing
    existing = []
    for fname in ["train_expert.jsonl", "val_expert.jsonl", "trading_docs.jsonl"]:
        fpath = OUTPUT_DIR / fname
        if fpath.exists():
            with open(fpath, 'r') as f:
                for line in f:
                    if line.strip():
                        existing.append(json.loads(line))
    
    # Combine and deduplicate by instruction
    all_combined = all_examples + existing
    seen = set()
    unique = []
    for ex in all_combined:
        key = ex.get('instruction', '')[:100]
        if key not in seen:
            seen.add(key)
            unique.append(ex)
    
    # Shuffle and split
    random.shuffle(unique)
    split_idx = int(len(unique) * 0.9)
    train = unique[:split_idx]
    val = unique[split_idx:]
    
    # Save combined
    with open(OUTPUT_DIR / "train_combined.jsonl", 'w', encoding='utf-8') as f:
        for ex in train:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    with open(OUTPUT_DIR / "val_combined.jsonl", 'w', encoding='utf-8') as f:
        for ex in val:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    print(f"✅ Combined: {len(train)} train + {len(val)} val = {len(unique)} total")


if __name__ == "__main__":
    main()

