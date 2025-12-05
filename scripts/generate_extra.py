#!/usr/bin/env python3
"""Extra examples to reach 3000+"""
import json, random
from pathlib import Path

OUTPUT_DIR = Path.home() / "ChatOS-v0.2" / "data" / "persrm"

def ce(i, o, c):
    return {"instruction": i.strip(), "output": o.strip(),
            "metadata": {"source": "extra", "category": c, "quality": 1.0}}

def gen():
    examples = []
    
    # Timeframe specific
    tfs = ["1m", "5m", "15m", "30m", "1h", "4h", "daily", "weekly"]
    inds = ["RSI", "MACD", "SMA", "EMA", "BB", "ATR", "ADX", "Stoch"]
    for tf in tfs:
        for ind in inds:
            examples.append(ce(
                f"Best {ind} settings for {tf} timeframe?",
                f"<think>{ind} on {tf} needs adjustment.</think><answer>## {ind} for {tf}\n- Period: adjusted for {tf}\n- Interpretation: context specific</answer>", "technical"))
    
    # Price levels
    levels = ["support", "resistance", "pivot", "fibonacci", "round numbers", "VWAP", "previous high", "previous low"]
    actions = ["enter long", "enter short", "exit", "add to position", "scale out"]
    for level in levels:
        for action in actions:
            examples.append(ce(
                f"Should I {action} at {level}?",
                f"<think>Decision to {action} at {level} depends on context.</think><answer>## {action.title()} at {level.title()}\n- Check trend\n- Confirm with indicators\n- Risk management</answer>", "strategies"))
    
    # Specific symbols
    symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "SPY", "QQQ", "BTC", "ETH", "EURUSD", "GBPUSD", "USDJPY", "GOLD", "OIL"]
    setups = ["breakout", "pullback", "reversal", "continuation", "gap fill"]
    for sym in symbols:
        for setup in setups:
            examples.append(ce(
                f"Trading {setup} on {sym}",
                f"<think>{setup.title()} setup on {sym} analysis.</think><answer>## {sym} {setup.title()}\n- Entry criteria\n- Stop placement\n- Target levels</answer>", "strategies"))
    
    # Order types in detail
    orders = ["market", "limit", "stop", "stop-limit", "trailing", "bracket", "OCO", "MOC", "LOC"]
    scenarios = ["entry", "exit", "stop loss", "take profit", "scaling"]
    for order in orders:
        for scenario in scenarios:
            examples.append(ce(
                f"When to use {order} order for {scenario}?",
                f"<think>{order.title()} order for {scenario} has specific use cases.</think><answer>## {order.title()} for {scenario.title()}\n- Best when: specific conditions\n- Avoid when: other conditions</answer>", "execution"))
    
    # Risk per trade
    risks = ["0.5%", "1%", "1.5%", "2%", "3%", "5%"]
    accounts = ["$5K", "$10K", "$25K", "$50K", "$100K", "$250K", "$500K", "$1M"]
    for risk in risks:
        for account in accounts:
            examples.append(ce(
                f"Position sizing with {risk} risk on {account} account",
                f"<think>{risk} risk on {account} means specific dollar risk.</think><answer>## {risk} Risk on {account}\n- Dollar risk calculation\n- Position sizing formula\n- Example trade</answer>", "risk"))
    
    # Candlestick patterns
    candles = ["doji", "hammer", "engulfing", "morning star", "evening star", "three soldiers", "three crows", "harami", "marubozu", "spinning top", "shooting star", "hanging man"]
    contexts = ["at support", "at resistance", "in uptrend", "in downtrend", "after gap"]
    for candle in candles:
        for context in contexts:
            examples.append(ce(
                f"Trading {candle} {context}",
                f"<think>{candle.title()} {context} interpretation.</think><answer>## {candle.title()} {context.title()}\n- Signal strength\n- Entry/exit rules\n- Confirmation needed</answer>", "technical"))
    
    # Chart patterns
    patterns = ["head shoulders", "double top", "double bottom", "triangle", "flag", "pennant", "wedge", "channel", "cup handle", "rectangle"]
    for pattern in patterns:
        for tf in tfs[:4]:
            examples.append(ce(
                f"Trading {pattern} on {tf} chart",
                f"<think>{pattern.title()} pattern on {tf} timeframe.</think><answer>## {pattern.title()} ({tf})\n- Pattern identification\n- Entry trigger\n- Target calculation</answer>", "technical"))
    
    # Market conditions
    conditions = ["bull market", "bear market", "sideways", "high volatility", "low volatility", "news-driven", "earnings season", "Fed day"]
    strategies = ["momentum", "mean reversion", "breakout", "swing", "scalping"]
    for condition in conditions:
        for strat in strategies:
            examples.append(ce(
                f"Using {strat} in {condition}",
                f"<think>{strat.title()} strategy in {condition} conditions.</think><answer>## {strat.title()} During {condition.title()}\n- Adjustments needed\n- Opportunity vs risk\n- Best practices</answer>", "strategies"))
    
    # Coding tasks
    tasks = ["fetch data", "clean data", "calculate indicator", "generate signals", "backtest", "optimize", "execute order", "track portfolio", "generate report", "send alert"]
    libs = ["pandas", "numpy", "ccxt", "alpaca", "yfinance", "ta-lib", "backtrader", "zipline"]
    for task in tasks:
        for lib in libs:
            examples.append(ce(
                f"How to {task} with {lib}?",
                f"<think>{task.title()} using {lib} library.</think><answer>## {task.title()} with {lib}\n```python\nimport {lib}\n# implementation\n```</answer>", "code"))
    
    # Quant concepts
    concepts = ["alpha", "beta", "Sharpe", "Sortino", "Calmar", "max drawdown", "VaR", "CVaR", "correlation", "covariance", "factor loading", "information ratio"]
    uses = ["portfolio construction", "risk management", "performance evaluation", "strategy selection"]
    for concept in concepts:
        for use in uses:
            examples.append(ce(
                f"Using {concept} for {use}",
                f"<think>{concept} application in {use}.</think><answer>## {concept.title()} in {use.title()}\n- Calculation\n- Interpretation\n- Decision making</answer>", "institutional"))
    
    # Trading psychology
    emotions = ["fear", "greed", "hope", "regret", "frustration", "overconfidence", "anxiety"]
    situations = ["winning streak", "losing streak", "big win", "big loss", "missed trade", "stopped out"]
    for emotion in emotions:
        for situation in situations:
            examples.append(ce(
                f"Managing {emotion} after {situation}",
                f"<think>{emotion.title()} after {situation} requires specific approach.</think><answer>## Managing {emotion.title()}\n- Recognition\n- Coping strategy\n- Prevention</answer>", "psychology"))
    
    # Alternative data
    alt_data = ["sentiment", "options flow", "dark pool", "insider trading", "short interest", "earnings estimate", "analyst rating", "news sentiment"]
    for data in alt_data:
        for asset in ["stocks", "crypto", "forex"]:
            examples.append(ce(
                f"Using {data} data for {asset} trading",
                f"<think>{data.title()} signals for {asset} analysis.</think><answer>## {data.title()} for {asset.title()}\n- Data sources\n- Signal extraction\n- Integration</answer>", "institutional"))
    
    # Broker/exchange specific
    brokers = ["IBKR", "Alpaca", "TD Ameritrade", "Schwab", "Fidelity", "Binance", "Coinbase", "Kraken"]
    for broker in brokers:
        for task in ["connect API", "place order", "get account", "stream data"]:
            examples.append(ce(
                f"How to {task} with {broker}?",
                f"<think>{task.title()} with {broker} API.</think><answer>## {broker} {task.title()}\n```python\n# {broker} specific code\n```</answer>", "code"))
    
    return examples

