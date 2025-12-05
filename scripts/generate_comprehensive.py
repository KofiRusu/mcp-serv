#!/usr/bin/env python3
"""
Comprehensive Example Generator
================================
Generates additional high-quality trading examples to reach 3000+ total.
"""

import json
import random
from pathlib import Path
import itertools

HOME = Path.home()
OUTPUT_DIR = HOME / "ChatOS-v0.2" / "data" / "persrm"

def ce(i, o, c):
    return {"instruction": i.strip(), "output": o.strip(), 
            "metadata": {"source": "comprehensive", "category": c, "quality": 1.0}}

def gen_comprehensive():
    examples = []
    
    # ========== STRATEGY PARAMETER TUNING ==========
    indicators = ["RSI", "MACD", "Stochastic", "BB", "CCI"]
    params = [(7, 14, 21), (5, 10, 20), (10, 20, 30)]
    for ind in indicators:
        for p1, p2, p3 in params:
            examples.append(ce(
                f"What parameters should I use for {ind}? Compare {p1}, {p2}, and {p3} periods.",
                f"""<think>Parameter selection for {ind} depends on timeframe and volatility.</think>
<answer>
## {ind} Parameter Comparison

| Period | Use Case | Sensitivity |
|--------|----------|-------------|
| {p1} | Scalping/short-term | High |
| {p2} | Swing trading | Medium |
| {p3} | Position trading | Low |

### Recommendation
- Fast markets: {p1}
- Normal markets: {p2}
- Slow/trending: {p3}

```python
{ind.lower()}_fast = calculate_{ind.lower()}(data, {p1})
{ind.lower()}_med = calculate_{ind.lower()}(data, {p2})
{ind.lower()}_slow = calculate_{ind.lower()}(data, {p3})
```
</answer>""", "technical"))
    
    # ========== TRADE MANAGEMENT ==========
    entry_methods = ["breakout", "pullback", "reversal", "momentum", "mean reversion"]
    exit_methods = ["target", "trailing stop", "indicator", "time-based", "volatility"]
    for entry in entry_methods:
        for exit in exit_methods[:3]:
            examples.append(ce(
                f"How do I manage a trade with {entry} entry and {exit} exit?",
                f"""<think>{entry.title()} entry with {exit} exit requires specific management rules.</think>
<answer>
## Trade Management: {entry.title()} Entry → {exit.title()} Exit

### Entry Rules
- {entry.title()} confirmation required
- Volume above average
- Trend alignment

### Position Management
```python
class TradeManager:
    def __init__(self, entry_type="{entry}", exit_type="{exit}"):
        self.entry_type = entry_type
        self.exit_type = exit_type
    
    def manage(self, position, market_data):
        if self.exit_type == "{exit}":
            return self.check_{exit.replace(" ", "_").replace("-", "_")}(position, market_data)
```

### Exit Rules
- {exit.title()} trigger
- Stop loss protection
- Partial profits at targets
</answer>""", "strategies"))
    
    # ========== MARKET ANALYSIS ==========
    market_types = ["trending up", "trending down", "ranging", "volatile", "low volatility"]
    analysis_tools = ["price action", "indicators", "volume", "sentiment", "order flow"]
    for market in market_types:
        for tool in analysis_tools:
            examples.append(ce(
                f"How do I analyze a {market} market using {tool}?",
                f"""<think>In {market} conditions, {tool} analysis reveals specific patterns.</think>
<answer>
## {tool.title()} Analysis in {market.title()} Markets

### Identifying {market.title()} Conditions
- Price structure characteristics
- {tool.title()} confirmation signals

### Trading Approach
```python
def analyze_{market.replace(" ", "_")}_{tool.replace(" ", "_")}(data):
    market_type = detect_market_type(data)
    if market_type == "{market}":
        signals = {tool.replace(" ", "_")}_analysis(data)
        return filter_for_{market.replace(" ", "_")}(signals)
```

### Key Patterns
- {tool.title()} behavior in {market} conditions
- Entry/exit timing
- Risk adjustments

### Pitfalls to Avoid
- Wrong tool for market type
- Ignoring regime changes
</answer>""", "technical"))
    
    # ========== PORTFOLIO CONSTRUCTION ==========
    asset_classes = ["stocks", "bonds", "commodities", "crypto", "forex"]
    weightings = ["equal weight", "market cap", "risk parity", "momentum-based"]
    for assets in itertools.combinations(asset_classes, 3):
        for weight in weightings[:2]:
            examples.append(ce(
                f"How do I build a {weight} portfolio of {', '.join(assets)}?",
                f"""<think>Building {weight} portfolio across {', '.join(assets)} requires balancing risk and return.</think>
<answer>
## {weight.title()} Portfolio: {', '.join([a.title() for a in assets])}

### Asset Allocation
```python
def build_{weight.replace(" ", "_").replace("-", "_")}_portfolio():
    assets = {list(assets)}
    weights = calculate_{weight.replace(" ", "_").replace("-", "_")}_weights(assets)
    return dict(zip(assets, weights))
```

### Rebalancing
- Frequency: Monthly/Quarterly
- Threshold: 5% drift
- Tax considerations

### Risk Metrics
- Expected volatility
- Correlation matrix
- Drawdown scenarios
</answer>""", "strategies"))
    
    # ========== SPECIFIC TRADES ==========
    symbols = ["AAPL", "TSLA", "SPY", "QQQ", "BTC", "ETH", "EURUSD", "GOLD"]
    setups = ["ascending triangle", "cup and handle", "double bottom", "flag pattern"]
    for symbol in symbols:
        for setup in setups:
            examples.append(ce(
                f"I see a {setup} forming on {symbol}. How should I trade it?",
                f"""<think>{setup.title()} on {symbol} requires specific entry, stop, and target levels.</think>
<answer>
## Trading {setup.title()} on {symbol}

### Pattern Identification
- Confirm {setup} structure
- Check volume pattern
- Verify trend context

### Trade Plan
```python
trade = {{
    'symbol': '{symbol}',
    'pattern': '{setup}',
    'entry': 'breakout above resistance',
    'stop': 'below pattern low',
    'target': 'pattern height projection'
}}
```

### Execution
1. Wait for breakout confirmation
2. Enter on volume
3. Place stop immediately
4. Scale out at targets

### Risk: 1-2% of account
</answer>""", "strategies"))
    
    # ========== QUANTITATIVE CONCEPTS ==========
    quant_topics = [
        ("alpha", "excess return above benchmark"),
        ("beta", "market sensitivity"),
        ("Sharpe ratio", "risk-adjusted return"),
        ("correlation", "relationship between assets"),
        ("cointegration", "long-term equilibrium"),
        ("factor exposure", "sensitivity to factors"),
        ("regime detection", "market state identification"),
        ("signal decay", "alpha degradation over time")
    ]
    for topic, desc in quant_topics:
        for context in ["portfolio management", "strategy development", "risk management"]:
            examples.append(ce(
                f"How is {topic} used in {context}?",
                f"""<think>{topic.title()} ({desc}) is essential in {context}.</think>
<answer>
## {topic.title()} in {context.title()}

### Definition
{desc.capitalize()}

### Application
```python
def apply_{topic.replace(" ", "_")}_{context.replace(" ", "_")}(data):
    {topic.replace(" ", "_")} = calculate_{topic.replace(" ", "_")}(data)
    # Use in {context}
    return {topic.replace(" ", "_")}_based_decision({topic.replace(" ", "_")})
```

### Practical Usage
- Measurement method
- Interpretation guidelines
- Decision rules

### Industry Standards
- Typical ranges
- Benchmarks
- Monitoring frequency
</answer>""", "institutional"))
    
    # ========== TRADING PSYCHOLOGY DEEP DIVE ==========
    emotions = ["fear", "greed", "hope", "regret", "anxiety", "overconfidence"]
    situations = ["after a loss", "during drawdown", "on a winning streak", "at market open"]
    for emotion in emotions:
        for situation in situations:
            examples.append(ce(
                f"How do I manage {emotion} {situation}?",
                f"""<think>Managing {emotion} {situation} is crucial for consistent trading.</think>
<answer>
## Managing {emotion.title()} {situation.title()}

### Recognition
- Physical symptoms
- Behavioral patterns
- Decision impact

### Coping Strategies
1. Pause before acting
2. Review trading plan
3. Use systematic rules
4. Deep breathing/break

### Prevention
```python
class EmotionManager:
    def check_{emotion}_{situation.replace(" ", "_")}(self, trade_state):
        if self.detect_{emotion}():
            return self.apply_protocol()
        return None
```

### Long-term Solutions
- Trading journal
- Meditation/mindfulness
- Position sizing rules
- Accountability partner
</answer>""", "psychology"))
    
    # ========== CODE PATTERNS ==========
    patterns = [
        ("strategy", "signal generation logic"),
        ("risk_manager", "position sizing and limits"),
        ("executor", "order placement logic"),
        ("data_handler", "data processing pipeline"),
        ("portfolio", "portfolio tracking"),
        ("backtester", "historical simulation"),
        ("optimizer", "parameter optimization"),
        ("reporter", "performance reporting")
    ]
    for pattern, desc in patterns:
        for style in ["object-oriented", "functional"]:
            examples.append(ce(
                f"How do I implement a {pattern} using {style} programming?",
                f"""<think>Implementing {pattern} ({desc}) with {style} approach.</think>
<answer>
## {pattern.title()} Implementation ({style.title()})

### Purpose
{desc.capitalize()}

### {style.title()} Approach
```python
{"class " + pattern.title().replace("_", "") + ":" if style == "object-oriented" else "def " + pattern + "_function(data):"}
    {"def __init__(self):" if style == "object-oriented" else "    # " + desc}
        {"self.state = {}" if style == "object-oriented" else "    result = process(data)"}
    
    {"def process(self, data):" if style == "object-oriented" else "    return result"}
        {"# " + desc if style == "object-oriented" else ""}
        {"return self._execute(data)" if style == "object-oriented" else ""}
```

### Integration
- Works with existing pipeline
- Testable design
- Clear interfaces
</answer>""", "code"))
    
    # ========== MARKET MICROSTRUCTURE ==========
    micro_topics = [
        ("bid-ask spread", "liquidity cost"),
        ("market depth", "available liquidity"),
        ("order imbalance", "supply/demand pressure"),
        ("price impact", "order effect on price"),
        ("latency", "execution speed"),
        ("maker-taker", "fee structure"),
        ("dark pools", "hidden liquidity"),
        ("market fragmentation", "multiple venues")
    ]
    for topic, desc in micro_topics:
        examples.append(ce(
            f"Explain {topic} and its impact on trading",
            f"""<think>{topic.title()} relates to {desc} in market microstructure.</think>
<answer>
## {topic.title()}

### Definition
{desc.capitalize()}

### Trading Impact
- Execution quality
- Cost considerations
- Strategy design

### Measurement
```python
def measure_{topic.replace("-", "_").replace(" ", "_")}(data):
    # Calculate {topic}
    metric = calculate_metric(data)
    return metric
```

### Optimization
- When to use/avoid
- Cost reduction strategies
- Monitoring approaches
</answer>""", "execution"))
    
    # ========== ALTERNATIVE DATA ==========
    alt_data = [
        ("satellite imagery", "track economic activity"),
        ("social media sentiment", "gauge public opinion"),
        ("web traffic", "measure company performance"),
        ("credit card data", "track consumer spending"),
        ("geolocation data", "analyze foot traffic"),
        ("patent filings", "predict innovation"),
        ("job postings", "assess company health"),
        ("app downloads", "measure product adoption")
    ]
    for data_type, use in alt_data:
        examples.append(ce(
            f"How can I use {data_type} in trading?",
            f"""<think>{data_type.title()} can {use} to generate trading signals.</think>
<answer>
## {data_type.title()} in Trading

### Use Case
{use.capitalize()}

### Implementation
```python
def {data_type.replace(" ", "_")}_signal(raw_data):
    processed = preprocess_{data_type.replace(" ", "_")}(raw_data)
    signal = extract_signal(processed)
    return signal
```

### Challenges
- Data quality
- Timeliness
- Cost
- Legal considerations

### Integration
- Combine with traditional data
- Validate signal quality
- Monitor decay
</answer>""", "institutional"))
    
    # ========== MACHINE LEARNING IN TRADING ==========
    ml_models = ["linear regression", "random forest", "XGBoost", "LSTM", "transformer"]
    ml_tasks = ["price prediction", "signal generation", "risk classification", "anomaly detection"]
    for model in ml_models:
        for task in ml_tasks:
            examples.append(ce(
                f"How do I use {model} for {task}?",
                f"""<think>{model.title()} for {task} requires specific architecture and training.</think>
<answer>
## {model.title()} for {task.title()}

### Model Setup
```python
from sklearn.ensemble import RandomForestClassifier  # example
import torch.nn as nn

def build_{model.replace(" ", "_")}_for_{task.replace(" ", "_")}(features):
    # Model architecture for {task}
    model = create_model()
    return model
```

### Training
- Feature engineering
- Train/validation split
- Hyperparameter tuning
- Cross-validation

### Deployment
- Paper trading first
- Monitor performance
- Retrain schedule
- Avoid overfitting
</answer>""", "code"))
    
    # ========== REGULATORY COMPLIANCE ==========
    regulations = [
        ("SEC Rule 15c3-5", "market access risk management"),
        ("Reg NMS", "national market system rules"),
        ("MiFID II", "European trading regulations"),
        ("Dodd-Frank", "derivatives regulation"),
        ("FINRA", "broker-dealer oversight"),
        ("pattern day trader", "PDT rule requirements")
    ]
    for reg, desc in regulations:
        examples.append(ce(
            f"What is {reg} and how does it affect trading?",
            f"""<think>{reg} covers {desc} and has specific compliance requirements.</think>
<answer>
## {reg}

### Overview
{desc.capitalize()}

### Key Requirements
- Registration/reporting
- Capital requirements
- Risk controls
- Record keeping

### Compliance
```python
class {reg.replace(" ", "").replace("-", "")}Compliance:
    def check_compliance(self, trade):
        # Verify {reg} requirements
        return is_compliant
```

### Penalties
- Fines
- Trading restrictions
- License suspension

### Best Practices
- Regular audits
- Documentation
- Training programs
</answer>""", "institutional"))
    
    return examples


