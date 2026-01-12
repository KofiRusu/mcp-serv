"""
trading_brain.py - PersRM Trading Decision Engine

This module provides the AI-powered trading decision logic:
1. Build market context from price data
2. Generate prompts for PersRM/Ollama
3. Parse trading signals from model responses
4. Calculate position sizing and risk parameters

The trading brain is designed to work with both paper and live trading modes.
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import httpx

logger = logging.getLogger(__name__)


@dataclass
class TradingDecision:
    """A trading decision from the model."""
    signal: str  # LONG, SHORT, CLOSE, HOLD
    symbol: str
    reasoning: str
    confidence: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    risk_reward: Optional[float] = None


class TradingBrain:
    """
    AI-powered trading decision engine using PersRM/Ollama.
    
    This class handles:
    - Building market context prompts
    - Querying the model for trading decisions
    - Parsing and validating responses
    - Calculating risk parameters
    """
    
    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "mistral:7b",  # Default model, can use fine-tuned PersRM
        timeout: int = 60,
    ):
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None
        
        # Technical indicator calculations (simplified)
        self.price_history: Dict[str, List[float]] = {}
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client
    
    async def close(self):
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI indicator."""
        if len(prices) < period + 1:
            return 50.0  # Neutral
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i - 1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return round(rsi, 2)
    
    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate EMA."""
        if len(prices) < period:
            return prices[-1] if prices else 0
        
        multiplier = 2 / (period + 1)
        ema = prices[0]
        
        for price in prices[1:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        
        return round(ema, 2)
    
    def _calculate_macd(self, prices: List[float]) -> Tuple[float, float, str]:
        """Calculate MACD indicator."""
        if len(prices) < 26:
            return 0, 0, "neutral"
        
        ema_12 = self._calculate_ema(prices, 12)
        ema_26 = self._calculate_ema(prices, 26)
        macd_line = ema_12 - ema_26
        
        # Signal line (9-period EMA of MACD)
        # Simplified: just use recent MACD value
        signal_line = macd_line * 0.9
        
        histogram = macd_line - signal_line
        trend = "bullish" if histogram > 0 else "bearish" if histogram < 0 else "neutral"
        
        return round(macd_line, 2), round(histogram, 2), trend
    
    def _update_price_history(self, symbol: str, price: float):
        """Update price history for a symbol."""
        if symbol not in self.price_history:
            self.price_history[symbol] = []
        
        self.price_history[symbol].append(price)
        
        # Keep last 100 prices
        if len(self.price_history[symbol]) > 100:
            self.price_history[symbol] = self.price_history[symbol][-100:]
    
    def build_market_context(
        self,
        symbol: str,
        price: float,
        change_24h: float,
        existing_position: Optional[Dict[str, Any]] = None,
        balance: float = 100000,
        mode: str = "paper",
    ) -> str:
        """
        Build a market context prompt for the model.
        
        Args:
            symbol: Trading pair (e.g., BTCUSDT)
            price: Current price
            change_24h: 24h price change percentage
            existing_position: Existing position if any
            balance: Available balance
            mode: Trading mode (paper/live)
            
        Returns:
            Formatted prompt string
        """
        # Update price history
        self._update_price_history(symbol, price)
        
        # Calculate indicators
        prices = self.price_history.get(symbol, [price])
        rsi = self._calculate_rsi(prices)
        macd_line, macd_histogram, macd_trend = self._calculate_macd(prices)
        
        # Build position info
        position_info = "None"
        if existing_position:
            pos_pnl = existing_position.get("pnl", 0)
            pos_pnl_pct = existing_position.get("pnl_percent", 0)
            position_info = (
                f"{existing_position['side'].upper()} {existing_position['size']:.6f} "
                f"@ ${existing_position['entry_price']:,.2f} "
                f"(PnL: ${pos_pnl:,.2f} / {pos_pnl_pct:.2f}%)"
            )
        
        # Calculate support/resistance (simplified)
        if len(prices) >= 20:
            recent_high = max(prices[-20:])
            recent_low = min(prices[-20:])
        else:
            recent_high = price * 1.05
            recent_low = price * 0.95
        
        context = f"""You are an expert crypto trader AI. Analyze the following market data and provide a trading decision.

MARKET DATA:
- Symbol: {symbol}
- Current Price: ${price:,.2f}
- 24h Change: {change_24h:+.2f}%
- Recent High: ${recent_high:,.2f}
- Recent Low: ${recent_low:,.2f}

TECHNICAL INDICATORS:
- RSI(14): {rsi} {"(OVERSOLD)" if rsi < 30 else "(OVERBOUGHT)" if rsi > 70 else "(NEUTRAL)"}
- MACD: {macd_line:+.2f} ({macd_trend.upper()})
- MACD Histogram: {macd_histogram:+.2f}
- Trend: {"BULLISH" if change_24h > 1 else "BEARISH" if change_24h < -1 else "SIDEWAYS"}

PORTFOLIO:
- Mode: {mode.upper()} TRADING
- Available Balance: ${balance:,.2f}
- Current Position: {position_info}

RULES:
1. Risk max 1-2% per trade
2. Always use stop-loss (2-3% from entry)
3. Target 2:1 or better risk/reward
4. Don't overtrade - HOLD if uncertain
5. Close positions that hit stop-loss or take-profit

RESPOND WITH EXACTLY ONE OF:
- LONG {symbol.replace('USDT', '')} - if bullish setup (RSI oversold, MACD bullish, or strong support)
- SHORT {symbol.replace('USDT', '')} - if bearish setup (RSI overbought, MACD bearish, or resistance rejection)
- CLOSE {symbol.replace('USDT', '')} - if existing position should be closed
- HOLD - if no clear setup or already positioned correctly

