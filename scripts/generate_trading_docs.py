#!/usr/bin/env python3
"""
Trading Algorithm Documentation Generator
==========================================
Generates comprehensive training examples covering trading and investment
algorithms from institutional to code-level detail.

Tiers:
1. Big Picture (Institutional Level)
2. Strategy Categories
3. Technical Implementation
4. Code-Level Detail
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import argparse

# Output directory
HOME = Path.home()
CHATOS_V02 = HOME / "ChatOS-v0.2"
OUTPUT_DIR = CHATOS_V02 / "data" / "persrm"


class TradingDocsGenerator:
    """Generate comprehensive trading documentation examples."""
    
    def __init__(self):
        self.examples: List[Dict] = []
        self.stats = {
            "institutional": 0,
            "strategies": 0,
            "technical": 0,
            "risk": 0,
            "execution": 0,
            "backtesting": 0,
            "code": 0,
        }
    
    def create_example(self, instruction: str, output: str, 
                      category: str, quality: float = 1.0) -> Dict:
        """Create a training example with metadata."""
        return {
            "instruction": instruction.strip(),
            "output": output.strip(),
            "metadata": {
                "source": "trading_docs",
                "category": category,
                "quality": quality,
                "generated_at": datetime.now().isoformat()
            }
        }

    # =========================================================================
    # TIER 1: INSTITUTIONAL LEVEL
    # =========================================================================
    
    def generate_institutional(self, max_examples: int = 300) -> None:
        """Generate institutional/hedge fund level documentation."""
        print("🏦 Generating institutional documentation...")
        
        topics = self._get_institutional_topics()
        count = 0
        
        for topic, qa_pairs in topics.items():
            for q, a in qa_pairs:
                if count >= max_examples:
                    break
                example = self.create_example(q, a, "institutional", 1.0)
                self.examples.append(example)
                self.stats["institutional"] += 1
                count += 1
        
        print(f"  ✓ Generated {count} institutional examples")
    
    def _get_institutional_topics(self) -> Dict[str, List[tuple]]:
        """Return institutional level Q&A pairs."""
        return {
            "hedge_fund_structure": [
                ("What is the structure of a quantitative hedge fund?",
                 """<think>
A quantitative hedge fund has several key structural components:
1. Front office (trading, research)
2. Middle office (risk, compliance)
3. Back office (operations, settlement)
4. Technology infrastructure

Each plays a critical role in alpha generation and risk management.
</think>

<answer>
## Quantitative Hedge Fund Structure

### Front Office
- **Portfolio Managers**: Make final allocation decisions
- **Quant Researchers**: Develop alpha models and strategies
- **Traders**: Execute orders, manage market impact

### Middle Office
- **Risk Management**: Monitor VaR, drawdowns, exposure limits
- **Compliance**: Ensure regulatory adherence (SEC, CFTC)
- **Performance Attribution**: Analyze returns by factor

### Back Office
- **Operations**: Trade settlement, reconciliation
- **Fund Accounting**: NAV calculation, investor reporting
- **IT Infrastructure**: Systems maintenance, data management

### Technology Stack
- **Data Pipeline**: Market data ingestion, cleaning, storage
- **Research Platform**: Backtesting, signal generation
- **Execution Management**: Order routing, smart order routing
- **Risk Systems**: Real-time monitoring, alerts

### Typical Team Size
- Small quant fund: 10-30 people
- Mid-size: 50-200 people
- Large (Citadel, Two Sigma): 1000+ people
</answer>"""),

                ("How do hedge funds generate alpha?",
                 """<think>
Alpha generation is the core value proposition of hedge funds.
It requires:
1. Information advantage
2. Processing advantage
3. Execution advantage
4. Risk management discipline
</think>

<answer>
## How Hedge Funds Generate Alpha

### Definition
Alpha = Returns above benchmark (risk-adjusted excess return)

### Alpha Sources

**1. Information Edge**
- Alternative data (satellite, credit card, web scraping)
- Proprietary research and analysis
- Expert networks and industry contacts

**2. Analytical Edge**
- Superior quantitative models
- Machine learning and AI
- Factor discovery and combination

**3. Execution Edge**
- Low-latency infrastructure
- Smart order routing
- Transaction cost minimization

**4. Structural Edge**
- Access to private markets
- Prime brokerage relationships
- Securities lending revenue

### Alpha Decay
- Signals lose effectiveness over time
- Competition erodes edge
- Must continuously develop new signals

### Measuring Alpha
```
Alpha = Portfolio Return - (Risk-Free Rate + Beta × Market Return)
```

A positive alpha indicates outperformance vs. benchmark.
</answer>"""),

                ("What is the difference between systematic and discretionary trading?",
                 """<think>
Systematic vs discretionary represents two fundamental approaches:
- Systematic: Rule-based, algorithmic
- Discretionary: Human judgment-based

Each has advantages and challenges.
</think>

<answer>
## Systematic vs. Discretionary Trading

### Systematic Trading
**Definition**: Algorithmic, rule-based strategies executed by computers

**Characteristics:**
- Backtestable and quantifiable
- Emotionless execution
- Scalable across markets
- Requires significant technology investment

**Advantages:**
- Consistent execution
- No emotional bias
- Can process vast data
- 24/7 operation

**Disadvantages:**
- Requires historical data
- May miss regime changes
- Crowded when strategies similar

### Discretionary Trading
**Definition**: Human traders make decisions based on judgment

**Characteristics:**
- Relies on experience and intuition
- Can adapt to novel situations
- Fundamental analysis often key

**Advantages:**
- Flexible to new information
- Can understand context
- Works in data-sparse environments

**Disadvantages:**
- Emotional biases
- Limited scalability
- Inconsistent execution

### Hybrid Approach
Many successful funds combine both:
- Systematic signal generation
- Discretionary position sizing
- Human override for extreme events
</answer>"""),

                ("Explain the fund of funds model",
                 """<think>
Fund of funds (FoF) is a meta-investment structure.
Key aspects:
- Diversification across managers
- Due diligence specialization
- Additional fee layer
</think>

<answer>
## Fund of Funds Model

### Definition
A fund that invests in other hedge funds rather than directly in securities.

### Structure
```
Investor → Fund of Funds → Multiple Hedge Funds → Securities
```

### Advantages
1. **Diversification**: Exposure to multiple strategies and managers
2. **Access**: Entry to funds with high minimums
3. **Due Diligence**: Professional manager selection
4. **Risk Management**: Portfolio-level risk oversight

### Disadvantages
1. **Double Fees**: Pay FoF fees + underlying fund fees
2. **Return Dilution**: Diversification reduces upside
3. **Transparency**: Less visibility into positions
4. **Liquidity**: Often longer lock-up periods

### Fee Structure
- Underlying funds: 2% management + 20% performance
- FoF layer: 1% management + 10% performance
- Total: ~3% + 30% (significant drag)

### When It Makes Sense
- Smaller investors seeking diversification
- Institutional investors needing manager selection
- Access to capacity-constrained funds
</answer>"""),
            ],

            "risk_framework": [
                ("What is Value at Risk (VaR) and how is it used in hedge funds?",
                 """<think>
VaR is a fundamental risk metric in finance.
Key aspects:
1. Definition and interpretation
2. Calculation methods
3. Limitations
4. Practical usage
</think>

<answer>
## Value at Risk (VaR)

### Definition
VaR answers: "What is the maximum loss over a given time period at a specified confidence level?"

**Example**: 1-day 95% VaR of $1M means there's a 5% chance of losing more than $1M in one day.

### Calculation Methods

**1. Historical VaR**
```python
import numpy as np

def historical_var(returns, confidence=0.95):
    return np.percentile(returns, (1 - confidence) * 100)
```

**2. Parametric VaR**
```python
def parametric_var(portfolio_value, volatility, confidence=0.95):
    from scipy.stats import norm
    z_score = norm.ppf(1 - confidence)
    return portfolio_value * volatility * z_score
```

**3. Monte Carlo VaR**
- Simulate thousands of scenarios
- Calculate losses in each
- Find percentile threshold

### Usage in Hedge Funds
- Daily risk reporting
- Position limit setting
- Capital allocation
- Regulatory compliance

### Limitations
1. Doesn't capture tail risk (use CVaR/Expected Shortfall)
2. Assumes normal distributions (often wrong)
3. Backward-looking
4. Not additive across portfolios

