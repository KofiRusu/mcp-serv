#!/usr/bin/env python3
"""
PersRM Expert Training Data Generator

Aggregates and transforms existing data sources into high-quality training examples
optimized for trading intelligence.

Data Sources:
- Scraped news (HN, Reddit, CoinGecko)
- HF trading states and decisions
- Backtest results and strategy metrics
- Trading psychology content
- Coding challenges (trading-related)

Usage:
    python generate_expert_training.py --output-dir ./data/persrm
"""

import json
import os
import random
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import argparse

# Base paths
HOME = Path(os.environ.get("HOME", "/home/kr"))
PERSRM_DATA = HOME / "persrm-data"
TRADING_MEMORY = HOME / "TradingMemory"
CHATOS_V02 = HOME / "ChatOS-v0.2"

# Data source paths
SCRAPED_DIR = PERSRM_DATA / "scraped"
SYNTHETIC_TRADING_DIR = PERSRM_DATA / "synthetic" / "trading"
PSYCHOLOGY_DIR = PERSRM_DATA / "economics" / "processed"
HF_TRADING_DIR = TRADING_MEMORY / "data" / "hf_trading"
BACKTEST_DIR = PERSRM_DATA / "backtest_results"
TRADES_DIR = TRADING_MEMORY / "trades"
CODING_DIR = PERSRM_DATA / "synthetic" / "coding"