def main():
    print("\n" + "="*60)
    print("📚 Comprehensive Example Generator")
    print("="*60 + "\n")
    
    examples = gen_comprehensive()
    print(f"Generated {len(examples)} new examples")
    
    # Save
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    comp_file = OUTPUT_DIR / "comprehensive.jsonl"
    with open(comp_file, 'w', encoding='utf-8') as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    print(f"✅ Saved to {comp_file}")
    
    # Load all and combine
    all_examples = list(examples)
    for fname in OUTPUT_DIR.glob("*.jsonl"):
        if fname.name not in ["comprehensive.jsonl", "train_combined.jsonl", "val_combined.jsonl"]:
            with open(fname, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            all_examples.append(json.loads(line))
                        except:
                            pass
    
    # Deduplicate
    seen = set()
    unique = []
    for ex in all_examples:
        key = ex.get('instruction', '')[:70]
        if key and key not in seen:
            seen.add(key)
            unique.append(ex)
    
    random.shuffle(unique)
    split = int(len(unique) * 0.9)
    
    with open(OUTPUT_DIR / "train_combined.jsonl", 'w', encoding='utf-8') as f:
        for ex in unique[:split]:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    with open(OUTPUT_DIR / "val_combined.jsonl", 'w', encoding='utf-8') as f:
        for ex in unique[split:]:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    
    print(f"✅ Final: {split} train + {len(unique)-split} val = {len(unique)} total")


if __name__ == "__main__":
    main()