### Best Practices
- Use multiple VaR measures
- Stress test beyond VaR
- Monitor VaR breaches
- Combine with other metrics (Sharpe, drawdown)
</answer>"""),

                ("How do hedge funds manage drawdowns?",
                 """<think>
Drawdown management is critical for fund survival.
Key elements:
1. Prevention (position sizing)
2. Detection (monitoring)
3. Response (de-risking)
4. Recovery (capital preservation)
</think>

<answer>
## Drawdown Management in Hedge Funds

### Definition
Drawdown = Peak-to-trough decline in portfolio value

```python
def calculate_drawdown(equity_curve):
    peak = equity_curve.expanding().max()
    drawdown = (equity_curve - peak) / peak
    return drawdown
```

### Prevention Strategies

**1. Position Sizing**
- Kelly criterion or fractional Kelly
- Maximum position limits (e.g., 5% per position)
- Sector/factor exposure limits

**2. Diversification**
- Uncorrelated strategies
- Multiple asset classes
- Geographic diversification

**3. Stop Losses**
- Position-level stops
- Strategy-level stops
- Portfolio-level circuit breakers

### Detection Systems

**Real-time Monitoring:**
- Intraday P&L tracking
- VaR utilization
- Margin usage
- Correlation breakdown alerts

### Response Protocols

**Typical Drawdown Limits:**
| Drawdown Level | Action |
|----------------|--------|
| -5% | Review positions |
| -10% | Reduce gross exposure 25% |
| -15% | Reduce gross exposure 50% |
| -20% | Emergency risk-off |

### Recovery Strategy
1. Preserve remaining capital
2. Reduce position sizes
3. Return to normal sizing gradually
4. Avoid revenge trading

### Key Metric: Recovery Factor
```
Recovery Factor = Net Profit / Max Drawdown
```
Target: > 3.0 for robust strategies
</answer>"""),
            ],

            "alpha_research": [
                ("How do quant funds conduct alpha research?",
                 """<think>
Alpha research is the lifeblood of quant funds.
Process includes:
1. Idea generation
2. Data collection
3. Model building
4. Backtesting
5. Paper trading
6. Live deployment
</think>

<answer>
## Quant Alpha Research Process

### 1. Idea Generation
**Sources:**
- Academic papers (SSRN, arXiv)
- Market observations
- Alternative data exploration
- Factor decomposition of returns

**Good Ideas Have:**
- Economic rationale
- Testable hypothesis
- Sufficient data availability
- Reasonable implementation cost

### 2. Data Collection & Processing
```python
# Example: Alternative data pipeline
class DataPipeline:
    def ingest(self, source):
        raw_data = self.fetch(source)
        cleaned = self.clean(raw_data)
        features = self.engineer_features(cleaned)
        return features
```

### 3. Signal Construction
**Common Approaches:**
- Linear factor models
- Machine learning (RF, XGBoost, Neural Nets)
- Statistical patterns (mean reversion, momentum)

### 4. Backtesting
**Best Practices:**
- Out-of-sample testing
- Walk-forward analysis
- Transaction cost modeling
- Slippage and market impact
- Multiple time periods

**Red Flags:**
- Too many parameters (overfitting)
- Survivorship bias
- Look-ahead bias
- Data snooping

### 5. Paper Trading
- 3-6 months minimum
- Compare to backtest expectations
- Execution quality analysis

### 6. Live Deployment
- Start with small allocation
- Gradually scale with confidence
- Continuous monitoring
- Decay analysis

### Research Team Structure
- Junior researchers: Data processing, initial testing
- Senior researchers: Model development, refinement
- Portfolio managers: Final allocation decisions
</answer>"""),
            ],

            "regulatory": [
                ("What regulations apply to hedge funds?",
                 """<think>
Hedge fund regulations vary by jurisdiction.
Key areas:
1. Registration requirements
2. Reporting obligations
3. Trading restrictions
4. Investor protections
</think>

<answer>
## Hedge Fund Regulatory Framework

### US Regulations

**SEC (Securities and Exchange Commission)**
- Form ADV: Adviser registration
- Form PF: Systemic risk reporting (>$150M AUM)
- Form 13F: Quarterly holdings (>$100M)
- Regulation D: Private placement rules

**CFTC (Commodity Futures Trading Commission)**
- CPO/CTA registration
- Commodity pool reporting
- Position limits on futures

**FINRA**
- Broker-dealer oversight
- Trade reporting (CAT, OATS)

### Key Compliance Areas

**1. Anti-Money Laundering (AML)**
- Know Your Customer (KYC)
- Suspicious activity reporting
- Source of funds verification

**2. Insider Trading**
- Material non-public information
- Information barriers (Chinese walls)
- Personal trading policies

**3. Market Manipulation**
- Spoofing/layering prohibition
- Front-running restrictions
- Best execution obligations

### European Regulations
- AIFMD: Alternative Investment Fund Managers Directive
- MiFID II: Market transparency, best execution
- EMIR: Derivatives reporting

### Compliance Infrastructure
```
Chief Compliance Officer
├── Trade Surveillance
├── Regulatory Reporting
├── Policy & Training
└── Investor Relations Compliance
```

### Penalties for Non-Compliance
- Fines (millions to billions)
- Trading bans
- Criminal prosecution
- Reputational damage
</answer>"""),
            ],
        }

    # =========================================================================
    # TIER 2: STRATEGY CATEGORIES
    # =========================================================================
    
    def generate_strategies(self, max_examples: int = 500) -> None:
        """Generate strategy type documentation."""
        print("📈 Generating strategy documentation...")
        
        topics = self._get_strategy_topics()
        count = 0
        
        for topic, qa_pairs in topics.items():
            for q, a in qa_pairs:
                if count >= max_examples:
                    break
                example = self.create_example(q, a, "strategies", 1.0)
                self.examples.append(example)
                self.stats["strategies"] += 1
                count += 1
        
        print(f"  ✓ Generated {count} strategy examples")
    
    def _get_strategy_topics(self) -> Dict[str, List[tuple]]:
        """Return strategy category Q&A pairs."""
        return {
            "momentum": [
                ("Explain momentum trading strategies",
                 """<think>
Momentum is one of the most persistent market anomalies.
Key aspects:
1. Price momentum
2. Factor momentum
3. Time-series vs cross-sectional
</think>

<answer>
## Momentum Trading Strategies

### Definition
Momentum = "Winners keep winning, losers keep losing"
Assets that performed well recently tend to continue performing well.

### Types of Momentum

**1. Price Momentum (Time-Series)**
```python
def time_series_momentum(prices, lookback=252):
    returns = prices.pct_change(lookback)
    signal = np.sign(returns)  # Long if positive, short if negative
    return signal
```

**2. Cross-Sectional Momentum**
```python
def cross_sectional_momentum(returns_df, lookback=252, top_n=10):
    momentum = returns_df.rolling(lookback).sum()
    ranks = momentum.rank(axis=1, ascending=False)
    longs = ranks <= top_n
    shorts = ranks >= len(ranks.columns) - top_n
    return longs, shorts
```

**3. Factor Momentum**
- Momentum in factor returns themselves
- Go long factors with positive momentum

### Key Parameters
| Parameter | Typical Range |
|-----------|---------------|
| Lookback | 3-12 months |
| Holding period | 1-3 months |
| Skip period | 1 week (avoid reversal) |
| Rebalance | Monthly |

### Why Momentum Works
- Behavioral: Underreaction to news
- Institutional: Herding behavior
- Fundamental: Gradual information diffusion

### Risks
- **Momentum crashes**: Sharp reversals (2009)
- **High turnover**: Transaction costs
- **Crowding**: Popular strategy

### Enhancement Techniques
- Volatility scaling
- Factor timing
- Machine learning filters
</answer>"""),

                ("What is mean reversion and how do you trade it?",
                 """<think>
Mean reversion is the counterpart to momentum.
Prices tend to revert to an average over time.
Key considerations:
1. Identifying mean
2. Timing entry/exit
3. Risk management
</think>

<answer>
## Mean Reversion Trading

### Definition
Mean reversion assumes prices fluctuate around a fair value and will return to that value over time.

### Mathematical Foundation
**Ornstein-Uhlenbeck Process:**
```
dX = θ(μ - X)dt + σdW
```
Where:
- θ = speed of reversion
- μ = long-term mean
- σ = volatility