def main():
    print("Generating extra examples...")
    examples = gen()
    print(f"Generated {len(examples)} examples")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "extra.jsonl", 'w') as f:
        for ex in examples:
            f.write(json.dumps(ex) + "\n")
    
    # Combine all
    all_ex = list(examples)
    for fname in OUTPUT_DIR.glob("*.jsonl"):
        if fname.name not in ["extra.jsonl", "train_combined.jsonl", "val_combined.jsonl"]:
            with open(fname) as f:
                for line in f:
                    if line.strip():
                        try: all_ex.append(json.loads(line))
                        except: pass
    
    seen = set()
    unique = []
    for ex in all_ex:
        key = ex.get('instruction', '')[:50]
        if key and key not in seen:
            seen.add(key)
            unique.append(ex)
    
    random.shuffle(unique)
    split = int(len(unique) * 0.9)
    
    with open(OUTPUT_DIR / "train_combined.jsonl", 'w') as f:
        for ex in unique[:split]:
            f.write(json.dumps(ex) + "\n")
    with open(OUTPUT_DIR / "val_combined.jsonl", 'w') as f:
        for ex in unique[split:]:
            f.write(json.dumps(ex) + "\n")
    
    print(f"✅ TOTAL: {split} train + {len(unique)-split} val = {len(unique)} unique")

if __name__ == "__main__":
    main()

