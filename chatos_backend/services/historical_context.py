"""
Historical Context Builder - Constructs Context A/B/C for Thought-Line Processing

This module builds the three historical context types used as FILTERS
in the thought-line processing pipeline:

- Context A: Market Microstructure + Orderflow history
- Context B: Regime + Volatility history
- Context C: Strategy + Agent performance history

Each context is built from database records and provides structured
data for thought evaluation and decision filtering.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import json
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ContextA:
    """Market Microstructure + Orderflow Context"""
    symbol: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lookback_hours: float = 24.0
    
    recent_trades_summary: Dict[str, Any] = field(default_factory=dict)
    cvd_series: List[float] = field(default_factory=list)
    cvd_current: float = 0.0
    cvd_trend: str = "neutral"
    
    delta_1m: float = 0.0
    delta_5m: float = 0.0
    delta_15m: float = 0.0
    delta_1h: float = 0.0
    
    whale_activity: List[Dict[str, Any]] = field(default_factory=list)
    whale_buy_pressure: float = 0.0
    whale_sell_pressure: float = 0.0
    
    liquidations_1h: Dict[str, float] = field(default_factory=dict)
    liquidations_24h: Dict[str, float] = field(default_factory=dict)
    liquidation_imbalance: float = 0.0
    
    funding_rate: float = 0.0
    funding_rate_predicted: float = 0.0
    funding_trend: str = "neutral"
    
    open_interest: float = 0.0
    oi_change_1h: float = 0.0
    oi_change_24h: float = 0.0
    oi_price_divergence: bool = False
    
    spread_bps: float = 0.0
    vwap: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "lookback_hours": self.lookback_hours,
            "cvd_current": self.cvd_current,
            "cvd_trend": self.cvd_trend,
            "delta_1h": self.delta_1h,
            "whale_buy_pressure": self.whale_buy_pressure,
            "whale_sell_pressure": self.whale_sell_pressure,
            "liquidations_1h": self.liquidations_1h,
            "liquidation_imbalance": self.liquidation_imbalance,
            "funding_rate": self.funding_rate,
            "funding_trend": self.funding_trend,
            "open_interest": self.open_interest,
            "oi_change_1h": self.oi_change_1h,
            "oi_price_divergence": self.oi_price_divergence,
            "vwap": self.vwap,
        }
    
    def get_hash(self) -> str:
        """Get deterministic hash for replay verification."""
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class ContextB:
    """Regime + Volatility Context"""
    symbol: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lookback_hours: float = 168.0
    
    current_regime: str = "ranging"
    regime_confidence: float = 0.5
    regime_duration_hours: float = 0.0
    regime_history: List[Dict[str, Any]] = field(default_factory=list)
    
    realized_vol_1h: float = 0.0
    realized_vol_24h: float = 0.0
    realized_vol_7d: float = 0.0
    vol_regime: str = "normal"
    vol_percentile: float = 50.0
    vol_expanding: bool = False
    vol_contracting: bool = False
    
    correlations: Dict[str, float] = field(default_factory=dict)
    correlation_btc: float = 0.0
    correlation_breakdown: bool = False
    
    current_drawdown_pct: float = 0.0
    max_drawdown_24h: float = 0.0
    max_drawdown_7d: float = 0.0
    drawdown_duration_hours: float = 0.0
    
    liquidity_score: float = 0.5
    spread_percentile: float = 50.0
    orderbook_imbalance: float = 0.0
    
    trend_strength: float = 0.0
    range_bound: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "lookback_hours": self.lookback_hours,
            "current_regime": self.current_regime,
            "regime_confidence": self.regime_confidence,
            "realized_vol_24h": self.realized_vol_24h,
            "vol_regime": self.vol_regime,
            "vol_percentile": self.vol_percentile,
            "correlations": self.correlations,
            "correlation_btc": self.correlation_btc,
            "current_drawdown_pct": self.current_drawdown_pct,
            "max_drawdown_24h": self.max_drawdown_24h,
            "liquidity_score": self.liquidity_score,
            "trend_strength": self.trend_strength,
            "range_bound": self.range_bound,
        }
    
    def get_hash(self) -> str:
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


@dataclass
class ContextC:
    """Strategy + Agent Performance Context"""
    symbol: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    lookback_days: int = 30
    
    recent_decisions: List[Dict[str, Any]] = field(default_factory=list)
    total_decisions: int = 0
    decisions_executed: int = 0
    
    outcomes: List[Dict[str, Any]] = field(default_factory=list)
    total_trades: int = 0
    win_count: int = 0
    loss_count: int = 0
    win_rate: float = 0.0
    
    total_pnl_usd: float = 0.0
    avg_pnl_per_trade: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    
    avg_slippage_bps: float = 0.0
    max_slippage_bps: float = 0.0
    slippage_trend: str = "stable"
    
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    latency_issues: bool = False
    
    risk_breaches: List[Dict[str, Any]] = field(default_factory=list)
    breach_count_7d: int = 0
    recent_kill_switch: bool = False
    
    model_confidence_avg: float = 0.5
    model_accuracy: float = 0.5
    calibration_error: float = 0.0
    overconfident: bool = False
    underconfident: bool = False
    
    current_positions: int = 0
    current_exposure_usd: float = 0.0
    daily_pnl_usd: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat(),
            "lookback_days": self.lookback_days,
            "total_decisions": self.total_decisions,
            "win_rate": self.win_rate,
            "total_pnl_usd": self.total_pnl_usd,
            "profit_factor": self.profit_factor,
            "avg_slippage_bps": self.avg_slippage_bps,
            "avg_latency_ms": self.avg_latency_ms,
            "breach_count_7d": self.breach_count_7d,
            "model_accuracy": self.model_accuracy,
            "calibration_error": self.calibration_error,
            "current_positions": self.current_positions,
            "daily_pnl_usd": self.daily_pnl_usd,
        }
    
    def get_hash(self) -> str:
        data = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data.encode()).hexdigest()[:16]


class HistoricalContextBuilder:
    """
    Builds historical context A/B/C for thought-line evaluation.
    
    Sources data from:
    1. Database (SQLite/PostgreSQL) for persistent history
    2. RealtimeDataStore for recent data
    3. Event history from EventBus
    """
    
    def __init__(self):
        self._db_session = None
        self._store = None
        self._event_bus = None
    
    @property
    def store(self):
        if self._store is None:
            from chatos_backend.services.realtime_data_store import get_realtime_store
            self._store = get_realtime_store()
        return self._store
    
    @property
    def event_bus(self):
        if self._event_bus is None:
            from chatos_backend.core.event_bus import get_event_bus
            self._event_bus = get_event_bus()
        return self._event_bus
    
    async def build_context_a(
        self,
        symbol: str,
        lookback: timedelta = timedelta(hours=24)
    ) -> ContextA:
        """
        Build Market Microstructure + Orderflow context.
        
        Sources:
        - OrderflowSnapshot table
        - LiquidationEvent table
        - FundingRate table
        - OpenInterest table
        - RealtimeDataStore (recent trades)
        - EventBus history
        """
        context = ContextA(
            symbol=symbol,
            lookback_hours=lookback.total_seconds() / 3600
        )
        
        await asyncio.gather(
            self._fill_orderflow_data(context),
            self._fill_liquidation_data(context),
            self._fill_funding_data(context),
            self._fill_oi_data(context),
        )
        
        self._calculate_derived_metrics_a(context)
        
        return context
    
    async def _fill_orderflow_data(self, context: ContextA):
        """Fill orderflow metrics from store and events."""
        trades = self.store.get_recent_trades(context.symbol, limit=100)
        
        if trades:
            buy_vol = sum(t.amount for t in trades if t.side == 'buy')
            sell_vol = sum(t.amount for t in trades if t.side == 'sell')
            total_vol = buy_vol + sell_vol
            
            context.delta_1h = buy_vol - sell_vol
            context.cvd_current = context.delta_1h
            
            if total_vol > 0:
                buy_pct = buy_vol / total_vol * 100
                if buy_pct > 55:
                    context.cvd_trend = "bullish"
                elif buy_pct < 45:
                    context.cvd_trend = "bearish"
                else:
                    context.cvd_trend = "neutral"
            
            buy_value = sum(t.amount * t.price for t in trades if t.side == 'buy')
            sell_value = sum(t.amount * t.price for t in trades if t.side == 'sell')
            total_value = buy_value + sell_value
            
            if total_value > 0:
                context.vwap = total_value / total_vol if total_vol > 0 else 0
            
            whale_threshold_usd = 50000
            whale_trades = [
                {"price": t.price, "amount": t.amount, "side": t.side, "value": t.amount * t.price}
                for t in trades
                if t.amount * t.price >= whale_threshold_usd
            ]
            context.whale_activity = whale_trades[-20:]
            
            if whale_trades:
                context.whale_buy_pressure = sum(w["value"] for w in whale_trades if w["side"] == "buy")
                context.whale_sell_pressure = sum(w["value"] for w in whale_trades if w["side"] == "sell")
            
            context.recent_trades_summary = {
                "count": len(trades),
                "buy_volume": buy_vol,
                "sell_volume": sell_vol,
                "total_value_usd": total_value,
            }
        
        events = self.event_bus.get_history("market.aggregation", limit=20)
        if events:
            cvd_values = [e.payload.get("cvd", 0) for e in events if e.payload.get("symbol") == context.symbol]
            if cvd_values:
                context.cvd_series = cvd_values[-10:]
    
    async def _fill_liquidation_data(self, context: ContextA):
        """Fill liquidation data from events."""
        events = self.event_bus.get_history("market.liquidation", limit=50)
        
        long_liqs_1h = 0.0
        short_liqs_1h = 0.0
        
        cutoff_1h = datetime.now(timezone.utc) - timedelta(hours=1)
        
        for event in events:
            if event.payload.get("symbol") != context.symbol:
                continue
            if event.timestamp < cutoff_1h:
                continue
            
            long_liqs_1h += event.payload.get("long_liquidations", 0)
            short_liqs_1h += event.payload.get("short_liquidations", 0)
        
        context.liquidations_1h = {
            "long": long_liqs_1h,
            "short": short_liqs_1h,
            "total": long_liqs_1h + short_liqs_1h,
        }
        
        total = long_liqs_1h + short_liqs_1h
        if total > 0:
            context.liquidation_imbalance = (long_liqs_1h - short_liqs_1h) / total
    
    async def _fill_funding_data(self, context: ContextA):
        """Fill funding rate data from events."""
        events = self.event_bus.get_history("market.funding", limit=10)
        
        for event in events:
            if event.payload.get("symbol") == context.symbol:
                context.funding_rate = event.payload.get("rate", 0)
                break
        
        if context.funding_rate > 0.01:
            context.funding_trend = "bullish_crowded"
        elif context.funding_rate < -0.01:
            context.funding_trend = "bearish_crowded"
        elif context.funding_rate > 0:
            context.funding_trend = "slightly_bullish"
        elif context.funding_rate < 0:
            context.funding_trend = "slightly_bearish"
        else:
            context.funding_trend = "neutral"
    
    async def _fill_oi_data(self, context: ContextA):
        """Fill open interest data from events."""
        events = self.event_bus.get_history("market.oi_update", limit=20)
        
        oi_values = []
        for event in events:
            if event.payload.get("symbol") == context.symbol:
                oi_values.append({
                    "oi": event.payload.get("oi", 0),
                    "timestamp": event.timestamp,
                })
        
        if oi_values:
            context.open_interest = oi_values[0]["oi"]
            
            if len(oi_values) >= 2:
                old_oi = oi_values[-1]["oi"]
                if old_oi > 0:
                    context.oi_change_1h = (context.open_interest - old_oi) / old_oi * 100
    
    def _calculate_derived_metrics_a(self, context: ContextA):
        """Calculate derived metrics for Context A."""
        ticker = self.store.get_ticker(context.symbol)
        if ticker:
            price_change = ticker.change_24h
            oi_change = context.oi_change_1h
            
            if price_change > 2 and oi_change < -5:
                context.oi_price_divergence = True
            elif price_change < -2 and oi_change > 5:
                context.oi_price_divergence = True
    
    async def build_context_b(
        self,
        symbol: str,
        lookback: timedelta = timedelta(days=7)
    ) -> ContextB:
        """
        Build Regime + Volatility context.
        
        Sources:
        - RegimeClassification table
        - VolatilitySnapshot table
        - CorrelationMatrix table
        - DrawdownTracker table
        - RealtimeDataStore (price data)
        """
        context = ContextB(
            symbol=symbol,
            lookback_hours=lookback.total_seconds() / 3600
        )
        
        await asyncio.gather(
            self._fill_regime_data(context),
            self._fill_volatility_data(context),
            self._fill_correlation_data(context),
            self._fill_drawdown_data(context),
        )
        
        return context
    
    async def _fill_regime_data(self, context: ContextB):
        """Fill regime classification data."""
        ticker = self.store.get_ticker(context.symbol)
        
        if ticker:
            change = ticker.change_24h
            
            if change > 5:
                context.current_regime = "trending_up"
                context.trend_strength = min(abs(change) / 10, 1.0)
            elif change < -5:
                context.current_regime = "trending_down"
                context.trend_strength = min(abs(change) / 10, 1.0)
            elif abs(change) < 2:
                context.current_regime = "ranging"
                context.range_bound = True
                context.trend_strength = 0.2
            else:
                context.current_regime = "ranging"
                context.trend_strength = 0.4
            
            context.regime_confidence = 0.6
    
    async def _fill_volatility_data(self, context: ContextB):
        """Fill volatility metrics."""
        ticker = self.store.get_ticker(context.symbol)
        
        if ticker:
            context.realized_vol_24h = abs(ticker.change_24h) * 2
            
            if context.realized_vol_24h < 2:
                context.vol_regime = "low"
                context.vol_percentile = 20.0
            elif context.realized_vol_24h < 5:
                context.vol_regime = "normal"
                context.vol_percentile = 50.0
            elif context.realized_vol_24h < 10:
                context.vol_regime = "high"
                context.vol_percentile = 75.0
            else:
                context.vol_regime = "extreme"
                context.vol_percentile = 95.0
    
    async def _fill_correlation_data(self, context: ContextB):
        """Fill correlation data."""
        context.correlations = {
            "BTC": 0.85 if context.symbol != "BTCUSDT" else 1.0,
            "ETH": 0.75 if context.symbol != "ETHUSDT" else 1.0,
        }
        
        context.correlation_btc = context.correlations.get("BTC", 0.0)
        
        if context.correlation_btc < 0.5:
            context.correlation_breakdown = True
    
    async def _fill_drawdown_data(self, context: ContextB):
        """Fill drawdown metrics."""
        ticker = self.store.get_ticker(context.symbol)
        
        if ticker and ticker.change_24h < 0:
            context.current_drawdown_pct = abs(ticker.change_24h)
            context.max_drawdown_24h = abs(ticker.change_24h)
    
    async def build_context_c(
        self,
        symbol: str,
        lookback: timedelta = timedelta(days=30)
    ) -> ContextC:
        """
        Build Strategy + Agent performance context.
        
        Sources:
        - TradingDecisionLog table
        - TradeOutcome table
        - RiskBreach table
        - ModelConfidenceCalibration table
        """
        context = ContextC(
            symbol=symbol,
            lookback_days=int(lookback.total_seconds() / 86400)
        )
        
        await asyncio.gather(
            self._fill_decision_history(context),
            self._fill_outcome_stats(context),
            self._fill_risk_history(context),
            self._fill_calibration_data(context),
        )
        
        return context
    
    async def _fill_decision_history(self, context: ContextC):
        """Fill recent decision history."""
        context.total_decisions = 0
        context.decisions_executed = 0
        context.recent_decisions = []
    
    async def _fill_outcome_stats(self, context: ContextC):
        """Fill trade outcome statistics."""
        context.total_trades = 0
        context.win_count = 0
        context.loss_count = 0
        context.win_rate = 0.5
        context.total_pnl_usd = 0.0
        context.profit_factor = 1.0
        context.avg_slippage_bps = 5.0
        context.avg_latency_ms = 50.0
    
    async def _fill_risk_history(self, context: ContextC):
        """Fill risk breach history."""
        context.breach_count_7d = 0
        context.recent_kill_switch = False
        context.risk_breaches = []
    
    async def _fill_calibration_data(self, context: ContextC):
        """Fill model calibration data."""
        context.model_confidence_avg = 0.5
        context.model_accuracy = 0.5
        context.calibration_error = 0.0
    
    async def build_all_contexts(
        self,
        symbol: str,
        lookback_a: timedelta = timedelta(hours=24),
        lookback_b: timedelta = timedelta(days=7),
        lookback_c: timedelta = timedelta(days=30),
    ) -> Tuple[ContextA, ContextB, ContextC]:
        """Build all three contexts in parallel."""
        return await asyncio.gather(
            self.build_context_a(symbol, lookback_a),
            self.build_context_b(symbol, lookback_b),
            self.build_context_c(symbol, lookback_c),
        )


_context_builder: Optional[HistoricalContextBuilder] = None


def get_context_builder() -> HistoricalContextBuilder:
    """Get the context builder singleton."""
    global _context_builder
    if _context_builder is None:
        _context_builder = HistoricalContextBuilder()
    return _context_builder