### Implementation

**1. Bollinger Band Strategy**
```python
def bollinger_mean_reversion(prices, window=20, num_std=2):
    sma = prices.rolling(window).mean()
    std = prices.rolling(window).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    
    # Signals
    long_signal = prices < lower  # Buy oversold
    short_signal = prices > upper  # Sell overbought
    return long_signal, short_signal
```

**2. Z-Score Trading**
```python
def zscore_strategy(prices, lookback=60, entry_z=2, exit_z=0):
    zscore = (prices - prices.rolling(lookback).mean()) / prices.rolling(lookback).std()
    
    long_entry = zscore < -entry_z
    short_entry = zscore > entry_z
    exit = abs(zscore) < exit_z
    return long_entry, short_entry, exit
```

**3. Pairs Trading**
- Find cointegrated pairs
- Trade the spread
- Mean reversion of spread

### Key Metrics
- **Half-life**: Time to revert halfway to mean
- **Hurst Exponent**: H < 0.5 indicates mean reversion

### When Mean Reversion Works
- Range-bound markets
- High liquidity instruments
- Short timeframes

### When It Fails
- Trending markets
- Regime changes
- Fundamental shifts
</answer>"""),
            ],

            "statistical_arbitrage": [
                ("Explain statistical arbitrage strategies",
                 """<think>
Stat arb is a systematic approach to market-neutral trading.
Key components:
1. Pair selection
2. Signal generation
3. Risk management
4. Execution
</think>

<answer>
## Statistical Arbitrage

### Definition
Statistical arbitrage exploits pricing inefficiencies using quantitative methods while maintaining market neutrality.

### Core Concepts

**1. Market Neutrality**
- Beta = 0 (no market exposure)
- Dollar neutral: Long $ = Short $
- Beta neutral: Long β = Short β

**2. Mean Reversion**
- Spread between related securities reverts
- Profit from temporary mispricing

### Common Approaches

**Pairs Trading**
```python
from statsmodels.tsa.stattools import coint

def find_cointegrated_pairs(prices_df, p_value_threshold=0.05):
    n = len(prices_df.columns)
    pairs = []
    for i in range(n):
        for j in range(i+1, n):
            stock1 = prices_df.iloc[:, i]
            stock2 = prices_df.iloc[:, j]
            score, pvalue, _ = coint(stock1, stock2)
            if pvalue < p_value_threshold:
                pairs.append((prices_df.columns[i], prices_df.columns[j], pvalue))
    return pairs
```

**Factor Models**
```python
# PCA-based stat arb
from sklearn.decomposition import PCA

def factor_model_residuals(returns, n_factors=5):
    pca = PCA(n_components=n_factors)
    factors = pca.fit_transform(returns)
    reconstructed = pca.inverse_transform(factors)
    residuals = returns - reconstructed  # Idiosyncratic returns
    return residuals
```

### Execution
- TWAP/VWAP for entry/exit
- Minimize market impact
- Trade in baskets

### Risk Management
- Sector neutrality
- Factor exposure limits
- Position limits per pair
- Maximum drawdown rules

### P&L Drivers
1. Spread reversion (alpha)
2. Financing costs (cost)
3. Transaction costs (cost)
4. Borrow costs for shorts (cost)
</answer>"""),
            ],

            "market_making": [
                ("How do market making algorithms work?",
                 """<think>
Market making is about providing liquidity and capturing the bid-ask spread.
Key elements:
1. Quote management
2. Inventory control
3. Adverse selection
4. Latency
</think>

<answer>
## Market Making Algorithms

### Definition
Market makers provide liquidity by continuously quoting bid and ask prices, profiting from the spread.

### Core Economics
```
Profit = (Ask - Bid) × Volume - Costs - Adverse Selection Losses
```

### Basic Market Making Model

**Avellaneda-Stoikov Model**
```python
def optimal_quotes(mid_price, inventory, volatility, risk_aversion, T):
    # Reservation price (adjust for inventory)
    r = mid_price - inventory * risk_aversion * volatility**2 * T
    
    # Optimal spread
    spread = risk_aversion * volatility**2 * T + (2/risk_aversion) * np.log(1 + risk_aversion/k)
    
    bid = r - spread/2
    ask = r + spread/2
    return bid, ask
```

### Key Components

**1. Quote Management**
- Dynamic spread based on volatility
- Skew quotes based on inventory
- Layer quotes at multiple levels

**2. Inventory Control**
- Target zero inventory
- Skew prices to reduce position
- Maximum inventory limits

**3. Adverse Selection**
- Toxic flow detection
- Cancel quotes before adverse moves
- Analyze order flow patterns

**4. Latency**
- Co-location at exchanges
- FPGA/hardware acceleration
- Optimized network paths

### Risk Management
```python
class MMRiskManager:
    def __init__(self, max_inventory, max_loss):
        self.max_inventory = max_inventory
        self.max_loss = max_loss
    
    def check_limits(self, inventory, pnl):
        if abs(inventory) > self.max_inventory:
            return "FLATTEN"
        if pnl < -self.max_loss:
            return "STOP"
        return "OK"
```

### Revenue Sources
1. Bid-ask spread capture
2. Exchange rebates (maker fees)
3. Last look privilege (some venues)
</answer>"""),
            ],

            "event_driven": [
                ("Explain event-driven trading strategies",
                 """<think>
Event-driven strategies capitalize on corporate events.
Types include:
1. Merger arbitrage
2. Earnings plays
3. Spin-offs
4. Restructuring
</think>

<answer>
## Event-Driven Trading Strategies

### Definition
Event-driven strategies profit from price movements around corporate events or announcements.

### Strategy Types

**1. Merger Arbitrage**
```python
def merger_arb_spread(target_price, deal_price, acquirer_price=None, exchange_ratio=None):
    if exchange_ratio:  # Stock deal
        implied_value = acquirer_price * exchange_ratio
    else:  # Cash deal
        implied_value = deal_price
    
    spread = (implied_value - target_price) / target_price
    return spread

# Typical spreads: 2-10% for announced deals
```

**Trade Structure:**
- Long target company
- Short acquirer (if stock deal)
- Profit if deal closes

**2. Earnings Strategies**
```python
def earnings_momentum(earnings_surprise, price_drift_days=60):
    # Post-Earnings Announcement Drift (PEAD)
    if earnings_surprise > 0:
        return "LONG"  # Positive surprise → continued drift up
    else:
        return "SHORT"
```

**Approaches:**
- Pre-earnings volatility selling
- Post-earnings drift capture
- Earnings surprise prediction

**3. Spin-offs**
- Parent company distributes subsidiary shares
- Often mispriced initially
- Small cap effect opportunity

**4. Restructuring/Distressed**
- Companies in financial distress
- Debt vs equity plays
- Bankruptcy emergence

### Risk Management
| Event Type | Key Risk | Hedge |
|------------|----------|-------|
| M&A | Deal break | Put options |
| Earnings | Gap risk | Straddles |
| Spin-off | Liquidity | Size limits |

### Data Requirements
- SEC filings (8-K, 13-D, 13-F)
- News feeds
- Earnings calendars
- M&A databases
</answer>"""),
            ],
        }

    # =========================================================================
    # TIER 3: TECHNICAL ANALYSIS
    # =========================================================================
    
    def generate_technical(self, max_examples: int = 600) -> None:
        """Generate technical analysis documentation."""
        print("📊 Generating technical analysis documentation...")
        
        # Generate indicator examples
        indicators = self._get_indicator_examples()
        count = 0
        
        for indicator, qa_pairs in indicators.items():
            for q, a in qa_pairs:
                if count >= max_examples:
                    break
                example = self.create_example(q, a, "technical", 1.0)
                self.examples.append(example)
                self.stats["technical"] += 1
                count += 1
        
        print(f"  ✓ Generated {count} technical examples")
    
    def _get_indicator_examples(self) -> Dict[str, List[tuple]]:
        """Return technical indicator Q&A pairs."""
        return {
            "rsi": [
                ("How do I implement and use RSI for trading?",
                 """<think>
RSI (Relative Strength Index) is a momentum oscillator.
Key aspects:
1. Calculation formula
2. Interpretation
3. Trading signals
4. Common mistakes
</think>

<answer>
## RSI (Relative Strength Index)