Include a brief 1-2 sentence reasoning."""
        
        return context
    
    async def get_trading_decision(
        self,
        symbol: str,
        price: float,
        change_24h: float,
        existing_position: Optional[Dict[str, Any]] = None,
        balance: float = 100000,
        mode: str = "paper",
    ) -> Dict[str, Any]:
        """
        Get a trading decision from PersRM/Ollama.
        
        Returns:
            Dictionary with signal, reasoning, stop_loss, take_profit
        """
        # Build the prompt
        prompt = self.build_market_context(
            symbol=symbol,
            price=price,
            change_24h=change_24h,
            existing_position=existing_position,
            balance=balance,
            mode=mode,
        )
        
        try:
            # Query the model
            client = await self._get_client()
            
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower for more consistent decisions
                        "num_predict": 256,
                    },
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                model_response = data.get("response", "HOLD")
                return self._parse_response(symbol, price, model_response)
            else:
                logger.warning(f"Model request failed: {response.status_code}")
                return self._fallback_decision(symbol, price, change_24h, existing_position)
                
        except Exception as e:
            logger.error(f"Error getting trading decision: {e}")
            return self._fallback_decision(symbol, price, change_24h, existing_position)
    
    def _parse_response(
        self,
        symbol: str,
        price: float,
        response: str,
    ) -> Dict[str, Any]:
        """Parse the model response into a trading decision."""
        response_upper = response.upper()
        
        # Extract signal
        signal = "HOLD"
        base_asset = symbol.replace("USDT", "")
        
        if f"LONG {base_asset}" in response_upper or f"LONG" in response_upper.split()[0:3]:
            signal = "LONG"
        elif f"SHORT {base_asset}" in response_upper or f"SHORT" in response_upper.split()[0:3]:
            signal = "SHORT"
        elif f"CLOSE {base_asset}" in response_upper or f"CLOSE" in response_upper.split()[0:3]:
            signal = "CLOSE"
        
        # Extract reasoning (everything after the signal)
        reasoning = response.strip()
        
        # Calculate stop-loss and take-profit based on signal
        stop_loss = None
        take_profit = None
        
        if signal == "LONG":
            stop_loss = round(price * 0.98, 2)  # 2% below
            take_profit = round(price * 1.06, 2)  # 6% above (3:1 R:R)
        elif signal == "SHORT":
            stop_loss = round(price * 1.02, 2)  # 2% above
            take_profit = round(price * 0.94, 2)  # 6% below
        
        return {
            "signal": signal,
            "reasoning": reasoning,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "price": price,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _fallback_decision(
        self,
        symbol: str,
        price: float,
        change_24h: float,
        existing_position: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Generate a fallback decision when model is unavailable.
        Uses simple technical rules.
        """
        prices = self.price_history.get(symbol, [price])
        rsi = self._calculate_rsi(prices)
        
        signal = "HOLD"
        reasoning = "Model unavailable, using fallback rules. "
        
        # Simple rules
        if existing_position:
            # Check if we should close
            pnl_percent = existing_position.get("pnl_percent", 0)
            if pnl_percent > 5 or pnl_percent < -3:
                signal = "CLOSE"
                reasoning += f"Position at {pnl_percent:.2f}% PnL, closing."
        else:
            # Look for entry
            if rsi < 30 and change_24h < -3:
                signal = "LONG"
                reasoning += f"RSI oversold at {rsi}, potential bounce."
            elif rsi > 70 and change_24h > 3:
                signal = "SHORT"
                reasoning += f"RSI overbought at {rsi}, potential pullback."
            else:
                reasoning += f"No clear setup. RSI: {rsi}, Change: {change_24h:+.2f}%"
        
        # Calculate levels
        stop_loss = None
        take_profit = None
        
        if signal == "LONG":
            stop_loss = round(price * 0.98, 2)
            take_profit = round(price * 1.06, 2)
        elif signal == "SHORT":
            stop_loss = round(price * 1.02, 2)
            take_profit = round(price * 0.94, 2)
        
        return {
            "signal": signal,
            "reasoning": reasoning,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "price": price,
            "timestamp": datetime.now().isoformat(),
            "fallback": True,
        }


# =============================================================================
# Utility Functions
# =============================================================================

async def get_quick_decision(
    symbol: str,
    price: float,
    change_24h: float = 0,
) -> Dict[str, Any]:
    """
    Quick utility to get a trading decision.
    
    Args:
        symbol: Trading pair
        price: Current price
        change_24h: 24h change percentage
        
    Returns:
        Trading decision dictionary
    """
    brain = TradingBrain()
    try:
        return await brain.get_trading_decision(
            symbol=symbol,
            price=price,
            change_24h=change_24h,
        )
    finally:
        await brain.close()


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss_price: float,
) -> float:
    """
    Calculate position size based on risk parameters.
    
    Args:
        account_balance: Total account balance
        risk_percent: Risk percentage (e.g., 1.0 for 1%)
        entry_price: Entry price
        stop_loss_price: Stop-loss price
        
    Returns:
        Position size in base asset
    """
    risk_amount = account_balance * (risk_percent / 100)
    price_risk = abs(entry_price - stop_loss_price)
    
    if price_risk == 0:
        return 0
    
    position_size = risk_amount / price_risk
    return round(position_size, 6)


def calculate_risk_reward(
    entry_price: float,
    stop_loss: float,
    take_profit: float,
    side: str,
) -> float:
    """
    Calculate risk/reward ratio.
    
    Returns:
        Risk/reward ratio (e.g., 3.0 means 3:1)
    """
    if side == "long":
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
    else:
        risk = stop_loss - entry_price
        reward = entry_price - take_profit
    
    if risk <= 0:
        return 0
    
    return round(reward / risk, 2)