class ExpertTrainingGenerator:
    """Generate high-quality training examples from multiple data sources."""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.examples: List[Dict] = []
        self.stats = {
            "trading_decisions": 0,
            "psychology_coaching": 0,
            "risk_management": 0,
            "sentiment_analysis": 0,
            "news_analysis": 0,
            "strategy_analysis": 0,
            "coding": 0,
            "market_status": 0,
        }
        
    def load_jsonl(self, path: Path) -> List[Dict]:
        """Load a JSONL file."""
        examples = []
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            examples.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        return examples
    
    def load_json(self, path: Path) -> Optional[Dict]:
        """Load a JSON file."""
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError:
                    return None
        return None
    
    def create_example(self, instruction: str, output: str, 
                      source: str, quality: float = 1.0,
                      category: str = "general") -> Dict:
        """Create a training example with proper metadata."""
        return {
            "instruction": instruction.strip(),
            "output": output.strip(),
            "metadata": {
                "source": source,
                "quality": quality,
                "category": category,
                "generated_at": datetime.now().isoformat()
            }
        }
    
    # =========================================================================
    # TRADING DECISIONS (from HF trading states)
    # =========================================================================
    
    def generate_trading_decisions(self, max_examples: int = 400) -> None:
        """Transform HF trading states into expert decision examples."""
        print(f"📊 Processing HF trading states from {HF_TRADING_DIR}...")
        
        if not HF_TRADING_DIR.exists():
            print("  ⚠️ HF trading directory not found")
            return
        
        state_files = sorted(HF_TRADING_DIR.glob("hf_state_*.json"))
        print(f"  Found {len(state_files)} state files")
        
        scenarios = [
            self._generate_entry_decision,
            self._generate_exit_decision,
            self._generate_position_sizing,
            self._generate_hold_vs_add,
            self._generate_stop_loss_adjustment,
        ]
        
        count = 0
        for state_file in state_files:
            if count >= max_examples:
                break
                
            state = self.load_json(state_file)
            if not state:
                continue
            
            # Pick a random scenario for this state
            scenario_fn = random.choice(scenarios)
            example = scenario_fn(state)
            
            if example:
                self.examples.append(example)
                self.stats["trading_decisions"] += 1
                count += 1
        
        print(f"  ✓ Generated {count} trading decision examples")
    
    def _generate_entry_decision(self, state: Dict) -> Optional[Dict]:
        """Generate entry decision from trading state."""
        # Extract relevant data - handle multiple formats
        stats = state.get("stats", {})
        trades = state.get("trades", [])
        
        # Get balance from stats
        balance = stats.get("balance", state.get("account", {}).get("balance", 10000))
        
        # Get symbols from stats or use defaults
        symbols = stats.get("symbols", ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
        if not symbols:
            symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        
        symbol = random.choice(symbols)
        
        # Try to get signal data from recent trades
        recent_trade = None
        for trade in trades:
            if trade.get("symbol") == symbol:
                recent_trade = trade
                break
        
        if recent_trade and "signal" in recent_trade:
            sig = recent_trade["signal"].get("indicators", {})
        else:
            # Generate synthetic indicators
            sig = {
                "price": random.uniform(90000, 100000) if "BTC" in symbol else random.uniform(3000, 3500) if "ETH" in symbol else random.uniform(130, 160),
                "rsi": random.uniform(20, 80),
                "macd": random.uniform(-0.5, 0.5),
                "macd_signal": random.uniform(-0.5, 0.5),
            }
        
        price = sig.get("price", 0)
        rsi = sig.get("rsi", 50)
        macd = sig.get("macd", 0)
        macd_signal = sig.get("macd_signal", macd * 0.9)
        volume_ratio = sig.get("volume_ratio", 1.0)
        
        if price == 0:
            return None
        
        # Generate instruction
        instruction = f"""Analyze this trading opportunity:

Symbol: {symbol}
Current Price: ${price:,.2f}
RSI(14): {rsi:.1f}
MACD: {macd:.4f} (Signal: {macd_signal:.4f})
Volume: {volume_ratio:.2f}x average
Account Balance: ${balance:,.2f}

Should I enter a position? If yes, provide entry, stop-loss, and take-profit levels."""

        # Generate expert response
        macd_bullish = macd > macd_signal
        rsi_oversold = rsi < 30
        rsi_overbought = rsi > 70
        high_volume = volume_ratio > 1.5
        
        # Determine recommendation
        if rsi_oversold and macd_bullish:
            action = "BUY/LONG"
            reasoning = "RSI oversold with MACD bullish divergence - high probability bounce setup"
            stop_pct = 0.02
            tp_pct = 0.04
        elif rsi_overbought:
            action = "WAIT"
            reasoning = "RSI overbought - wait for pullback before entering"
            stop_pct = 0
            tp_pct = 0
        elif macd_bullish and rsi > 40 and rsi < 60:
            action = "BUY/LONG"
            reasoning = "MACD bullish crossover with neutral RSI - trend continuation likely"
            stop_pct = 0.015
            tp_pct = 0.03
        else:
            action = "WAIT"
            reasoning = "No clear edge - mixed signals suggest waiting for better setup"
            stop_pct = 0
            tp_pct = 0
        
        if action == "BUY/LONG":
            stop_loss = price * (1 - stop_pct)
            take_profit = price * (1 + tp_pct)
            position_size = min(balance * 0.02 / (price * stop_pct), balance * 0.1 / price)
            
            output = f"""<think>
Analyzing {symbol} for potential entry...

Technical Analysis:
- RSI at {rsi:.1f}: {"Oversold - bullish" if rsi < 30 else "Overbought - bearish" if rsi > 70 else "Neutral"}
- MACD vs Signal: {"Bullish" if macd_bullish else "Bearish"} ({macd:.4f} vs {macd_signal:.4f})
- Volume: {volume_ratio:.2f}x average - {"High interest" if high_volume else "Normal"}

Risk Assessment:
- 2% account risk = ${balance * 0.02:,.2f} max loss
- Position size based on stop distance

Key signal: {reasoning}
</think>

<answer>
**Recommendation: {action}**

Entry: ${price:,.2f}
Stop-Loss: ${stop_loss:,.2f} ({stop_pct*100:.1f}% below entry)
Take-Profit: ${take_profit:,.2f} ({tp_pct*100:.1f}% above entry)

Position Size: {position_size:.4f} {symbol.split('/')[0]}
Risk: ${balance * 0.02:,.2f} (2% of account)
Risk/Reward: 1:{tp_pct/stop_pct:.1f}

**Reasoning:** {reasoning}

**Risk Management:**
- Set stop-loss immediately after entry
- Consider scaling out 50% at 1:1 R:R
- Move stop to breakeven after 1R profit
</answer>"""
        else:
            output = f"""<think>
Analyzing {symbol} for potential entry...

Technical Analysis:
- RSI at {rsi:.1f}: {"Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral range"}
- MACD vs Signal: {"Bullish" if macd_bullish else "Bearish"}
- Volume: {volume_ratio:.2f}x average

Assessment: {reasoning}
</think>

<answer>
**Recommendation: {action}**

**Reasoning:** {reasoning}

**What to watch for:**
- RSI moving to oversold (<30) for long entry
- MACD bullish crossover confirmation
- Volume spike indicating institutional interest

**Action:** Add {symbol} to watchlist and wait for clearer setup.
</answer>"""

        return self.create_example(
            instruction, output, 
            source="hf_trading_expert",
            quality=1.0,
            category="trading_decision"
        )
    
    def _generate_exit_decision(self, state: Dict) -> Optional[Dict]:
        """Generate exit decision from trading state."""
        trades = state.get("trades", [])
        stats = state.get("stats", {})
        
        # Need closed trades to analyze
        if not trades or not isinstance(trades, list) or len(trades) == 0:
            return None
        
        # Pick a random trade
        trade = random.choice(trades)
        if not isinstance(trade, dict):
            return None
        
        symbol = trade.get("symbol", "BTC/USDT")
        entry_price = trade.get("entry_price", 50000)
        exit_price = trade.get("exit_price", entry_price)
        current_price = exit_price  # For closed trades, current = exit
        quantity = trade.get("quantity", 0.1)
        side = trade.get("side", "long")
        pnl_pct = trade.get("pnl_pct", 0)
        
        # Get signal indicators if available
        signal_data = trade.get("signal", {})
        indicators = signal_data.get("indicators", {})
        rsi = indicators.get("rsi", random.uniform(30, 70))
        macd = indicators.get("macd", random.uniform(-0.5, 0.5))
        macd_signal = indicators.get("macd_signal", macd * 0.9)
        
        instruction = f"""Evaluate this open position:

Symbol: {symbol}
Side: {side.upper()}
Entry Price: ${entry_price:,.2f}
Current Price: ${current_price:,.2f}
Quantity: {quantity:.4f}
Unrealized P&L: {pnl_pct:+.2f}%

Current RSI: {rsi:.1f}
MACD: {macd:.4f} (Signal: {macd_signal:.4f})

Should I hold, take profit, or cut losses?"""

        macd_bullish = macd > macd_signal
        
        # Determine exit recommendation
        if pnl_pct > 5 and rsi > 70:
            action = "TAKE PROFIT"
            reasoning = "Good profit with overbought RSI - momentum likely to fade"
        elif pnl_pct > 3 and not macd_bullish:
            action = "TAKE PARTIAL PROFIT"
            reasoning = "Decent profit but MACD turning bearish - reduce exposure"
        elif pnl_pct < -3:
            action = "CUT LOSS"
            reasoning = "Loss exceeding comfort zone - preserve capital"
        elif pnl_pct > 1 and macd_bullish:
            action = "HOLD"
            reasoning = "Profit running with bullish momentum - let it ride"
        else:
            action = "HOLD"
            reasoning = "Position within normal range - no action needed"
        
        output = f"""<think>
Position Analysis for {symbol} {side.upper()}:

P&L Status: {pnl_pct:+.2f}% {"(profitable)" if pnl_pct > 0 else "(at loss)"}
Technical Signals:
- RSI {rsi:.1f}: {"Overbought - consider exit" if rsi > 70 else "Oversold - potential bounce" if rsi < 30 else "Neutral"}
- MACD: {"Bullish momentum" if macd_bullish else "Bearish momentum"}

Decision factors:
1. Current profit/loss level
2. Momentum indicators
3. Risk management rules
</think>

<answer>
**Recommendation: {action}**

**Reasoning:** {reasoning}

{"**Suggested Exit:** $" + f"{current_price:,.2f}" if "PROFIT" in action or action == "CUT LOSS" else ""}
{"**Realized P&L:** " + f"{pnl_pct:+.2f}% (${quantity * entry_price * pnl_pct / 100:,.2f})" if "PROFIT" in action or action == "CUT LOSS" else ""}

**Next Steps:**
{f"- Close {'50%' if 'PARTIAL' in action else '100%'} of position at market" if action != "HOLD" else "- Continue monitoring position"}
{f"- {'Set trailing stop at breakeven' if 'PARTIAL' in action else 'Move to next opportunity'}" if action != "HOLD" else "- Adjust stop-loss if needed"}
</answer>"""

        return self.create_example(
            instruction, output,
            source="hf_trading_expert",
            quality=1.0,
            category="trading_decision"
        )
    
    def _generate_position_sizing(self, state: Dict) -> Optional[Dict]:
        """Generate position sizing advice."""
        account = state.get("account", {})
        balance = account.get("balance", 10000)
        
        symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        symbol = random.choice(symbols)
        
        prices = {"BTC/USDT": 93000, "ETH/USDT": 3200, "SOL/USDT": 145}
        price = prices.get(symbol, 50000)
        
        risk_pct = random.choice([1, 2, 3])
        stop_pct = random.choice([1.5, 2, 2.5, 3])
        
        instruction = f"""Calculate proper position size:

Account Balance: ${balance:,.2f}
Risk per trade: {risk_pct}%
Symbol: {symbol}
Entry Price: ${price:,.2f}
Stop-Loss: {stop_pct}% below entry

What position size should I use?"""

        # Calculate
        risk_amount = balance * (risk_pct / 100)
        stop_distance = price * (stop_pct / 100)
        position_size = risk_amount / stop_distance
        position_value = position_size * price
        leverage_if_needed = position_value / balance if position_value > balance else 1
        
        output = f"""<think>
Position Sizing Calculation:

Step 1: Calculate risk amount
Account: ${balance:,.2f}
Risk: {risk_pct}% = ${risk_amount:,.2f}

Step 2: Calculate stop distance in dollars
Entry: ${price:,.2f}
Stop: {stop_pct}% below = ${price * (1 - stop_pct/100):,.2f}
Stop distance: ${stop_distance:,.2f}

Step 3: Calculate position size
Position = Risk / Stop Distance
Position = ${risk_amount:,.2f} / ${stop_distance:,.2f}
Position = {position_size:.6f} {symbol.split('/')[0]}
</think>

<answer>
**Position Size: {position_size:.6f} {symbol.split('/')[0]}**

**Breakdown:**
- Position Value: ${position_value:,.2f}
- Risk Amount: ${risk_amount:,.2f} ({risk_pct}% of account)
- Stop-Loss Price: ${price * (1 - stop_pct/100):,.2f}

**Risk Validation:**
- If stopped out: Lose ${risk_amount:,.2f} ✓
- Maximum drawdown from this trade: {risk_pct}%
- {"No leverage needed" if leverage_if_needed <= 1 else f"Requires {leverage_if_needed:.1f}x leverage - consider reducing size"}

**The Kelly Criterion suggests:**
- Never risk more than 2-5% per trade
- Your {risk_pct}% risk is {"conservative ✓" if risk_pct <= 2 else "acceptable" if risk_pct <= 3 else "aggressive ⚠️"}
</answer>"""

        return self.create_example(
            instruction, output,
            source="risk_management_expert",
            quality=1.0,
            category="risk_management"
        )
        
    def _generate_hold_vs_add(self, state: Dict) -> Optional[Dict]:
        """Generate hold vs add position decision."""
        # Reuse entry decision logic
        return self._generate_entry_decision(state)
    
    def _generate_stop_loss_adjustment(self, state: Dict) -> Optional[Dict]:
        """Generate stop-loss adjustment advice."""
        # Only generate if we have trades
        trades = state.get("trades", [])
        if not trades or not isinstance(trades, list) or len(trades) == 0:
            return self._generate_position_sizing(state)
        return self._generate_exit_decision(state)
    
    # =========================================================================
    # TRADING PSYCHOLOGY (from curated content)
    # =========================================================================
    
    def generate_psychology_coaching(self, max_examples: int = 200) -> None:
        """Generate trading psychology coaching scenarios."""
        print(f"🧠 Processing trading psychology from {PSYCHOLOGY_DIR}...")
        
        psychology_file = PSYCHOLOGY_DIR / "trading_psychology.jsonl"
        if not psychology_file.exists():
            print("  ⚠️ Trading psychology file not found")
            return
        
        articles = self.load_jsonl(psychology_file)
        print(f"  Found {len(articles)} psychology articles")
        
        # Coaching scenario templates
        scenarios = [
            ("I just lost 3 trades in a row and want to double my position size to recover quickly. Is this a good idea?", "revenge_trading"),
            ("I keep seeing my friends post about huge gains on crypto. I feel like I'm missing out. Should I go all-in?", "fomo"),
            ("I have a winning position up 20% but I'm scared it will reverse. Should I close it now?", "loss_aversion"),
            ("I bought a coin at $100, it's now $50. I know it will come back, so I'm holding. Right?", "anchoring"),
            ("I've been watching BTC all day and I feel like I need to make a trade. Any trade.", "overtrading"),
            ("My trading system says SELL but the news is bullish. Should I ignore my system?", "confirmation_bias"),
            ("I lost money last month. Maybe trading isn't for me. Should I quit?", "drawdown_psychology"),
            ("I made 5 winning trades in a row. I feel unstoppable! Should I increase my size?", "overconfidence"),
            ("The market keeps hitting my stop loss then reversing. They're hunting my stops!", "conspiracy_thinking"),
            ("I can't sleep because I have an open position. Is this normal?", "emotional_attachment"),
        ]
        
        count = 0
        for question, topic in scenarios:
            if count >= max_examples:
                break
            
            # Find relevant article
            relevant_article = None
            for article in articles:
                if topic.replace("_", " ") in article.get("content", "").lower():
                    relevant_article = article
                    break
            
            if not relevant_article:
                relevant_article = random.choice(articles) if articles else None
            
            example = self._generate_psychology_response(question, topic, relevant_article)
            if example:
                self.examples.append(example)
                self.stats["psychology_coaching"] += 1
                count += 1
        
        # Generate more from article content
        for article in articles:
            if count >= max_examples:
                break
            
            example = self._generate_psychology_from_article(article)
            if example:
                self.examples.append(example)
                self.stats["psychology_coaching"] += 1
                count += 1
        
        print(f"  ✓ Generated {count} psychology coaching examples")
    
    def _generate_psychology_response(self, question: str, topic: str, 
                                      article: Optional[Dict]) -> Optional[Dict]:
        """Generate psychology coaching response."""
        
        topic_responses = {
            "revenge_trading": {
                "action": "STOP. Do NOT increase position size.",
                "explanation": "You're experiencing revenge trading - the psychological urge to quickly recover losses by taking bigger risks. This almost always leads to bigger losses.",
                "steps": [
                    "Step away from trading for 24-48 hours",
                    "Review your 3 losses objectively - were they good trades with bad outcomes, or bad trades?",
                    "Return to your normal position sizing - NEVER increase size after losses",
                    "Focus on process, not P&L recovery"
                ]
            },
            "fomo": {
                "action": "NO. Do NOT go all-in based on others' gains.",
                "explanation": "FOMO (Fear of Missing Out) is one of the most dangerous emotions in trading. Social media shows winners, not the majority who lose.",
                "steps": [
                    "Remember: for every winner posted, there are 10 losers not posting",
                    "Stick to your trading plan and position sizing rules",
                    "Markets offer endless opportunities - missing one doesn't matter",
                    "Ask yourself: would you make this trade if you hadn't seen those posts?"
                ]
            },
            "loss_aversion": {
                "action": "Consider taking partial profits.",
                "explanation": "You're experiencing loss aversion - the fear of giving back gains is causing you to consider closing too early. However, letting winners run is key to profitable trading.",
                "steps": [
                    "Set a trailing stop to protect profits while allowing upside",
                    "Take 50% off and let the rest run with a breakeven stop",
                    "Have a target before entering trades - stick to it",
                    "Journal this feeling - it's normal but must be managed"
                ]
            },
            "anchoring": {
                "action": "Your entry price is IRRELEVANT to the current trade decision.",
                "explanation": "You're anchoring to your purchase price. The market doesn't care what you paid. The only question is: would you buy at THIS price?",
                "steps": [
                    "Ask: if I had cash instead of this position, would I buy it now?",
                    "If no: sell and reallocate to better opportunities",
                    "If yes: hold, but set a proper stop loss from current price",
                    "Accept the loss and move forward - sunk cost fallacy is destroying your capital"
                ]
            },
            "overtrading": {
                "action": "Close the charts. Do NOT trade.",
                "explanation": "The urge to trade when there's no setup is called 'action bias' - the need to do something. But in trading, doing nothing is often the best action.",
                "steps": [
                    "Set maximum daily trades (e.g., 3)",
                    "Only trade when your system gives a clear signal",
                    "Find activities outside trading to occupy downtime",
                    "Remember: the best traders are patient - they wait for A+ setups"
                ]
            },
        }
        
        response_data = topic_responses.get(topic, {
            "action": "Take a step back and assess objectively.",
            "explanation": "This is a common trading psychology challenge.",
            "steps": ["Review your trading journal", "Consult your trading plan", "Consider talking to a mentor"]
        })
        
        output = f"""<think>
Identifying the psychological pattern: {topic.replace('_', ' ').title()}

This is a classic trading psychology trap that affects even experienced traders.
The emotional state described indicates:
- Elevated stress response
- Potential for impulsive decisions
- Need for systematic intervention

Referencing trading psychology principles to formulate response.
</think>

<answer>
**{response_data['action']}**

**What you're experiencing:** {response_data['explanation']}

**Action Plan:**
{chr(10).join(f'{i+1}. {step}' for i, step in enumerate(response_data['steps']))}

**Remember:**
- Your emotional state is a signal, not a trading strategy
- Professional traders have rules specifically to override emotions
- Taking a break is never the wrong decision when feeling emotional
- One trade doesn't define your trading career

**Key insight:** The fact that you're asking this question shows self-awareness. That's the first step to better trading psychology.
</answer>"""

        return self.create_example(
            question, output,
            source="psychology_expert",
            quality=1.0,
            category="psychology_coaching"
        )
    
    def _generate_psychology_from_article(self, article: Dict) -> Optional[Dict]:
        """Generate Q&A from psychology article."""
        title = article.get("title", "")
        content = article.get("content", "")
        
        if not title or not content:
            return None
        
        instruction = f"Explain the concept of '{title}' and how it affects traders."
        
        # Extract key points from content
        sentences = content.split(". ")
        key_points = sentences[:5] if len(sentences) > 5 else sentences
        
        output = f"""<think>
Analyzing trading psychology concept: {title}

This is a fundamental concept that affects trading performance.
Key aspects to cover:
- Definition and explanation
- How it manifests in trading
- Practical mitigation strategies
</think>

<answer>
## {title}

{content[:500]}...

**Key Takeaways:**
- Awareness is the first step to overcoming this bias
- Use systematic trading rules to override emotional impulses
- Keep a trading journal to identify patterns
- Consider the opposite viewpoint before making decisions

**Practical Application:**
Before every trade, ask yourself: "Am I making this decision based on my system, or based on emotion?"
</answer>"""

        return self.create_example(
            instruction, output,
            source="psychology_article",
            quality=0.9,
            category="psychology_coaching"
        )
    
    # =========================================================================
    # STRATEGY ANALYSIS (from backtest results)
    # =========================================================================
    
    def generate_strategy_analysis(self, max_examples: int = 100) -> None:
        """Convert backtest results into strategy analysis examples."""
        print(f"📈 Processing backtest results from {BACKTEST_DIR}...")
        
        if not BACKTEST_DIR.exists():
            print("  ⚠️ Backtest directory not found")
            return
        
        summary_files = list(BACKTEST_DIR.glob("*_summary.json"))
        print(f"  Found {len(summary_files)} backtest summaries")
        
        count = 0
        for summary_file in summary_files:
            if count >= max_examples:
                break
            
            summary = self.load_json(summary_file)
            if not summary:
                continue
            
            example = self._generate_backtest_analysis(summary)
            if example:
                self.examples.append(example)
                self.stats["strategy_analysis"] += 1
                count += 1
        
        print(f"  ✓ Generated {count} strategy analysis examples")
    
    def _generate_backtest_analysis(self, summary: Dict) -> Optional[Dict]:
        """Generate analysis from backtest summary."""
        strategy = summary.get("strategy_name", "Unknown Strategy")
        symbol = summary.get("symbol", "BTC/USDT")
        timeframe = summary.get("timeframe", "1h")
        
        initial = summary.get("initial_capital", 10000)
        final = summary.get("final_capital", 10000)
        total_trades = summary.get("total_trades", 0)
        win_rate = summary.get("win_rate", 0) * 100
        total_return = summary.get("total_return", 0) * 100
        max_dd = summary.get("max_drawdown", 0) * 100
        sharpe = summary.get("sharpe_ratio", 0)
        profit_factor = summary.get("profit_factor", 0)
        avg_win = summary.get("avg_win", 0)
        avg_loss = summary.get("avg_loss", 0)
        
        metrics = summary.get("metrics", {})
        expectancy = metrics.get("expectancy", 0)
        
        instruction = f"""Analyze this backtest result:

Strategy: {strategy}
Symbol: {symbol} ({timeframe})
Period: 30 days

Performance Metrics:
- Total Return: {total_return:.1f}%
- Win Rate: {win_rate:.1f}%
- Total Trades: {total_trades}
- Max Drawdown: {max_dd:.2f}%
- Sharpe Ratio: {sharpe:.2f}
- Profit Factor: {profit_factor:.2f}
- Avg Win: {avg_win:.2f}%
- Avg Loss: {avg_loss:.2f}%

Is this strategy worth trading live?"""

        # Analyze
        good_sharpe = sharpe > 1
        good_win_rate = win_rate > 45
        good_profit_factor = profit_factor > 1.5
        enough_trades = total_trades > 30
        manageable_dd = max_dd < 20
        
        score = sum([good_sharpe, good_win_rate, good_profit_factor, enough_trades, manageable_dd])
        
        if score >= 4:
            verdict = "PROMISING - Consider live testing with small size"
            color = "green"
        elif score >= 2:
            verdict = "NEEDS IMPROVEMENT - Address weaknesses before live trading"
            color = "yellow"
        else:
            verdict = "NOT READY - Significant issues need resolution"
            color = "red"
        
        output = f"""<think>
Evaluating {strategy} on {symbol}:

Strengths:
{f"- Sharpe Ratio {sharpe:.2f} > 1 indicates good risk-adjusted returns" if good_sharpe else ""}
{f"- Win rate {win_rate:.1f}% is acceptable" if good_win_rate else ""}
{f"- Profit factor {profit_factor:.2f} means winners outpace losers" if good_profit_factor else ""}
{f"- {total_trades} trades provides statistical significance" if enough_trades else ""}
{f"- Max drawdown {max_dd:.2f}% is manageable" if manageable_dd else ""}

Weaknesses:
{f"- Sharpe Ratio {sharpe:.2f} is poor (want > 1)" if not good_sharpe else ""}
{f"- Win rate {win_rate:.1f}% is below ideal (want > 45%)" if not good_win_rate else ""}
{f"- Profit factor {profit_factor:.2f} means losers outpace winners" if not good_profit_factor else ""}
{f"- Only {total_trades} trades - need 30+ for confidence" if not enough_trades else ""}
{f"- Max drawdown {max_dd:.2f}% is concerning (want < 20%)" if not manageable_dd else ""}

Overall score: {score}/5
</think>

<answer>
## Strategy Assessment: {verdict}

### Performance Summary
| Metric | Value | Status |
|--------|-------|--------|
| Total Return | {total_return:.1f}% | {"✓" if total_return > 0 else "✗"} |
| Sharpe Ratio | {sharpe:.2f} | {"✓" if good_sharpe else "⚠️"} |
| Win Rate | {win_rate:.1f}% | {"✓" if good_win_rate else "⚠️"} |
| Profit Factor | {profit_factor:.2f} | {"✓" if good_profit_factor else "⚠️"} |
| Max Drawdown | {max_dd:.2f}% | {"✓" if manageable_dd else "⚠️"} |
| Trade Count | {total_trades} | {"✓" if enough_trades else "⚠️ Need more data"} |

### Recommendations
{"1. **Ready for paper trading** - Run for 3+ months before live capital" if score >= 4 else "1. **Extend backtest period** - 30 days is not enough for confidence"}
{"2. Reduce position size initially (0.5% risk per trade)" if score >= 4 else f"2. **Improve {'Sharpe ratio' if not good_sharpe else 'win rate' if not good_win_rate else 'profit factor'}** - Current level is concerning"}
{"3. Set a maximum drawdown threshold of 15% for live trading" if score >= 4 else "3. Consider adding filters to reduce false signals"}

### Expected Live Performance
- Likely worse than backtest (expect 30-50% degradation)
- Estimated monthly return: {total_return * 0.6 / 30 * 21:.1f}% (conservative)
- Risk of ruin: {"Low" if manageable_dd and good_sharpe else "Medium" if manageable_dd else "High"}
</answer>"""

        return self.create_example(
            instruction, output,
            source="backtest_analysis",
            quality=1.0,
            category="strategy_analysis"
        )
    
    # =========================================================================
    # NEWS & SENTIMENT ANALYSIS (from scraped data)
    # =========================================================================
    
    def generate_news_analysis(self, max_examples: int = 300) -> None:
        """Create news impact analysis from scraped data."""
        print(f"📰 Processing scraped news from {SCRAPED_DIR}...")
        
        if not SCRAPED_DIR.exists():
            print("  ⚠️ Scraped directory not found")
            return
        
        scraped_files = sorted(SCRAPED_DIR.glob("scraped_*.jsonl"))[-10:]  # Last 10 files
        print(f"  Processing {len(scraped_files)} recent scraped files")
        
        all_items = []
        for f in scraped_files:
            all_items.extend(self.load_jsonl(f))
        
        print(f"  Found {len(all_items)} scraped items")
        
        # Filter for crypto/trading relevant items
        crypto_keywords = ["bitcoin", "btc", "ethereum", "eth", "crypto", "blockchain", 
                          "trading", "market", "price", "defi", "nft", "web3"]
        
        count = 0
        for item in all_items:
            if count >= max_examples:
                break
            
            source = item.get("metadata", {}).get("source", "")
            
            if source == "coingecko":
                example = self._generate_market_status(item)
                if example:
                    self.examples.append(example)
                    self.stats["market_status"] += 1
                    count += 1
            elif source in ["hackernews", "reddit/LocalLLaMA", "reddit/programming"]:
                # Check if crypto/trading related
                text = (item.get("input", "") + item.get("output", "")).lower()
                if any(kw in text for kw in crypto_keywords):
                    example = self._generate_news_impact(item)
                    if example:
                        self.examples.append(example)
                        self.stats["news_analysis"] += 1
                        count += 1
        
        print(f"  ✓ Generated {count} news/sentiment examples")
    
    def _generate_market_status(self, item: Dict) -> Optional[Dict]:
        """Generate market status analysis."""
        metadata = item.get("metadata", {})
        symbol = metadata.get("symbol", "BTC")
        
        # Parse existing output for price data
        output_text = item.get("output", "")
        
        # Extract price from output
        price_match = re.search(r"Price: \$([0-9,.]+)", output_text)
        change_match = re.search(r"24h Change: ([+-]?[0-9.]+)%", output_text)
        
        if not price_match:
            return None
        
        price = float(price_match.group(1).replace(",", ""))
        change = float(change_match.group(1)) if change_match else 0
        
        instruction = f"What is the current market status of {symbol} and what does it indicate for traders?"
        
        # Determine market condition
        if change > 5:
            condition = "STRONG BULLISH"
            advice = "Consider taking profits on longs, avoid shorting"
        elif change > 2:
            condition = "BULLISH"
            advice = "Look for pullback entries, maintain long bias"
        elif change < -5:
            condition = "STRONG BEARISH"
            advice = "Avoid catching falling knives, wait for stabilization"
        elif change < -2:
            condition = "BEARISH"
            advice = "Reduce long exposure, look for short opportunities"
        else:
            condition = "NEUTRAL"
            advice = "Range-bound conditions, wait for breakout"
        
        new_output = f"""<think>
Analyzing {symbol} market status:

Current Data:
- Price: ${price:,.2f}
- 24h Change: {change:+.2f}%

Market Condition Assessment:
- {"Strong momentum" if abs(change) > 5 else "Moderate movement" if abs(change) > 2 else "Consolidation phase"}
- {"Potential overextension" if abs(change) > 7 else "Trend intact"}
</think>

<answer>
## {symbol} Market Status: {condition}

**Current Price:** ${price:,.2f}
**24h Change:** {change:+.2f}%

**Market Interpretation:**
{advice}

**Key Levels to Watch:**
- Resistance: ${price * 1.05:,.2f}
- Support: ${price * 0.95:,.2f}

**Trading Implications:**
- {"Wait for pullback before new longs" if change > 3 else "Look for bounce entries" if change < -3 else "Trade the range with tight stops"}
- {"Set stops wider due to volatility" if abs(change) > 5 else "Normal stop placement"}
</answer>"""

        return self.create_example(
            instruction, new_output,
            source="market_status",
            quality=0.9,
            category="sentiment_analysis"
        )
    
    def _generate_news_impact(self, item: Dict) -> Optional[Dict]:
        """Generate news impact analysis."""
        input_text = item.get("input", "")
        metadata = item.get("metadata", {})
        source = metadata.get("source", "news")
        
        # Extract title if present
        title_match = re.search(r"Title: (.+?)(?:\n|$)", input_text)
        title = title_match.group(1) if title_match else input_text[:100]
        
        instruction = f"""Analyze this news headline for market impact:

Source: {source}
Headline: {title}

What is the potential impact on crypto/trading markets?"""

        # Determine impact
        bullish_words = ["launch", "adoption", "partnership", "approved", "bullish", "growth", "new"]
        bearish_words = ["hack", "ban", "crash", "fraud", "investigation", "lawsuit", "bearish"]
        
        text_lower = title.lower()
        bullish_score = sum(1 for w in bullish_words if w in text_lower)
        bearish_score = sum(1 for w in bearish_words if w in text_lower)
        
        if bullish_score > bearish_score:
            sentiment = "BULLISH"
            impact = "Positive for market sentiment"
        elif bearish_score > bullish_score:
            sentiment = "BEARISH"
            impact = "Negative for market sentiment"
        else:
            sentiment = "NEUTRAL"
            impact = "Limited direct market impact"
        
        output = f"""<think>
Analyzing news for market impact:

Headline: {title[:100]}
Source: {source}

Sentiment Analysis:
- Bullish indicators: {bullish_score}
- Bearish indicators: {bearish_score}
- Overall: {sentiment}

Relevance to trading: {"High" if "crypto" in text_lower or "bitcoin" in text_lower else "Medium" if bullish_score + bearish_score > 0 else "Low"}
</think>

<answer>
## News Impact Analysis

**Headline:** {title[:150]}
**Source:** {source}

**Sentiment:** {sentiment}
**Impact Level:** {"High" if abs(bullish_score - bearish_score) > 2 else "Medium" if abs(bullish_score - bearish_score) > 0 else "Low"}

**Market Implications:**
{impact}

**Trading Action:**
- {"Consider bullish positions if confirmed by technicals" if sentiment == "BULLISH" else "Be cautious with longs, consider reducing exposure" if sentiment == "BEARISH" else "No immediate action required"}
- {"Watch for breakout opportunities" if sentiment == "BULLISH" else "Set tighter stops" if sentiment == "BEARISH" else "Continue normal trading plan"}

**Time Horizon:**
- Short-term impact: {"1-3 days" if sentiment != "NEUTRAL" else "Minimal"}
- Long-term impact: {"Depends on follow-through" if sentiment != "NEUTRAL" else "None expected"}
</answer>"""

        return self.create_example(
            instruction, output,
            source="news_analysis",
            quality=0.9,
            category="sentiment_analysis"
        )
    
    # =========================================================================
    # CODING (trading-related)
    # =========================================================================
    
    def generate_trading_code(self, max_examples: int = 300) -> None:
        """Generate trading-related coding examples."""
        print(f"💻 Processing coding challenges from {CODING_DIR}...")
        
        coding_file = CODING_DIR / "coding_training_data.jsonl"
        if not coding_file.exists():
            print("  ⚠️ Coding file not found")
            return
        
        challenges = self.load_jsonl(coding_file)
        print(f"  Found {len(challenges)} coding challenges")
        
        # Trading-related coding topics
        trading_topics = [
            ("Implement a simple moving average crossover strategy", "strategy"),
            ("Calculate RSI (Relative Strength Index) from price data", "indicator"),
            ("Build a position sizing calculator with Kelly Criterion", "risk"),
            ("Create a trailing stop-loss manager", "risk"),
            ("Implement a MACD indicator from scratch", "indicator"),
            ("Build an order book aggregator", "data"),
            ("Create a portfolio rebalancing algorithm", "portfolio"),
            ("Implement a backtesting engine", "backtest"),
            ("Build a WebSocket price feed handler", "data"),
            ("Create a trade journal data structure", "data"),
            ("Implement exponential moving average", "indicator"),
            ("Build a profit/loss calculator", "risk"),
            ("Create a candlestick pattern detector", "indicator"),
            ("Implement a rate limiter for API calls", "infrastructure"),
            ("Build a simple market order executor", "execution"),
        ]
        
        count = 0
        for topic, category in trading_topics:
            if count >= max_examples:
                break
            
            example = self._generate_trading_code_example(topic, category)
            if example:
                self.examples.append(example)
                self.stats["coding"] += 1
                count += 1
        
        print(f"  ✓ Generated {count} trading code examples")
    
    def _generate_trading_code_example(self, topic: str, category: str) -> Optional[Dict]:
        """Generate a trading-related coding example."""
        
        code_examples = {
            "Implement a simple moving average crossover strategy": {
                "code": '''def sma_crossover_strategy(prices: list, short_period: int = 10, long_period: int = 30) -> list:
    """
    Simple Moving Average Crossover Strategy.
    Returns list of signals: 1 (buy), -1 (sell), 0 (hold)
    """
    signals = [0] * len(prices)
    
    if len(prices) < long_period:
        return signals
    
    for i in range(long_period, len(prices)):
        short_sma = sum(prices[i-short_period:i]) / short_period
        long_sma = sum(prices[i-long_period:i]) / long_period
        prev_short = sum(prices[i-short_period-1:i-1]) / short_period
        prev_long = sum(prices[i-long_period-1:i-1]) / long_period
        
        # Bullish crossover
        if prev_short <= prev_long and short_sma > long_sma:
            signals[i] = 1
        # Bearish crossover
        elif prev_short >= prev_long and short_sma < long_sma:
            signals[i] = -1
    
    return signals''',
                "complexity": "O(n * k) where n is price length, k is long_period",
                "explanation": "Detects when short-term momentum crosses long-term trend"
            },
            "Calculate RSI (Relative Strength Index) from price data": {
                "code": '''def calculate_rsi(prices: list, period: int = 14) -> list:
    """
    Calculate RSI indicator.
    RSI = 100 - (100 / (1 + RS))
    RS = Average Gain / Average Loss
    """
    if len(prices) < period + 1:
        return [50.0] * len(prices)  # Default neutral
    
    rsi_values = [50.0] * (period)  # Not enough data initially
    
    # Calculate price changes
    changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    # Initial averages
    gains = [c if c > 0 else 0 for c in changes[:period]]
    losses = [-c if c < 0 else 0 for c in changes[:period]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    
    for i in range(period, len(changes)):
        change = changes[i]
        gain = change if change > 0 else 0
        loss = -change if change < 0 else 0
        
        # Smoothed averages (Wilder's method)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
        
        rsi_values.append(rsi)
    
    return rsi_values''',
                "complexity": "O(n) time, O(n) space",
                "explanation": "RSI measures momentum on a 0-100 scale. >70 is overbought, <30 is oversold"
            },
            "Build a position sizing calculator with Kelly Criterion": {
                "code": '''def kelly_position_size(
    win_rate: float,
    avg_win: float,
    avg_loss: float,
    kelly_fraction: float = 0.25  # Use fractional Kelly for safety
) -> float:
    """
    Calculate optimal position size using Kelly Criterion.
    
    Full Kelly: f = (p * b - q) / b
    where p = win probability, q = loss probability, b = win/loss ratio
    
    Returns fraction of capital to risk (0 to 1)
    """
    if avg_loss == 0:
        return 0.0
    
    p = win_rate  # Probability of winning
    q = 1 - win_rate  # Probability of losing
    b = abs(avg_win / avg_loss)  # Win/loss ratio
    
    # Kelly formula
    full_kelly = (p * b - q) / b
    
    # Never risk more than Kelly suggests
    if full_kelly <= 0:
        return 0.0
    
    # Apply fractional Kelly for safety
    fractional_kelly = full_kelly * kelly_fraction
    
    # Cap at reasonable maximum (10% of capital)
    return min(fractional_kelly, 0.10)


def calculate_position_size(
    account_balance: float,
    entry_price: float,
    stop_loss_price: float,
    risk_percent: float = 0.02
) -> float:
    """
    Calculate position size based on fixed percentage risk.
    """
    risk_amount = account_balance * risk_percent
    stop_distance = abs(entry_price - stop_loss_price)
    
    if stop_distance == 0:
        return 0.0
    
    position_size = risk_amount / stop_distance
    return position_size''',
                "complexity": "O(1)",
                "explanation": "Kelly optimizes long-term growth. Use fractional Kelly (25-50%) to reduce volatility."
            },
        }
        
        if topic in code_examples:
            data = code_examples[topic]
        else:
            # Generic template
            data = {
                "code": f"# Implementation for: {topic}\n# TODO: Add implementation",
                "complexity": "Depends on implementation",
                "explanation": f"This implements {topic} for trading applications."
            }
        
        instruction = f"Write Python code to: {topic}"
        
        output = f"""<think>
Problem: {topic}
Category: {category}

Approach:
1. Understand the trading concept
2. Implement with proper data structures
3. Handle edge cases
4. Optimize for real-time use
</think>

<answer>
```python
{data['code']}
```

**Complexity Analysis:**
- Time: {data['complexity']}
- Space: O(n) for storing results

**Trading Application:**
{data['explanation']}

**Usage Example:**
```python
prices = [100, 102, 101, 105, 103, 107, 104, 108, 110, 109]
# result = function(prices)
```
</answer>"""

        return self.create_example(
            instruction, output,
            source="trading_code",
            quality=1.0,
            category="coding"
        )
    
    # =========================================================================
    # ADDITIONAL SYNTHETIC GENERATORS
    # =========================================================================
    
    def generate_synthetic_trading_scenarios(self, max_examples: int = 500) -> None:
        """Generate diverse synthetic trading scenarios."""
        print(f"🎯 Generating synthetic trading scenarios...")
        
        scenarios = [
            # Entry scenarios
            ("BTC just broke above $95,000 resistance with high volume. RSI is 62. Should I buy?", "breakout_entry"),
            ("ETH dropped 8% in the last hour on no news. RSI is 22. Is this a buying opportunity?", "dip_buy"),
            ("SOL has been consolidating between $140-150 for 3 days. Which way will it break?", "consolidation"),
            ("BTC is making higher lows but volume is declining. What does this mean?", "divergence"),
            ("I see a head and shoulders pattern forming on ETH. Should I short?", "pattern_trading"),
            
            # Exit scenarios
            ("My BTC long is up 15% but momentum is slowing. Should I take profits?", "profit_taking"),
            ("Position is down 5% and hitting my mental stop. Should I hold or cut?", "stop_loss_decision"),
            ("I'm up 3x on an altcoin. How do I manage this position?", "large_profit"),
            
            # Risk scenarios
            ("I have $10,000 to trade. How should I size my first position?", "position_sizing"),
            ("What's the maximum I should risk on any single trade?", "risk_rules"),
            ("How do I set a proper stop loss for a volatile crypto?", "stop_placement"),
            
            # Market analysis
            ("Bitcoin dominance is rising. What does this mean for alts?", "btc_dominance"),
            ("Funding rates on BTC perpetuals are extremely positive. What's the implication?", "funding_rates"),
            ("The Fear & Greed Index is at 85 (Extreme Greed). Should I be worried?", "sentiment_indicator"),
            ("Open interest on ETH just hit all-time high. What should I expect?", "derivatives_analysis"),
            
            # Psychology scenarios
            ("I'm on a 5-trade winning streak. Should I increase my size?", "overconfidence"),
            ("Every trade I make goes against me immediately. Am I cursed?", "bad_luck_streak"),
            ("I can't stop checking prices every 5 minutes. Is this normal?", "addiction"),
            ("I had a great month but gave back 80% of gains in one bad trade. How do I recover?", "recovery"),
        ]
        
        count = 0
        for question, scenario_type in scenarios:
            if count >= max_examples:
                break
            
            # Generate variations of each scenario
            for variation in range(min(40, max_examples // len(scenarios))):
                if count >= max_examples:
                    break
                    
                example = self._generate_scenario_response(question, scenario_type, variation)
                if example:
                    self.examples.append(example)
                    self.stats["trading_decisions"] += 1
                    count += 1
        
        print(f"  ✓ Generated {count} synthetic trading scenarios")
    
    def _generate_scenario_response(self, question: str, scenario_type: str, variation: int) -> Optional[Dict]:
        """Generate response for trading scenario."""
        
        # Vary the question slightly
        symbols = ["BTC", "ETH", "SOL", "AVAX", "MATIC"]
        prices = {"BTC": (88000, 98000), "ETH": (2800, 3500), "SOL": (120, 160), "AVAX": (30, 45), "MATIC": (0.8, 1.2)}
        
        symbol = random.choice(symbols)
        price_range = prices.get(symbol, (100, 200))
        price = random.uniform(*price_range)
        rsi = random.uniform(15, 85)
        
        # Modify question with random values
        modified_q = question
        if "BTC" in question:
            modified_q = question.replace("BTC", symbol)
        if "$95,000" in question:
            modified_q = modified_q.replace("$95,000", f"${price:,.0f}")
        if "RSI is 62" in question:
            modified_q = modified_q.replace("RSI is 62", f"RSI is {rsi:.0f}")
        
        # Generate appropriate response based on scenario type
        if scenario_type == "breakout_entry":
            output = self._breakout_response(symbol, price, rsi)
        elif scenario_type == "dip_buy":
            output = self._dip_buy_response(symbol, price, rsi)
        elif scenario_type == "profit_taking":
            output = self._profit_taking_response(symbol, price)
        elif scenario_type == "position_sizing":
            output = self._position_sizing_response(price)
        elif scenario_type == "overconfidence":
            output = self._psychology_response("overconfidence")
        elif scenario_type in ["btc_dominance", "funding_rates", "sentiment_indicator"]:
            output = self._market_structure_response(scenario_type)
        else:
            output = self._generic_trading_response(modified_q, symbol, price, rsi)
        
        return self.create_example(
            modified_q, output,
            source="synthetic_scenario",
            quality=1.0,
            category="trading_decision"
        )
    
    def _breakout_response(self, symbol: str, price: float, rsi: float) -> str:
        return f"""<think>
Analyzing {symbol} breakout:

Breakout Validation Checklist:
1. Price action: Above resistance ✓
2. Volume: High volume confirms ✓
3. RSI: {rsi:.0f} - {"Overbought caution" if rsi > 70 else "Room to run" if rsi < 65 else "Neutral"}
4. Market context: Need to check BTC correlation

Risk assessment:
- Breakouts fail ~40% of time
- Need to see retest of breakout level for confirmation
</think>

<answer>
**Analysis: Valid breakout but wait for confirmation**

The breakout looks legitimate based on volume, but RSI at {rsi:.0f} {"suggests caution - don't chase" if rsi > 70 else "has room to run"}.

**If entering:**
- Entry: ${price:,.2f}
- Stop: ${price * 0.97:,.2f} (below breakout level)
- Target 1: ${price * 1.05:,.2f} (5%)
- Target 2: ${price * 1.10:,.2f} (10%)

**Better approach:**
Wait for a pullback to the breakout level (${price * 0.98:,.2f}) for lower-risk entry.

**Position size:** Maximum 2% account risk
</answer>"""

    def _dip_buy_response(self, symbol: str, price: float, rsi: float) -> str:
        return f"""<think>
Analyzing {symbol} dip:

Oversold Analysis:
- RSI at {rsi:.0f}: {"Extremely oversold - bounce likely" if rsi < 25 else "Oversold" if rsi < 35 else "Not yet oversold"}
- 8% drop with no news: Could be liquidation cascade or whale movement
- Key question: Is this capitulation or start of larger move?

Risk factors:
- Catching falling knives is dangerous
- Need to see stabilization first
</think>

<answer>
**Analysis: {"High probability bounce setup" if rsi < 30 else "Wait for more confirmation"}**

RSI at {rsi:.0f} {"indicates extreme oversold - statistically bounces 80%+ of time" if rsi < 25 else "is getting oversold but could go lower"}.

**Strategy:**
{"Enter 1/3 position now, add on confirmation" if rsi < 30 else "Wait for RSI < 25 or bullish candle"}

**If entering:**
- Entry: ${price:,.2f}
- Stop: ${price * 0.95:,.2f} (5% below - allow volatility)
- Target: ${price * 1.08:,.2f} (recovery to pre-dip)

**Warning:** No news drops can continue. Use tight position sizing (1% risk).
</answer>"""

    def _profit_taking_response(self, symbol: str, price: float) -> str:
        return f"""<think>
Position Management - 15% Profit:

Current situation:
- Significant unrealized gains
- Momentum slowing (warning sign)
- Paper profits can evaporate quickly

Options:
1. Close all - lock in gains
2. Close partial - reduce risk, keep upside
3. Trailing stop - let it ride with protection
</think>

<answer>
**Recommendation: Take partial profits**

With 15% gain and slowing momentum, smart money management is:

**Action Plan:**
1. **Close 50%** of position now at ${price:,.2f}
2. **Move stop** on remaining 50% to breakeven
3. **Trail stop** 5% below each new high

**Why not close all?**
Slowing momentum ≠ reversal. Trends can consolidate then continue.

**Why not hold all?**
15% is real money. Locking in 7.5% guaranteed while keeping 7.5%+ potential is optimal risk management.

**Key insight:** "You can't go broke taking profits" - but you also won't get rich closing every winner early. Balance is key.
</answer>"""

    def _position_sizing_response(self, price: float) -> str:
        account = 10000
        risk_pct = 2
        stop_pct = 3
        
        risk_amount = account * (risk_pct / 100)
        position_size = risk_amount / (price * stop_pct / 100)
        position_value = position_size * price
        
        return f"""<think>
Position Sizing Calculation:

Account: $10,000
Risk tolerance: 2% per trade = ${risk_amount:.2f} max loss

Standard approach:
1. Determine max loss acceptable
2. Calculate stop distance
3. Size position so stop = max loss
</think>

<answer>
**Position Sizing for $10,000 Account**

**Golden Rules:**
1. Never risk more than 2% per trade
2. Never have more than 6% total account at risk
3. Size position based on stop distance

**Example Calculation:**

| Parameter | Value |
|-----------|-------|
| Account | $10,000 |
| Risk per trade | 2% = ${risk_amount:.2f} |
| Entry price | ${price:,.2f} |
| Stop loss | 3% = ${price * 0.97:,.2f} |
| Position size | {position_size:.4f} units |
| Position value | ${position_value:,.2f} |

**First Trade Advice:**
Start with 1% risk ($100) until you have 20+ trades logged. This preserves capital while you learn.
</answer>"""

    def _psychology_response(self, topic: str) -> str:
        return f"""<think>
Psychology Alert: Overconfidence detected

5-trade winning streak psychological effects:
- Dopamine surge creating euphoria
- Illusion of skill (could be luck)
- Risk of increasing size at worst time
- "I can't lose" mentality is dangerous
</think>

<answer>
**DO NOT increase your position size.**

A 5-trade winning streak is great, but it's statistically expected and doesn't mean you've "figured it out."

**Reality check:**
- Even a 50% win rate strategy will have 5+ win streaks regularly
- The streak will end - often right when you size up
- Sizing up after wins = mathematical path to ruin

**What to do instead:**
1. Stick to your established position sizing rules
2. Take a small break to reset mentally
3. Review: were these good trades or lucky trades?
4. Journal what's working and what's luck

**Key insight:** Professional traders keep size CONSTANT regardless of recent performance. That discipline is what separates them from gamblers.
</answer>"""

    def _market_structure_response(self, topic: str) -> str:
        responses = {
            "btc_dominance": """<think>
Analyzing Bitcoin Dominance:

BTC dominance rising means:
- Money flowing from alts to BTC
- Risk-off sentiment (BTC = "safe haven" in crypto)
- Altcoin pain likely to continue
</think>

<answer>
**Rising BTC Dominance Analysis**

**What it means:**
- Capital rotating from altcoins to Bitcoin
- Typically happens during uncertainty or early bull markets
- Alts usually underperform BTC during dominance uptrends

**Trading implications:**
1. **Reduce altcoin exposure** - they'll likely underperform
2. **Favor BTC longs** over alt longs
3. **Wait for dominance peak** before rotating back to alts
4. **Historical pattern:** Dominance peaks, then "alt season" begins

**What to watch:**
- BTC dominance > 55% = strong alt headwind
- Dominance starting to drop = alt season approaching
</answer>""",
            
            "funding_rates": """<think>
Analyzing extreme positive funding:

High funding rates mean:
- Lots of leveraged longs paying to stay in position
- Market is crowded on one side
- Contrarian signal - often precedes pullback
</think>

<answer>
**Extreme Positive Funding Analysis**

**What it means:**
- Longs paying shorts 0.1%+ every 8 hours
- Market heavily positioned bullish
- High funding is a contrarian bearish signal

**Historical pattern:**
- Funding > 0.1% often precedes 5-15% corrections
- Doesn't mean immediate dump, but risk is elevated

**Trading implications:**
1. **Don't open new longs** at elevated funding
2. **Consider reducing long exposure**
3. **Shorts become statistically favorable** (getting paid + likely reversal)
4. **Wait for funding normalization** before new longs

**Key insight:** When everyone is long, who's left to buy?
</answer>""",
            
            "sentiment_indicator": """<think>
Analyzing Extreme Greed reading:

Fear & Greed at 85:
- Top 10% of historical readings
- Crowd is euphoric
- Classic contrarian sell signal
</think>

<answer>
**Fear & Greed at 85: Extreme Caution Warranted**

**Historical data:**
- Readings > 80 preceded corrections 70% of time
- Average pullback: 15-25%
- Does NOT mean immediate crash

**What to do:**
1. **Do not FOMO into new positions**
2. **Take profits on winning trades**
3. **Tighten stops on existing positions**
4. **Have cash ready for the dip**

**Contrarian wisdom:**
"Be fearful when others are greedy, and greedy when others are fearful." - Buffett

**Timeline:**
Extreme readings can persist for days/weeks. Don't short immediately, but reduce risk.
</answer>"""
        }
        
        return responses.get(topic, self._generic_trading_response("", "BTC", 93000, 50))

    def _generic_trading_response(self, question: str, symbol: str, price: float, rsi: float) -> str:
        return f"""<think>
Analyzing trading question about {symbol}:

Current context:
- Price: ${price:,.2f}
- RSI: {rsi:.0f}
- Question focus: {question[:50]}...

Formulating comprehensive response.
</think>

<answer>
**Analysis for {symbol} at ${price:,.2f}**

**Technical Setup:**
- RSI at {rsi:.0f}: {"Oversold - look for bounce" if rsi < 30 else "Overbought - caution" if rsi > 70 else "Neutral range"}
- Price action: Needs more context for full analysis

**General Guidance:**
1. Always use stop losses (2-3% for crypto)
2. Size positions based on account risk (max 2%)
3. Don't chase moves - wait for pullbacks
4. Have a plan before entering

**Risk management reminder:**
- Entry without exit plan = gambling
- Size matters more than direction
- Preserve capital to fight another day
</answer>"""

    def generate_risk_management_examples(self, max_examples: int = 200) -> None:
        """Generate risk management focused examples."""
        print(f"⚠️ Generating risk management examples...")
        
        risk_topics = [
            "How do I calculate the right position size?",
            "What's the Kelly Criterion and should I use it?",
            "How do I set stop losses for volatile assets?",
            "What's the maximum I should have at risk at one time?",
            "How do I manage a portfolio of multiple positions?",
            "When should I use leverage and how much?",
            "How do I calculate risk-reward ratio?",
            "What's the difference between mental and hard stops?",
            "How do I protect profits with trailing stops?",
            "What's proper risk management for a $1000 account?",
            "How many positions should I have open at once?",
            "What's the 1% rule in trading?",
            "How do I recover from a large drawdown?",
            "Should I average down on losing positions?",
            "How do I handle correlated positions?",
        ]
        
        count = 0
        for topic in risk_topics:
            if count >= max_examples:
                break
            
            for i in range(min(25, max_examples // len(risk_topics))):
                if count >= max_examples:
                    break
                    
                example = self._generate_risk_example(topic, i)
                if example:
                    self.examples.append(example)
                    self.stats["risk_management"] += 1
                    count += 1
        
        print(f"  ✓ Generated {count} risk management examples")
    
    def _generate_risk_example(self, topic: str, variation: int) -> Optional[Dict]:
        """Generate risk management response."""
        
        account_sizes = [1000, 5000, 10000, 25000, 50000, 100000]
        account = random.choice(account_sizes)
        
        modified_topic = topic
        if "$1000" in topic:
            modified_topic = topic.replace("$1000", f"${account:,}")
        
        output = f"""<think>
Risk Management Analysis:

Topic: {topic}
Account context: ${account:,}

Key principles:
1. Capital preservation is #1 priority
2. Position sizing determines survival
3. Risk per trade should be consistent
</think>

<answer>
## {topic}

**For a ${account:,} account:**

**Core Risk Rules:**
| Rule | Value |
|------|-------|
| Max risk per trade | 1-2% = ${account * 0.015:,.0f} |
| Max total exposure | 6% = ${account * 0.06:,.0f} |
| Max correlated risk | 4% = ${account * 0.04:,.0f} |
| Max positions | 3-5 at a time |

**Position Sizing Formula:**
```
Position Size = (Account × Risk%) / (Entry - Stop Loss)
```

**Example:**
- Account: ${account:,}
- Risk: 2% = ${account * 0.02:,.0f}
- Entry: $50,000
- Stop: $48,500 (3%)
- Position: ${account * 0.02:,.0f} / $1,500 = {account * 0.02 / 1500:.4f} BTC

**Key Insight:**
Your position size should ALWAYS be determined by your stop loss distance, not by how much you "want" to buy.
</answer>"""

        return self.create_example(
            modified_topic, output,
            source="risk_management",
            quality=1.0,
            category="risk_management"
        )
    
    def generate_market_analysis_examples(self, max_examples: int = 300) -> None:
        """Generate market analysis examples."""
        print(f"📊 Generating market analysis examples...")
        
        analysis_types = [
            ("technical", ["support/resistance", "trend analysis", "chart patterns", "indicator signals", "price action", "volume profile"]),
            ("fundamental", ["on-chain metrics", "network activity", "adoption metrics", "tokenomics", "developer activity", "TVL analysis"]),
            ("sentiment", ["social sentiment", "funding rates", "open interest", "whale activity", "retail vs institutions", "fear and greed"]),
            ("macro", ["correlation to stocks", "DXY impact", "interest rates", "regulatory news", "liquidity conditions", "global risk"]),
        ]
        
        symbols = ["BTC", "ETH", "SOL", "AVAX", "LINK", "MATIC", "DOT", "ADA"]
        
        count = 0
        for analysis_type, subtopics in analysis_types:
            for subtopic in subtopics:
                if count >= max_examples:
                    break
                
                for symbol in symbols:
                    if count >= max_examples:
                        break
                    
                    example = self._generate_market_analysis(analysis_type, subtopic, symbol)
                    if example:
                        self.examples.append(example)
                        self.stats["sentiment_analysis"] += 1
                        count += 1
        
        print(f"  ✓ Generated {count} market analysis examples")
    
    def _generate_market_analysis(self, analysis_type: str, subtopic: str, symbol: str) -> Optional[Dict]:
        """Generate market analysis example."""
        
        prices = {"BTC": 93500, "ETH": 3200, "SOL": 145}
        price = prices.get(symbol, 1000)
        
        instruction = f"Provide a {analysis_type} analysis of {symbol} focusing on {subtopic}."
        
        output = f"""<think>
{analysis_type.title()} Analysis for {symbol}:

Focus: {subtopic}
Current price: ${price:,}

Gathering relevant data points and formulating analysis.
</think>

<answer>
## {symbol} {analysis_type.title()} Analysis: {subtopic.title()}

**Current Price:** ${price:,}

**{subtopic.title()} Assessment:**

{"**Key Levels:**" if "support" in subtopic or "resistance" in subtopic else "**Key Metrics:**"}
- {"Support: $" + f"{price * 0.95:,.0f}" if "support" in subtopic else "Primary indicator: Bullish"}
- {"Resistance: $" + f"{price * 1.05:,.0f}" if "resistance" in subtopic else "Secondary indicator: Neutral"}
- {"Major support: $" + f"{price * 0.90:,.0f}" if "support" in subtopic else "Trend: Upward"}

**Analysis:**
Based on {subtopic}, {symbol} is showing {"strength" if random.random() > 0.5 else "consolidation"} signals.

**Trading Implication:**
- Bias: {"Bullish" if random.random() > 0.4 else "Neutral"}
- Confidence: {"High" if random.random() > 0.6 else "Medium"}
- Timeframe: {"Short-term" if "sentiment" in analysis_type else "Medium-term"}

**Action:**
{"Look for long entries on dips to support" if random.random() > 0.5 else "Wait for breakout confirmation before entering"}
</answer>"""

        return self.create_example(
            instruction, output,
            source="market_analysis",
            quality=0.95,
            category="sentiment_analysis"
        )
    
    def generate_indicator_examples(self, max_examples: int = 200) -> None:
        """Generate technical indicator interpretation examples."""
        print(f"📉 Generating indicator interpretation examples...")
        
        indicators = [
            ("RSI", [15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85]),
            ("MACD", ["bullish crossover", "bearish crossover", "positive divergence", "negative divergence", "histogram expansion", "histogram contraction"]),
            ("Moving Averages", ["golden cross", "death cross", "price above MA", "price below MA", "MA ribbon expansion", "MA ribbon contraction"]),
            ("Bollinger Bands", ["squeeze", "upper band touch", "lower band touch", "walking the band", "band expansion", "mean reversion"]),
            ("Volume", ["high volume breakout", "low volume rally", "volume divergence", "climax volume", "accumulation", "distribution"]),
            ("Fibonacci", ["38.2% retracement", "50% retracement", "61.8% retracement", "78.6% retracement", "extension targets", "confluence zones"]),
            ("Stochastic", ["oversold", "overbought", "bullish crossover", "bearish crossover"]),
            ("ADX", ["strong trend", "weak trend", "trend starting", "trend ending"]),
        ]
        
        symbols = ["BTC", "ETH", "SOL", "AVAX", "LINK"]
        
        count = 0
        for indicator, values in indicators:
            for value in values:
                if count >= max_examples:
                    break
                
                for symbol in symbols:
                    if count >= max_examples:
                        break
                    
                    example = self._generate_indicator_example(indicator, value, symbol)
                    if example:
                        self.examples.append(example)
                        self.stats["trading_decisions"] += 1
                        count += 1
        
        print(f"  ✓ Generated {count} indicator examples")
    
    def _generate_indicator_example(self, indicator: str, value, symbol: str) -> Optional[Dict]:
        """Generate indicator interpretation example."""
        
        prices = {"BTC": random.uniform(88000, 98000), "ETH": random.uniform(2900, 3400), "SOL": random.uniform(130, 160)}
        price = prices.get(symbol, 1000)
        
        if indicator == "RSI":
            rsi_value = value if isinstance(value, (int, float)) else 50
            instruction = f"{symbol} RSI is at {rsi_value}. What does this indicate and how should I trade it?"
            
            if rsi_value < 30:
                signal = "OVERSOLD - Bullish"
                action = "Look for long entries"
                explanation = "RSI below 30 indicates oversold conditions. Historically, prices tend to bounce from these levels."
            elif rsi_value > 70:
                signal = "OVERBOUGHT - Bearish"
                action = "Consider taking profits or shorting"
                explanation = "RSI above 70 indicates overbought conditions. Pullback or reversal likely."
            else:
                signal = "NEUTRAL"
                action = "Wait for clearer signal"
                explanation = "RSI in neutral zone doesn't provide strong directional bias."
            
            output = f"""<think>
RSI Analysis for {symbol}:
- Current RSI: {rsi_value}
- Zone: {"Oversold" if rsi_value < 30 else "Overbought" if rsi_value > 70 else "Neutral"}

Historical context:
- RSI < 30: Bounce 75% of time within 3 days
- RSI > 70: Pullback 65% of time within 3 days
</think>

<answer>
## RSI Analysis: {signal}

**{symbol} RSI: {rsi_value}**

**Interpretation:**
{explanation}

**Trading Signal:** {action}

**Strategy:**
{"Wait for bullish candle confirmation, then enter long with stop below recent low" if rsi_value < 30 else "Scale out of longs, tighten stops, or look for short entries" if rsi_value > 70 else "Use other indicators for confirmation before trading"}

**Risk Note:**
RSI can stay extreme for extended periods. Never trade RSI alone - confirm with price action and other indicators.
</answer>"""

        elif indicator == "MACD":
            instruction = f"{symbol} is showing a {value} on the MACD. What does this mean?"
            
            bullish = "bullish" in str(value).lower() or "positive" in str(value).lower()
            
            output = f"""<think>
MACD Signal Analysis:
- Signal: {value}
- Implication: {"Bullish momentum" if bullish else "Bearish momentum"}

MACD is a trend-following momentum indicator.
</think>

<answer>
## MACD Analysis: {value.title()}

**Signal Type:** {"BULLISH" if bullish else "BEARISH"}

**What this means:**
{"The MACD line crossing above the signal line indicates building bullish momentum. This often precedes price increases." if "crossover" in str(value).lower() and bullish else "The MACD showing divergence from price suggests hidden momentum that may soon reflect in price action." if "divergence" in str(value).lower() else "MACD is providing a directional bias signal."}

**Trading Approach:**
- {"Look for long entries" if bullish else "Consider shorts or reducing longs"}
- Confirm with price action and volume
- Use MACD histogram for momentum strength

**Caution:**
MACD is a lagging indicator. The move may already be partially priced in.
</answer>"""

        else:
            instruction = f"Explain how to interpret {indicator} showing {value} for {symbol}."
            
            output = f"""<think>
Technical Analysis - {indicator}:
- Signal: {value}
- Asset: {symbol}
- Price: ${price:,.2f}
</think>

<answer>
## {indicator} Analysis: {value}

**Current Setup on {symbol}:**
- Price: ${price:,.2f}
- Signal: {value}

**Interpretation:**
This {indicator} signal typically indicates {"momentum building" if "breakout" in str(value).lower() or "cross" in str(value).lower() else "a potential reversal or continuation"}.

**Trading Implications:**
1. {"Bullish bias - look for long entries" if random.random() > 0.5 else "Cautious approach - wait for confirmation"}
2. Set stops based on recent structure
3. Take profits at logical resistance/support levels

**Remember:** No single indicator is perfect. Always use multiple confirmations.
</answer>"""

        return self.create_example(
            instruction, output,
            source="indicator_analysis",
            quality=1.0,
            category="trading_decision"
        )

    # =========================================================================
    # MAIN GENERATION FLOW
    # =========================================================================
    
    def generate_all(self) -> None:
        """Generate all training examples."""
        print("\n" + "="*60)
        print("🚀 PersRM Expert Training Data Generator")
        print("="*60 + "\n")
        
        # Generate from each source
        self.generate_trading_decisions(max_examples=400)
        self.generate_psychology_coaching(max_examples=200)
        self.generate_strategy_analysis(max_examples=100)
        self.generate_news_analysis(max_examples=300)
        self.generate_trading_code(max_examples=200)
        
        # Generate additional synthetic examples
        self.generate_synthetic_trading_scenarios(max_examples=800)
        self.generate_risk_management_examples(max_examples=400)
        self.generate_market_analysis_examples(max_examples=500)
        self.generate_indicator_examples(max_examples=300)
        
        print("\n" + "="*60)
        print(f"📊 Generation Complete: {len(self.examples)} total examples")
        print("="*60)
        
        for category, count in self.stats.items():
            if count > 0:
                print(f"  {category}: {count}")
    
    def save(self) -> None:
        """Save training and validation data."""
        # Shuffle examples
        random.shuffle(self.examples)
        
        # Split 90/10
        split_idx = int(len(self.examples) * 0.9)
        train_examples = self.examples[:split_idx]
        val_examples = self.examples[split_idx:]
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save training data
        train_file = self.output_dir / "train_expert.jsonl"
        with open(train_file, 'w', encoding='utf-8') as f:
            for example in train_examples:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")
        
        # Save validation data
        val_file = self.output_dir / "val_expert.jsonl"
        with open(val_file, 'w', encoding='utf-8') as f:
            for example in val_examples:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")
        
        print(f"\n✅ Saved {len(train_examples)} training examples to {train_file}")
        print(f"✅ Saved {len(val_examples)} validation examples to {val_file}")


def main():
    parser = argparse.ArgumentParser(description="Generate expert training data for PersRM")
    parser.add_argument("--output-dir", type=str, 
                       default=str(CHATOS_V02 / "data" / "persrm"),
                       help="Output directory for training data")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    generator = ExpertTrainingGenerator(output_dir)
    generator.generate_all()
    generator.save()


if __name__ == "__main__":
    main()