### Formula
```python
def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = pd.Series(gains).rolling(window=period).mean()
    avg_loss = pd.Series(losses).rolling(window=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi
```

### Interpretation
| RSI Value | Meaning |
|-----------|---------|
| > 70 | Overbought |
| < 30 | Oversold |
| 50 | Neutral |

### Trading Signals

**1. Overbought/Oversold**
```python
def rsi_signals(rsi, overbought=70, oversold=30):
    buy = rsi < oversold
    sell = rsi > overbought
    return buy, sell
```

**2. Divergence**
- Price makes new high, RSI doesn't = bearish divergence
- Price makes new low, RSI doesn't = bullish divergence

**3. RSI Trend Lines**
- Draw trend lines on RSI itself
- Breaks can precede price breaks

### Advanced Usage
- Use multiple timeframes
- Combine with trend filters
- Adjust periods for volatility

### Common Mistakes
1. Using RSI alone (need confirmation)
2. Ignoring trend context
3. Fixed thresholds for all markets
</answer>"""),
            ],
            
            "macd": [
                ("Explain MACD indicator and how to trade with it",
                 """<think>
MACD is a trend-following momentum indicator.
Components:
1. MACD line
2. Signal line
3. Histogram
</think>

<answer>
## MACD (Moving Average Convergence Divergence)

### Calculation
```python
def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram
```

### Components
1. **MACD Line**: Fast EMA - Slow EMA
2. **Signal Line**: EMA of MACD line
3. **Histogram**: MACD - Signal (momentum)

### Trading Signals

**1. Crossovers**
```python
def macd_crossover(macd, signal):
    bullish = (macd > signal) & (macd.shift(1) <= signal.shift(1))
    bearish = (macd < signal) & (macd.shift(1) >= signal.shift(1))
    return bullish, bearish
```

**2. Zero Line Cross**
- MACD crosses above 0: Bullish
- MACD crosses below 0: Bearish

**3. Divergence**
- Price up, MACD down = bearish divergence
- Price down, MACD up = bullish divergence

**4. Histogram**
- Growing: Momentum increasing
- Shrinking: Momentum decreasing

### Best Practices
- Use with trend identification
- Wait for confirmation
- Avoid in ranging markets
- Multiple timeframe analysis

### Parameter Optimization
| Market Type | Fast | Slow | Signal |
|-------------|------|------|--------|
| Standard | 12 | 26 | 9 |
| Fast | 5 | 13 | 6 |
| Slow | 19 | 39 | 9 |
</answer>"""),
            ],

            "moving_averages": [
                ("How do I use moving averages in trading strategies?",
                 """<think>
Moving averages are fundamental technical tools.
Types:
1. SMA (Simple)
2. EMA (Exponential)
3. WMA (Weighted)
Uses:
1. Trend identification
2. Support/resistance
3. Crossover signals
</think>

<answer>
## Moving Averages in Trading

### Types and Calculation

**Simple Moving Average (SMA)**
```python
def sma(prices, period):
    return prices.rolling(window=period).mean()
```

**Exponential Moving Average (EMA)**
```python
def ema(prices, period):
    return prices.ewm(span=period, adjust=False).mean()
```

**Weighted Moving Average (WMA)**
```python
def wma(prices, period):
    weights = np.arange(1, period + 1)
    return prices.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum())
```

### Common Strategies

**1. Trend Following**
```python
def trend_following(price, ma_period=200):
    ma = sma(price, ma_period)
    trend = "BULLISH" if price > ma else "BEARISH"
    return trend
```

**2. MA Crossover**
```python
def ma_crossover(prices, fast=50, slow=200):
    fast_ma = sma(prices, fast)
    slow_ma = sma(prices, slow)
    
    golden_cross = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
    death_cross = (fast_ma < slow_ma) & (fast_ma.shift(1) >= slow_ma.shift(1))
    return golden_cross, death_cross
```

**3. MA Ribbon**
```python
def ma_ribbon(prices, periods=[10, 20, 30, 40, 50]):
    return {p: ema(prices, p) for p in periods}
```

### Key Periods
| Period | Use Case |
|--------|----------|
| 9-10 | Short-term trend |
| 20-21 | Swing trading |
| 50 | Intermediate trend |
| 200 | Long-term trend |

### Support and Resistance
- Price often bounces off key MAs
- 50 and 200 MA are widely watched
- Act as dynamic S/R levels

### Tips
- EMA reacts faster to price changes
- Use multiple timeframes
- MA works best in trending markets
- Lagging indicator - use with leading indicators
</answer>"""),
            ],
            
            "bollinger": [
                ("How do Bollinger Bands work and how to trade them?",
                 """<think>
Bollinger Bands measure volatility and relative price levels.
Components:
1. Middle band (SMA)
2. Upper band (SMA + 2σ)
3. Lower band (SMA - 2σ)
</think>

<answer>
## Bollinger Bands

### Calculation
```python
def bollinger_bands(prices, period=20, num_std=2):
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    
    upper = middle + (num_std * std)
    lower = middle - (num_std * std)
    
    return upper, middle, lower
```

### Key Metrics

**Bandwidth (Volatility)**
```python
def bandwidth(upper, lower, middle):
    return (upper - lower) / middle
```

**%B (Position within bands)**
```python
def percent_b(price, upper, lower):
    return (price - lower) / (upper - lower)
```

### Trading Strategies

**1. Mean Reversion**
```python
def bb_mean_reversion(price, upper, lower, middle):
    buy = price <= lower  # Buy at lower band
    sell = price >= upper  # Sell at upper band
    target = middle  # Exit at middle
    return buy, sell, target
```

**2. Breakout Strategy**
```python
def bb_breakout(price, upper, lower, bandwidth):
    # Low bandwidth = squeeze
    squeeze = bandwidth < bandwidth.rolling(100).quantile(0.1)
    breakout_up = squeeze.shift(1) & (price > upper)
    breakout_down = squeeze.shift(1) & (price < lower)
    return breakout_up, breakout_down
```

**3. Walking the Bands**
- Strong trends "walk" along upper/lower bands
- Not a reversal signal in strong trends

### Patterns
| Pattern | Meaning |
|---------|---------|
| Squeeze | Low volatility, big move coming |
| W-Bottom | Bullish reversal |
| M-Top | Bearish reversal |
| Walking bands | Strong trend |

### Best Practices
- Combine with RSI for confirmation
- Adjust period for timeframe
- Use %B for position sizing
- Don't fade strong trends
</answer>"""),
            ],

            "volume": [
                ("How do I analyze volume in trading?",
                 """<think>
Volume confirms price movements.
Key concepts:
1. Volume-price relationship
2. Volume indicators
3. Volume patterns
</think>

<answer>
## Volume Analysis

### Core Principle
**"Volume precedes price"** - Volume changes often predict price moves.

### Volume-Price Relationships
| Price | Volume | Interpretation |
|-------|--------|----------------|
| ↑ | ↑ | Strong uptrend |
| ↑ | ↓ | Weak rally, potential reversal |
| ↓ | ↑ | Strong downtrend |
| ↓ | ↓ | Weak decline, potential reversal |

### Key Indicators

**1. On-Balance Volume (OBV)**
```python
def obv(close, volume):
    direction = np.sign(close.diff())
    obv = (direction * volume).cumsum()
    return obv
```

**2. Volume Weighted Average Price (VWAP)**
```python
def vwap(high, low, close, volume):
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    return vwap
```

**3. Volume Profile**
```python
def volume_profile(prices, volume, bins=50):
    price_bins = pd.cut(prices, bins=bins)
    profile = volume.groupby(price_bins).sum()
    return profile
```

**4. Money Flow Index (MFI)**
```python
def mfi(high, low, close, volume, period=14):
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    
    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)
    
    positive_mf = positive_flow.rolling(period).sum()
    negative_mf = negative_flow.rolling(period).sum()
    
    mfi = 100 - (100 / (1 + positive_mf / negative_mf))
    return mfi
```

### Volume Patterns
- **Climax volume**: Trend exhaustion
- **Dry-up**: Consolidation before move
- **Breakout volume**: Confirms breakout validity

### VWAP Trading
- Institutional benchmark
- Buy below VWAP, sell above
- Used for execution quality
</answer>"""),
            ],
        }

    # =========================================================================
    # TIER 4: RISK MANAGEMENT
    # =========================================================================
    
    def generate_risk(self, max_examples: int = 400) -> None:
        """Generate risk management documentation."""
        print("⚠️ Generating risk management documentation...")
        
        topics = self._get_risk_topics()
        count = 0
        
        for topic, qa_pairs in topics.items():
            for q, a in qa_pairs:
                if count >= max_examples:
                    break
                example = self.create_example(q, a, "risk", 1.0)
                self.examples.append(example)
                self.stats["risk"] += 1
                count += 1
        
        print(f"  ✓ Generated {count} risk management examples")
    
    def _get_risk_topics(self) -> Dict[str, List[tuple]]:
        """Return risk management Q&A pairs."""
        return {
            "position_sizing": [
                ("How should I size my trading positions?",
                 """<think>
Position sizing determines survival and growth.
Methods:
1. Fixed fractional
2. Kelly criterion
3. Volatility-based
</think>

<answer>
## Position Sizing Methods

### 1. Fixed Fractional (Percent Risk)
```python
def fixed_fractional_size(account, risk_percent, entry, stop_loss):
    risk_amount = account * risk_percent
    stop_distance = abs(entry - stop_loss)
    position_size = risk_amount / stop_distance
    return position_size

# Example
account = 100000
risk_pct = 0.02  # 2% risk
entry = 50.00
stop = 48.00
size = fixed_fractional_size(account, risk_pct, entry, stop)
# size = 1000 shares
```

### 2. Kelly Criterion
```python
def kelly_size(win_rate, avg_win, avg_loss):
    # Kelly formula: f* = (p*b - q) / b
    # where p=win rate, q=loss rate, b=win/loss ratio
    b = abs(avg_win / avg_loss)
    f = (win_rate * b - (1 - win_rate)) / b
    return max(0, f)  # Never negative

# Full Kelly is aggressive, use half or quarter Kelly
def fractional_kelly(win_rate, avg_win, avg_loss, fraction=0.25):
    return kelly_size(win_rate, avg_win, avg_loss) * fraction
```

### 3. Volatility-Based (ATR)
```python
def atr_position_size(account, risk_percent, atr, atr_multiple=2):
    risk_amount = account * risk_percent
    stop_distance = atr * atr_multiple
    position_size = risk_amount / stop_distance
    return position_size
```

### Position Sizing Rules

| Rule | Guideline |
|------|-----------|
| Per trade | 1-2% max risk |
| Correlated positions | 4-6% combined |
| Total portfolio | 10-20% max at risk |
| Single position | Max 10% of account |

### Position Sizing Based on Conviction
| Conviction | Position Size |
|------------|---------------|
| Low | 0.5% risk |
| Medium | 1% risk |
| High | 2% risk |
| Maximum | 3% risk (rare) |

### Common Mistakes
1. Sizing based on "feeling"
2. Increasing size after losses
3. Not accounting for correlation
4. Ignoring transaction costs
</answer>"""),
            ],

            "portfolio_risk": [
                ("How do I manage portfolio-level risk?",
                 """<think>
Portfolio risk management considers:
1. Correlations between positions
2. Factor exposures
3. Concentration limits
4. Tail risk
</think>

<answer>
## Portfolio Risk Management

### Key Metrics

**1. Portfolio VaR**
```python
def portfolio_var(weights, returns, confidence=0.95):
    portfolio_returns = returns @ weights
    var = np.percentile(portfolio_returns, (1-confidence) * 100)
    return var
```

**2. Expected Shortfall (CVaR)**
```python
def expected_shortfall(weights, returns, confidence=0.95):
    portfolio_returns = returns @ weights
    var = np.percentile(portfolio_returns, (1-confidence) * 100)
    es = portfolio_returns[portfolio_returns <= var].mean()
    return es
```

**3. Maximum Drawdown**
```python
def max_drawdown(equity_curve):
    peak = equity_curve.expanding().max()
    drawdown = (equity_curve - peak) / peak
    return drawdown.min()
```

### Risk Limits

| Risk Type | Limit |
|-----------|-------|
| Single position | < 10% of portfolio |
| Sector exposure | < 25% of portfolio |
| Factor exposure | < 2 standard deviations |
| Daily VaR | < 2% of portfolio |
| Max drawdown | < 20% |

### Correlation Management
```python
def portfolio_correlation_risk(returns):
    corr_matrix = returns.corr()
    # Average correlation (excluding diagonal)
    mask = np.triu(np.ones_like(corr_matrix, dtype=bool), k=1)
    avg_corr = corr_matrix.where(mask).mean().mean()
    return avg_corr
```

### Factor Exposure
Monitor exposure to:
- Market (beta)
- Size
- Value
- Momentum
- Volatility
- Sector

### Stress Testing
```python
def stress_test(portfolio, scenarios):
    results = {}
    for name, scenario in scenarios.items():
        impact = portfolio @ scenario
        results[name] = impact
    return results

scenarios = {
    '2008 crisis': {...},  # Historical returns
    'flash crash': {...},
    'covid crash': {...},
}
```

### Hedging Strategies
1. Index puts for tail risk
2. VIX calls for volatility
3. Sector ETF shorts
4. Currency hedges
</answer>"""),
            ],

            "stop_losses": [
                ("What are the best stop loss strategies?",
                 """<think>
Stop losses protect capital.
Types:
1. Fixed percentage
2. ATR-based
3. Technical levels
4. Time-based
</think>

<answer>
## Stop Loss Strategies

### 1. Fixed Percentage Stop
```python
def percentage_stop(entry_price, stop_percent):
    stop_price = entry_price * (1 - stop_percent)
    return stop_price

# Example: 2% stop
entry = 100
stop = percentage_stop(entry, 0.02)  # Stop at 98
```

### 2. ATR-Based Stop
```python
def atr_stop(entry_price, atr, multiplier=2):
    stop_price = entry_price - (atr * multiplier)
    return stop_price

# Adapts to volatility
```

### 3. Technical Level Stop
```python
def technical_stop(entry, support_level, buffer_percent=0.005):
    stop_price = support_level * (1 - buffer_percent)
    return stop_price

# Place stop below key support
```

### 4. Trailing Stop
```python
class TrailingStop:
    def __init__(self, entry, trail_percent):
        self.entry = entry
        self.trail_percent = trail_percent
        self.highest = entry
    
    def update(self, current_price):
        self.highest = max(self.highest, current_price)
        stop = self.highest * (1 - self.trail_percent)
        return stop
```

### 5. Chandelier Exit
```python
def chandelier_exit(high, atr, multiplier=3, lookback=22):
    highest_high = high.rolling(lookback).max()
    stop = highest_high - (atr * multiplier)
    return stop
```

### Stop Placement Guidelines

| Market Condition | Stop Type | Distance |
|-----------------|-----------|----------|
| Trending | Trailing | 2-3 ATR |
| Ranging | Fixed | 1-2 ATR |
| Volatile | Wide | 3-4 ATR |
| Low vol | Tight | 1 ATR |

### Common Mistakes
1. Stop too tight (stopped out by noise)
2. Stop too wide (excessive loss)
3. Moving stops away from price
4. No stop at all

### Mental vs Hard Stops
- **Hard stops**: Automatic execution
- **Mental stops**: Manual, requires discipline
- **Recommendation**: Use hard stops
</answer>"""),
            ],
        }

    # =========================================================================
    # TIER 5: EXECUTION ALGORITHMS
    # =========================================================================
    
    def generate_execution(self, max_examples: int = 300) -> None:
        """Generate execution algorithm documentation."""
        print("⚡ Generating execution documentation...")
        
        topics = self._get_execution_topics()
        count = 0
        
        for topic, qa_pairs in topics.items():
            for q, a in qa_pairs:
                if count >= max_examples:
                    break
                example = self.create_example(q, a, "execution", 1.0)
                self.examples.append(example)
                self.stats["execution"] += 1
                count += 1
        
        print(f"  ✓ Generated {count} execution examples")
    
    def _get_execution_topics(self) -> Dict[str, List[tuple]]:
        """Return execution algorithm Q&A pairs."""
        return {
            "twap": [
                ("How do I implement a TWAP execution algorithm?",
                 """<think>
TWAP (Time-Weighted Average Price) spreads orders evenly over time.
Key aspects:
1. Time slicing
2. Order sizing
3. Execution logic
</think>

<answer>
## TWAP (Time-Weighted Average Price)

### Definition
TWAP executes an order by splitting it into equal parts over a specified time period.

### Implementation
```python
import time
from datetime import datetime, timedelta

class TWAPExecutor:
    def __init__(self, symbol, total_qty, duration_minutes, api):
        self.symbol = symbol
        self.total_qty = total_qty
        self.duration = duration_minutes
        self.api = api
        self.executed_qty = 0
        self.orders = []
    
    def calculate_slices(self, num_slices):
        qty_per_slice = self.total_qty / num_slices
        interval = self.duration / num_slices
        return qty_per_slice, interval
    
    def execute(self, num_slices=10):
        qty_per_slice, interval_minutes = self.calculate_slices(num_slices)
        
        for i in range(num_slices):
            # Check remaining quantity
            remaining = self.total_qty - self.executed_qty
            if remaining <= 0:
                break
            
            # Execute slice
            order_qty = min(qty_per_slice, remaining)
            order = self.api.market_order(self.symbol, order_qty)
            self.orders.append(order)
            self.executed_qty += order_qty
            
            # Wait for next slice
            if i < num_slices - 1:
                time.sleep(interval_minutes * 60)
        
        return self.get_summary()
    
    def get_summary(self):
        avg_price = sum(o['price'] * o['qty'] for o in self.orders) / self.executed_qty
        return {
            'executed_qty': self.executed_qty,
            'avg_price': avg_price,
            'num_orders': len(self.orders)
        }
```

### Enhancements

**1. Randomization**
```python
def randomized_twap(base_qty, variance=0.2):
    random_factor = 1 + random.uniform(-variance, variance)
    return base_qty * random_factor
```

**2. Volume Participation**
```python
def volume_adjusted_slice(target_qty, current_volume, max_participation=0.1):
    return min(target_qty, current_volume * max_participation)
```

### When to Use TWAP
- Minimize market impact
- No strong view on intraday direction
- Illiquid securities
- Large orders relative to volume

### TWAP vs VWAP
| Aspect | TWAP | VWAP |
|--------|------|------|
| Time | Equal slices | Volume-weighted |
| Best for | Stable volume | Variable volume |
| Benchmark | Time-based | Volume-based |
</answer>"""),
            ],

            "vwap": [
                ("How do I implement a VWAP execution algorithm?",
                 """<think>
VWAP (Volume-Weighted Average Price) matches historical volume patterns.
Components:
1. Volume prediction
2. Order scheduling
3. Real-time adjustment
</think>

<answer>
## VWAP (Volume-Weighted Average Price)

### Definition
VWAP executes orders in proportion to historical volume patterns.

### Calculation
```python
def calculate_vwap(high, low, close, volume):
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    return vwap
```

### Implementation
```python
class VWAPExecutor:
    def __init__(self, symbol, total_qty, api):
        self.symbol = symbol
        self.total_qty = total_qty
        self.api = api
        self.executed_qty = 0
        
    def get_volume_profile(self, lookback_days=20):
        # Get historical intraday volume patterns
        historical = self.api.get_intraday_volume(
            self.symbol, lookback_days
        )
        # Calculate average volume by time bucket
        volume_profile = historical.groupby('time_bucket').mean()
        # Normalize to percentages
        volume_profile = volume_profile / volume_profile.sum()
        return volume_profile
    
    def schedule_orders(self, volume_profile):
        schedule = []
        for time_bucket, pct in volume_profile.items():
            qty = self.total_qty * pct
            schedule.append({
                'time': time_bucket,
                'qty': qty
            })
        return schedule
    
    def execute_adaptive(self, schedule):
        for slot in schedule:
            target_time = slot['time']
            target_qty = slot['qty']
            
            # Wait until target time
            self.wait_until(target_time)
            
            # Adjust based on actual vs expected volume
            actual_volume = self.api.get_current_volume(self.symbol)
            expected_volume = slot.get('expected_volume')
            
            if actual_volume > expected_volume * 1.2:
                # Volume higher than expected, execute more
                adjusted_qty = target_qty * 1.1
            elif actual_volume < expected_volume * 0.8:
                # Volume lower, execute less now
                adjusted_qty = target_qty * 0.9
            else:
                adjusted_qty = target_qty
            
            # Execute
            self.api.market_order(self.symbol, adjusted_qty)
            self.executed_qty += adjusted_qty
```

### VWAP Slippage
```python
def vwap_slippage(execution_price, vwap):
    slippage_bps = (execution_price - vwap) / vwap * 10000
    return slippage_bps
```

### Best Practices
1. Use at least 20 days of history
2. Adjust for unusual volume days
3. Don't exceed participation rate limits
4. Monitor real-time vs expected volume
</answer>"""),
            ],

            "smart_order_routing": [
                ("What is smart order routing and how does it work?",
                 """<think>
Smart Order Routing (SOR) optimizes execution across venues.
Key aspects:
1. Venue selection
2. Order splitting
3. Latency considerations
</think>

<answer>
## Smart Order Routing (SOR)

### Definition
SOR automatically routes orders to the best available venue based on price, liquidity, and cost.

### Implementation
```python
class SmartOrderRouter:
    def __init__(self, venues):
        self.venues = venues  # List of connected exchanges/venues
    
    def get_best_quotes(self, symbol):
        quotes = {}
        for venue in self.venues:
            quote = venue.get_quote(symbol)
            quotes[venue.name] = {
                'bid': quote.bid,
                'ask': quote.ask,
                'bid_size': quote.bid_size,
                'ask_size': quote.ask_size
            }
        return quotes
    
    def route_order(self, symbol, side, qty):
        quotes = self.get_best_quotes(symbol)
        
        # Sort venues by price (best first)
        if side == 'BUY':
            sorted_venues = sorted(quotes.items(), 
                                   key=lambda x: x[1]['ask'])
        else:
            sorted_venues = sorted(quotes.items(), 
                                   key=lambda x: -x[1]['bid'])
        
        # Split order across venues
        orders = []
        remaining = qty
        
        for venue_name, quote in sorted_venues:
            if remaining <= 0:
                break
            
            available = quote['ask_size'] if side == 'BUY' else quote['bid_size']
            fill_qty = min(remaining, available)
            
            orders.append({
                'venue': venue_name,
                'qty': fill_qty,
                'price': quote['ask'] if side == 'BUY' else quote['bid']
            })
            remaining -= fill_qty
        
        return orders
```

### Routing Strategies

**1. Best Price**
- Route to venue with best price
- Simple but may miss liquidity

**2. Cost-Based**
```python
def total_cost(price, qty, maker_fee, taker_fee, spread_cost):
    execution_cost = price * qty
    fee_cost = execution_cost * taker_fee
    market_impact = spread_cost * qty
    return execution_cost + fee_cost + market_impact
```

**3. Liquidity-Seeking**
- Prioritize venues with more liquidity
- Reduces partial fills

### Venue Considerations
| Factor | Importance |
|--------|------------|
| Price | High |
| Liquidity | High |
| Fees | Medium |
| Latency | High (for HFT) |
| Rebates | Medium |

### Regulatory Requirements
- Best execution obligation
- Order routing disclosure
- Execution quality reports
</answer>"""),
            ],
        }

    # =========================================================================
    # TIER 6: BACKTESTING
    # =========================================================================
    
    def generate_backtesting(self, max_examples: int = 300) -> None:
        """Generate backtesting documentation."""
        print("🔬 Generating backtesting documentation...")
        
        topics = self._get_backtesting_topics()
        count = 0
        
        for topic, qa_pairs in topics.items():
            for q, a in qa_pairs:
                if count >= max_examples:
                    break
                example = self.create_example(q, a, "backtesting", 1.0)
                self.examples.append(example)
                self.stats["backtesting"] += 1
                count += 1
        
        print(f"  ✓ Generated {count} backtesting examples")
    
    def _get_backtesting_topics(self) -> Dict[str, List[tuple]]:
        """Return backtesting Q&A pairs."""
        return {
            "framework": [
                ("How do I build a backtesting framework?",
                 """<think>
A backtesting framework simulates strategy performance on historical data.
Components:
1. Data management
2. Strategy engine
3. Execution simulation
4. Performance analysis
</think>

<answer>
## Building a Backtesting Framework

### Core Architecture
```python
class Backtester:
    def __init__(self, data, strategy, initial_capital=100000):
        self.data = data
        self.strategy = strategy
        self.capital = initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
    
    def run(self):
        for timestamp, bar in self.data.iterrows():
            # Generate signals
            signals = self.strategy.generate_signals(bar, self.positions)
            
            # Execute signals
            for signal in signals:
                self.execute_signal(signal, bar)
            
            # Update portfolio value
            portfolio_value = self.calculate_portfolio_value(bar)
            self.equity_curve.append({
                'timestamp': timestamp,
                'value': portfolio_value
            })
        
        return self.analyze_results()
    
    def execute_signal(self, signal, bar):
        if signal['action'] == 'BUY':
            cost = signal['quantity'] * bar['close'] * (1 + self.slippage)
            if cost <= self.capital:
                self.positions[signal['symbol']] = {
                    'quantity': signal['quantity'],
                    'entry_price': bar['close']
                }
                self.capital -= cost
                self.trades.append({
                    'type': 'BUY',
                    'price': bar['close'],
                    'quantity': signal['quantity']
                })
        
        elif signal['action'] == 'SELL':
            if signal['symbol'] in self.positions:
                position = self.positions[signal['symbol']]
                proceeds = position['quantity'] * bar['close'] * (1 - self.slippage)
                self.capital += proceeds
                del self.positions[signal['symbol']]
                self.trades.append({
                    'type': 'SELL',
                    'price': bar['close'],
                    'quantity': position['quantity']
                })
```

### Strategy Interface
```python
class Strategy:
    def __init__(self, params):
        self.params = params
    
    def generate_signals(self, bar, positions):
        raise NotImplementedError
```

### Performance Metrics
```python
def analyze_results(equity_curve, trades):
    returns = pd.Series(equity_curve).pct_change()
    
    metrics = {
        'total_return': (equity_curve[-1] - equity_curve[0]) / equity_curve[0],
        'sharpe_ratio': returns.mean() / returns.std() * np.sqrt(252),
        'max_drawdown': calculate_max_drawdown(equity_curve),
        'win_rate': len([t for t in trades if t['pnl'] > 0]) / len(trades),
        'profit_factor': sum(t['pnl'] for t in trades if t['pnl'] > 0) / 
                        abs(sum(t['pnl'] for t in trades if t['pnl'] < 0))
    }
    return metrics
```

### Critical Features
1. **Transaction costs**: Include realistic fees
2. **Slippage**: Model market impact
3. **Data alignment**: Avoid look-ahead bias
4. **Survivorship bias**: Use point-in-time data
</answer>"""),
            ],

            "biases": [
                ("What are common backtesting biases and how to avoid them?",
                 """<think>
Backtesting biases lead to overly optimistic results.
Major biases:
1. Look-ahead bias
2. Survivorship bias
3. Overfitting
4. Data snooping
</think>

<answer>
## Backtesting Biases

### 1. Look-Ahead Bias
**Problem**: Using future information in past decisions.

```python
# WRONG - Uses future data
def wrong_signal(prices):
    future_return = prices.shift(-5) / prices - 1
    return future_return > 0.05

# CORRECT - Only uses available data
def correct_signal(prices):
    past_return = prices / prices.shift(5) - 1
    return past_return > 0.05
```

### 2. Survivorship Bias
**Problem**: Only testing on stocks that still exist.

**Solution**:
- Use point-in-time databases
- Include delisted stocks
- Account for mergers/acquisitions

```python
# Use survivorship-bias-free data
data = get_point_in_time_data(date)  # As it was known on that date
```

### 3. Overfitting
**Problem**: Strategy fits noise, not signal.

**Detection**:
```python
def check_overfitting(in_sample_sharpe, out_sample_sharpe):
    degradation = (in_sample_sharpe - out_sample_sharpe) / in_sample_sharpe
    if degradation > 0.5:
        print("Warning: Likely overfitting")
```

**Prevention**:
- Limit parameters
- Out-of-sample testing
- Cross-validation

### 4. Data Snooping
**Problem**: Testing many strategies, reporting best.

**Solution**: Bonferroni correction
```python
def adjusted_pvalue(p_value, num_tests):
    return min(1, p_value * num_tests)
```

### 5. Transaction Cost Underestimation
**Realistic costs**:
```python
def realistic_costs(price, quantity, is_maker=False):
    spread_cost = price * 0.0005  # Half spread
    commission = price * quantity * 0.0001
    slippage = price * 0.0002
    
    if not is_maker:
        slippage *= 2  # Taker gets worse fills
    
    return spread_cost + commission + slippage
```

### Validation Checklist
- [ ] No future data in signals
- [ ] Point-in-time universe
- [ ] Out-of-sample testing
- [ ] Realistic transaction costs
- [ ] Multiple time periods
- [ ] Parameter sensitivity analysis
</answer>"""),
            ],
        }

    # =========================================================================
    # TIER 7: CODE IMPLEMENTATIONS
    # =========================================================================
    
    def generate_code(self, max_examples: int = 600) -> None:
        """Generate code implementation examples."""
        print("💻 Generating code examples...")
        
        topics = self._get_code_topics()
        count = 0
        
        for topic, qa_pairs in topics.items():
            for q, a in qa_pairs:
                if count >= max_examples:
                    break
                example = self.create_example(q, a, "code", 1.0)
                self.examples.append(example)
                self.stats["code"] += 1
                count += 1
        
        print(f"  ✓ Generated {count} code examples")
    
    def _get_code_topics(self) -> Dict[str, List[tuple]]:
        """Return code implementation Q&A pairs."""
        return {
            "data_structures": [
                ("How do I implement an order book data structure?",
                 """<think>
An order book tracks bids and asks.
Requirements:
1. Fast insertion/deletion
2. Price-time priority
3. Level aggregation
</think>

<answer>
## Order Book Implementation

```python
from sortedcontainers import SortedDict
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional
import time

@dataclass
class Order:
    order_id: str
    side: str  # 'bid' or 'ask'
    price: float
    quantity: float
    timestamp: float
    
class OrderBook:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids = SortedDict()  # Price -> {order_id: Order}
        self.asks = SortedDict()  # Price -> {order_id: Order}
        self.orders = {}  # order_id -> Order
    
    def add_order(self, order: Order):
        self.orders[order.order_id] = order
        book = self.bids if order.side == 'bid' else self.asks
        
        if order.price not in book:
            book[order.price] = {}
        book[order.price][order.order_id] = order
    
    def cancel_order(self, order_id: str):
        if order_id not in self.orders:
            return
        
        order = self.orders[order_id]
        book = self.bids if order.side == 'bid' else self.asks
        
        del book[order.price][order_id]
        if not book[order.price]:
            del book[order.price]
        del self.orders[order_id]
    
    def get_best_bid(self) -> Optional[float]:
        if self.bids:
            return self.bids.peekitem(-1)[0]  # Highest bid
        return None
    
    def get_best_ask(self) -> Optional[float]:
        if self.asks:
            return self.asks.peekitem(0)[0]  # Lowest ask
        return None
    
    def get_spread(self) -> Optional[float]:
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask - best_bid
        return None
    
    def get_depth(self, levels: int = 5):
        bid_depth = []
        ask_depth = []
        
        for i, (price, orders) in enumerate(reversed(self.bids.items())):
            if i >= levels:
                break
            total_qty = sum(o.quantity for o in orders.values())
            bid_depth.append({'price': price, 'quantity': total_qty})
        
        for i, (price, orders) in enumerate(self.asks.items()):
            if i >= levels:
                break
            total_qty = sum(o.quantity for o in orders.values())
            ask_depth.append({'price': price, 'quantity': total_qty})
        
        return {'bids': bid_depth, 'asks': ask_depth}
```

### Usage
```python
book = OrderBook('BTC/USD')
book.add_order(Order('1', 'bid', 50000, 1.0, time.time()))
book.add_order(Order('2', 'ask', 50100, 0.5, time.time()))

print(f"Spread: {book.get_spread()}")  # 100
print(f"Best bid: {book.get_best_bid()}")  # 50000
```
</answer>"""),
            ],

            "indicators": [
                ("Implement all major technical indicators in Python",
                 """<think>
Technical indicators are mathematical calculations on price/volume.
Categories:
1. Trend indicators
2. Momentum indicators
3. Volatility indicators
4. Volume indicators
</think>

<answer>
## Technical Indicators Library

```python
import numpy as np
import pandas as pd

class TechnicalIndicators:
    # ==================== TREND ====================
    
    @staticmethod
    def sma(prices, period):
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def ema(prices, period):
        return prices.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def macd(prices, fast=12, slow=26, signal=9):
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    # ==================== MOMENTUM ====================
    
    @staticmethod
    def rsi(prices, period=14):
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def stochastic(high, low, close, k_period=14, d_period=3):
        lowest_low = low.rolling(k_period).min()
        highest_high = high.rolling(k_period).max()
        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(d_period).mean()
        return k, d
    
    @staticmethod
    def cci(high, low, close, period=20):
        tp = (high + low + close) / 3
        sma_tp = tp.rolling(period).mean()
        mad = tp.rolling(period).apply(lambda x: np.abs(x - x.mean()).mean())
        return (tp - sma_tp) / (0.015 * mad)
    
    # ==================== VOLATILITY ====================
    
    @staticmethod
    def atr(high, low, close, period=14):
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()
    
    @staticmethod
    def bollinger_bands(prices, period=20, num_std=2):
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + (num_std * std)
        lower = sma - (num_std * std)
        return upper, sma, lower
    
    # ==================== VOLUME ====================
    
    @staticmethod
    def obv(close, volume):
        direction = np.sign(close.diff())
        return (direction * volume).cumsum()
    
    @staticmethod
    def vwap(high, low, close, volume):
        tp = (high + low + close) / 3
        return (tp * volume).cumsum() / volume.cumsum()
    
    @staticmethod
    def mfi(high, low, close, volume, period=14):
        tp = (high + low + close) / 3
        mf = tp * volume
        pos_mf = mf.where(tp > tp.shift(), 0).rolling(period).sum()
        neg_mf = mf.where(tp < tp.shift(), 0).rolling(period).sum()
        return 100 - (100 / (1 + pos_mf / neg_mf))
```

### Usage
```python
ti = TechnicalIndicators()
df['rsi'] = ti.rsi(df['close'])
df['macd'], df['signal'], df['hist'] = ti.macd(df['close'])
df['upper'], df['middle'], df['lower'] = ti.bollinger_bands(df['close'])
```
</answer>"""),
            ],

            "exchange_api": [
                ("How do I connect to a cryptocurrency exchange API?",
                 """<think>
Exchange APIs allow automated trading.
Common features:
1. REST API for orders
2. WebSocket for market data
3. Authentication
4. Rate limiting
</think>

<answer>
## Exchange API Integration

### REST API Client
```python
import hmac
import hashlib
import time
import requests
from urllib.parse import urlencode

class ExchangeAPI:
    def __init__(self, api_key, api_secret, base_url):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url
        self.session = requests.Session()
    
    def _sign(self, params):
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _request(self, method, endpoint, params=None, signed=False):
        url = f"{self.base_url}{endpoint}"
        
        if params is None:
            params = {}
        
        if signed:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._sign(params)
        
        headers = {'X-API-KEY': self.api_key}
        
        if method == 'GET':
            response = self.session.get(url, params=params, headers=headers)
        elif method == 'POST':
            response = self.session.post(url, data=params, headers=headers)
        elif method == 'DELETE':
            response = self.session.delete(url, params=params, headers=headers)
        
        return response.json()
    
    # Public endpoints
    def get_ticker(self, symbol):
        return self._request('GET', '/api/v1/ticker', {'symbol': symbol})
    
    def get_orderbook(self, symbol, limit=100):
        return self._request('GET', '/api/v1/depth', 
                           {'symbol': symbol, 'limit': limit})
    
    # Private endpoints (signed)
    def get_balance(self):
        return self._request('GET', '/api/v1/account', signed=True)
    
    def place_order(self, symbol, side, order_type, quantity, price=None):
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity
        }
        if price:
            params['price'] = price
        return self._request('POST', '/api/v1/order', params, signed=True)
    
    def cancel_order(self, symbol, order_id):
        return self._request('DELETE', '/api/v1/order',
                           {'symbol': symbol, 'orderId': order_id}, signed=True)
```

### WebSocket Client
```python
import websocket
import json
import threading

class ExchangeWebSocket:
    def __init__(self, url, on_message):
        self.url = url
        self.on_message = on_message
        self.ws = None
    
    def connect(self):
        self.ws = websocket.WebSocketApp(
            self.url,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        thread = threading.Thread(target=self.ws.run_forever)
        thread.daemon = True
        thread.start()
    
    def subscribe(self, channel, symbol):
        msg = {
            'method': 'SUBSCRIBE',
            'params': [f'{symbol.lower()}@{channel}'],
            'id': 1
        }
        self.ws.send(json.dumps(msg))
    
    def _on_message(self, ws, message):
        data = json.loads(message)
        self.on_message(data)
    
    def _on_error(self, ws, error):
        print(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status, close_msg):
        print("WebSocket closed")
```

### Usage
```python
# REST
api = ExchangeAPI(API_KEY, API_SECRET, 'https://api.exchange.com')
ticker = api.get_ticker('BTC/USDT')
order = api.place_order('BTC/USDT', 'BUY', 'LIMIT', 0.1, 50000)

# WebSocket
def handle_trade(data):
    print(f"Trade: {data}")

ws = ExchangeWebSocket('wss://stream.exchange.com/ws', handle_trade)
ws.connect()
ws.subscribe('trade', 'BTCUSDT')
```
</answer>"""),
            ],
        }

    # =========================================================================
    # MAIN GENERATION & OUTPUT
    # =========================================================================
    
    def generate_all(self):
        """Generate all documentation examples."""
        print("\n" + "="*60)
        print("📚 Trading Documentation Generator")
        print("="*60 + "\n")
        
        self.generate_institutional(max_examples=300)
        self.generate_strategies(max_examples=500)
        self.generate_technical(max_examples=600)
        self.generate_risk(max_examples=400)
        self.generate_execution(max_examples=300)
        self.generate_backtesting(max_examples=300)
        self.generate_code(max_examples=600)
        
        print("\n" + "="*60)
        print(f"📊 Generation Complete: {len(self.examples)} total examples")
        print("="*60)
        
        for category, count in self.stats.items():
            if count > 0:
                print(f"  {category}: {count}")
    
    def save(self, output_dir: Path):
        """Save examples to files."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Shuffle
        random.shuffle(self.examples)
        
        # Save documentation examples
        docs_file = output_dir / "trading_docs.jsonl"
        with open(docs_file, 'w', encoding='utf-8') as f:
            for example in self.examples:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")
        
        print(f"\n✅ Saved {len(self.examples)} examples to {docs_file}")
        
        # Merge with existing expert training data
        existing_train = output_dir / "train_expert.jsonl"
        existing_val = output_dir / "val_expert.jsonl"
        
        all_examples = list(self.examples)
        
        if existing_train.exists():
            with open(existing_train, 'r') as f:
                for line in f:
                    if line.strip():
                        all_examples.append(json.loads(line))
        
        if existing_val.exists():
            with open(existing_val, 'r') as f:
                for line in f:
                    if line.strip():
                        all_examples.append(json.loads(line))
        
        # Shuffle combined
        random.shuffle(all_examples)
        
        # Split 90/10
        split_idx = int(len(all_examples) * 0.9)
        train = all_examples[:split_idx]
        val = all_examples[split_idx:]
        
        # Save combined
        combined_train = output_dir / "train_combined.jsonl"
        combined_val = output_dir / "val_combined.jsonl"
        
        with open(combined_train, 'w', encoding='utf-8') as f:
            for example in train:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")
        
        with open(combined_val, 'w', encoding='utf-8') as f:
            for example in val:
                f.write(json.dumps(example, ensure_ascii=False) + "\n")
        
        print(f"✅ Saved {len(train)} training + {len(val)} validation to combined files")
        print(f"   Total combined: {len(all_examples)} examples")


def main():
    parser = argparse.ArgumentParser(description="Generate trading documentation for PersRM")
    parser.add_argument("--output-dir", type=str, 
                       default=str(OUTPUT_DIR),
                       help="Output directory")
    args = parser.parse_args()
    
    generator = TradingDocsGenerator()
    generator.generate_all()
    generator.save(Path(args.output_dir))


if __name__ == "__main__":
    main()

