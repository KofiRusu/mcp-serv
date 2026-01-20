"""
Trading History Models - Historical Data Types A/B/C for Thought-Line Processing

This module defines the database models for storing historical trading data
that serves as FILTERS in the thought-line processing system:

- Type A: Market Microstructure + Orderflow (trades, CVD, whale prints, liquidations, funding, OI)
- Type B: Regime + Volatility (trend/range, vol clusters, correlations, drawdowns, liquidity)  
- Type C: Strategy + Agent Performance (decisions, outcomes, slippage, latency, risk, confidence)

These models enable:
1. Real-time data persistence from scrapers
2. Historical context building for thought evaluation
3. Deterministic replay via stored snapshots
4. Performance calibration and risk assessment
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Column, Integer, Float, String, Text, DateTime, Boolean,
    Enum as SQLEnum, ForeignKey, Index, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())[:12]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class RegimeType(str, Enum):
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE_BREAKOUT = "volatile_breakout"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"


class VolatilityRegime(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    EXTREME = "extreme"


class TradingSignal(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE = "CLOSE"
    HOLD = "HOLD"


class ThoughtStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    WARNED = "warned"
    BLOCKED = "blocked"
    FAILED = "failed"


class FilterResult(str, Enum):
    PASS = "pass"
    WARN = "warn"
    BLOCK = "block"


class RiskBreachType(str, Enum):
    POSITION_SIZE = "position_size"
    DAILY_LOSS = "daily_loss"
    DRAWDOWN = "drawdown"
    CORRELATION = "correlation"
    STALE_DATA = "stale_data"
    EXCHANGE_ERROR = "exchange_error"
    KILL_SWITCH = "kill_switch"


class OrderflowSnapshot(Base):
    """
    Historical Type A: Market Microstructure + Orderflow
    Stores aggregated trade data for a time window.
    """
    __tablename__ = "orderflow_snapshots"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    window_seconds = Column(Integer, default=60)
    
    trades_count = Column(Integer, default=0)
    buy_count = Column(Integer, default=0)
    sell_count = Column(Integer, default=0)
    
    buy_volume = Column(Float, default=0.0)
    sell_volume = Column(Float, default=0.0)
    total_volume = Column(Float, default=0.0)
    
    buy_value_usd = Column(Float, default=0.0)
    sell_value_usd = Column(Float, default=0.0)
    
    delta = Column(Float, default=0.0)
    delta_pct = Column(Float, default=0.0)
    cvd = Column(Float, default=0.0)
    
    vwap = Column(Float, default=0.0)
    spread_bps = Column(Float, default=0.0)
    
    price_open = Column(Float, default=0.0)
    price_high = Column(Float, default=0.0)
    price_low = Column(Float, default=0.0)
    price_close = Column(Float, default=0.0)
    
    whale_trades = Column(JSON, default=list)
    large_trade_count = Column(Integer, default=0)
    large_trade_value_usd = Column(Float, default=0.0)
    
    __table_args__ = (
        Index('ix_orderflow_symbol_time', 'symbol', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "window_seconds": self.window_seconds,
            "trades_count": self.trades_count,
            "buy_volume": self.buy_volume,
            "sell_volume": self.sell_volume,
            "delta": self.delta,
            "delta_pct": self.delta_pct,
            "cvd": self.cvd,
            "vwap": self.vwap,
            "spread_bps": self.spread_bps,
            "whale_trades": self.whale_trades,
            "large_trade_count": self.large_trade_count,
        }


class LiquidationEvent(Base):
    """Historical Type A: Individual liquidation events."""
    __tablename__ = "liquidation_events"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    
    side = Column(SQLEnum(TradeSide), nullable=False)
    amount_usd = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Float, default=0.0)
    
    is_large = Column(Boolean, default=False)
    
    __table_args__ = (
        Index('ix_liquidation_symbol_time', 'symbol', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "side": self.side.value if self.side else None,
            "amount_usd": self.amount_usd,
            "price": self.price,
            "is_large": self.is_large,
        }


class FundingRate(Base):
    """Historical Type A: Funding rate snapshots."""
    __tablename__ = "funding_rates"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    
    rate = Column(Float, nullable=False)
    predicted_rate = Column(Float, default=None)
    mark_price = Column(Float, default=None)
    index_price = Column(Float, default=None)
    
    __table_args__ = (
        Index('ix_funding_symbol_time', 'symbol', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "rate": self.rate,
            "predicted_rate": self.predicted_rate,
        }


class OpenInterest(Base):
    """Historical Type A: Open interest snapshots."""
    __tablename__ = "open_interest"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    
    oi_value = Column(Float, nullable=False)
    oi_contracts = Column(Float, default=None)
    oi_change_1h = Column(Float, default=0.0)
    oi_change_24h = Column(Float, default=0.0)
    
    __table_args__ = (
        Index('ix_oi_symbol_time', 'symbol', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "oi_value": self.oi_value,
            "oi_change_1h": self.oi_change_1h,
            "oi_change_24h": self.oi_change_24h,
        }


class RegimeClassification(Base):
    """Historical Type B: Market regime classifications."""
    __tablename__ = "regime_classifications"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    
    regime = Column(SQLEnum(RegimeType), nullable=False)
    confidence = Column(Float, default=0.5)
    method = Column(String(50), default="default")
    
    trend_strength = Column(Float, default=0.0)
    range_bound = Column(Boolean, default=False)
    breakout_probability = Column(Float, default=0.0)
    
    supporting_indicators = Column(JSON, default=dict)
    
    __table_args__ = (
        Index('ix_regime_symbol_time', 'symbol', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "regime": self.regime.value if self.regime else None,
            "confidence": self.confidence,
            "method": self.method,
            "trend_strength": self.trend_strength,
        }


class VolatilitySnapshot(Base):
    """Historical Type B: Volatility measurements."""
    __tablename__ = "volatility_snapshots"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    
    realized_vol_1h = Column(Float, default=0.0)
    realized_vol_24h = Column(Float, default=0.0)
    realized_vol_7d = Column(Float, default=0.0)
    
    vol_regime = Column(SQLEnum(VolatilityRegime), default=VolatilityRegime.NORMAL)
    vol_percentile = Column(Float, default=50.0)
    
    atr_1h = Column(Float, default=0.0)
    atr_24h = Column(Float, default=0.0)
    
    high_24h = Column(Float, default=0.0)
    low_24h = Column(Float, default=0.0)
    range_pct = Column(Float, default=0.0)
    
    __table_args__ = (
        Index('ix_vol_symbol_time', 'symbol', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "realized_vol_24h": self.realized_vol_24h,
            "vol_regime": self.vol_regime.value if self.vol_regime else None,
            "vol_percentile": self.vol_percentile,
            "range_pct": self.range_pct,
        }


class CorrelationMatrix(Base):
    """Historical Type B: Cross-asset correlations."""
    __tablename__ = "correlation_matrices"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    lookback_hours = Column(Integer, default=24)
    
    pairs = Column(JSON, nullable=False)
    
    btc_dominance = Column(Float, default=0.0)
    average_correlation = Column(Float, default=0.0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "lookback_hours": self.lookback_hours,
            "pairs": self.pairs,
            "btc_dominance": self.btc_dominance,
            "average_correlation": self.average_correlation,
        }


class DrawdownTracker(Base):
    """Historical Type B: Drawdown tracking."""
    __tablename__ = "drawdown_trackers"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    
    peak_price = Column(Float, nullable=False)
    peak_timestamp = Column(DateTime(timezone=True))
    current_price = Column(Float, nullable=False)
    drawdown_pct = Column(Float, nullable=False)
    duration_hours = Column(Float, default=0.0)
    
    max_drawdown_24h = Column(Float, default=0.0)
    max_drawdown_7d = Column(Float, default=0.0)
    
    recovery_pct = Column(Float, default=0.0)
    
    __table_args__ = (
        Index('ix_drawdown_symbol_time', 'symbol', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "drawdown_pct": self.drawdown_pct,
            "duration_hours": self.duration_hours,
            "max_drawdown_24h": self.max_drawdown_24h,
        }


class TradingDecisionLog(Base):
    """Historical Type C: Trading decision records."""
    __tablename__ = "trading_decision_logs"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    thought_id = Column(String(12), index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    
    signal = Column(SQLEnum(TradingSignal), nullable=False)
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    position_size = Column(Float)
    leverage = Column(Float, default=1.0)
    
    confidence = Column(Float, default=0.5)
    reasoning = Column(Text)
    
    model_version = Column(String(50))
    context_hash = Column(String(64))
    
    context_a_snapshot = Column(JSON, default=dict)
    context_b_snapshot = Column(JSON, default=dict)
    context_c_snapshot = Column(JSON, default=dict)
    
    filter_results = Column(JSON, default=dict)
    
    executed = Column(Boolean, default=False)
    execution_id = Column(String(12))
    
    __table_args__ = (
        Index('ix_decision_symbol_time', 'symbol', 'timestamp'),
        Index('ix_decision_thought', 'thought_id'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "thought_id": self.thought_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "symbol": self.symbol,
            "signal": self.signal.value if self.signal else None,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "executed": self.executed,
        }


class TradeOutcome(Base):
    """Historical Type C: Trade outcome records."""
    __tablename__ = "trade_outcomes"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    decision_id = Column(String(12), ForeignKey("trading_decision_logs.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(SQLEnum(TradeSide))
    
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    
    pnl_usd = Column(Float, nullable=False)
    pnl_pct = Column(Float, nullable=False)
    
    slippage_entry_bps = Column(Float, default=0.0)
    slippage_exit_bps = Column(Float, default=0.0)
    total_slippage_bps = Column(Float, default=0.0)
    
    latency_decision_ms = Column(Float, default=0.0)
    latency_execution_ms = Column(Float, default=0.0)
    
    duration_seconds = Column(Float, default=0.0)
    
    hit_stop_loss = Column(Boolean, default=False)
    hit_take_profit = Column(Boolean, default=False)
    manual_close = Column(Boolean, default=False)
    
    fees_usd = Column(Float, default=0.0)
    
    decision = relationship("TradingDecisionLog", backref="outcomes")
    
    __table_args__ = (
        Index('ix_outcome_symbol_time', 'symbol', 'timestamp'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "symbol": self.symbol,
            "pnl_usd": self.pnl_usd,
            "pnl_pct": self.pnl_pct,
            "total_slippage_bps": self.total_slippage_bps,
            "duration_seconds": self.duration_seconds,
        }


class RiskBreach(Base):
    """Historical Type C: Risk breach events."""
    __tablename__ = "risk_breaches"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    
    breach_type = Column(SQLEnum(RiskBreachType), nullable=False)
    severity = Column(Integer, default=1)
    
    symbol = Column(String(20))
    details = Column(JSON, default=dict)
    
    triggered_kill_switch = Column(Boolean, default=False)
    auto_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime(timezone=True))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "breach_type": self.breach_type.value if self.breach_type else None,
            "severity": self.severity,
            "symbol": self.symbol,
            "details": self.details,
            "triggered_kill_switch": self.triggered_kill_switch,
        }


class ModelConfidenceCalibration(Base):
    """Historical Type C: Model confidence calibration records."""
    __tablename__ = "model_confidence_calibrations"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    model_version = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    
    lookback_days = Column(Integer, default=7)
    total_decisions = Column(Integer, default=0)
    
    predicted_confidence_avg = Column(Float, default=0.5)
    actual_accuracy = Column(Float, default=0.5)
    calibration_error = Column(Float, default=0.0)
    
    confidence_buckets = Column(JSON, default=dict)
    
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "model_version": self.model_version,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "calibration_error": self.calibration_error,
            "actual_accuracy": self.actual_accuracy,
            "win_rate": self.win_rate,
        }


class ThoughtTrace(Base):
    """Records of individual thought executions through the pipeline."""
    __tablename__ = "thought_traces"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    thought_id = Column(String(12), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    
    symbol = Column(String(20), nullable=False)
    hypothesis = Column(Text)
    
    status = Column(SQLEnum(ThoughtStatus), default=ThoughtStatus.PENDING)
    
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Float, default=0.0)
    
    live_context = Column(JSON, default=dict)
    context_a = Column(JSON, default=dict)
    context_b = Column(JSON, default=dict)
    context_c = Column(JSON, default=dict)
    
    filter_a_result = Column(SQLEnum(FilterResult))
    filter_a_details = Column(JSON, default=dict)
    filter_b_result = Column(SQLEnum(FilterResult))
    filter_b_details = Column(JSON, default=dict)
    filter_c_result = Column(SQLEnum(FilterResult))
    filter_c_details = Column(JSON, default=dict)
    
    decision_signal = Column(SQLEnum(TradingSignal))
    decision_confidence = Column(Float)
    decision_reasoning = Column(Text)
    
    trace_steps = Column(JSON, default=list)
    
    model_version = Column(String(50))
    config_hash = Column(String(64))
    
    __table_args__ = (
        Index('ix_thought_trace_time', 'timestamp'),
        Index('ix_thought_trace_status', 'status'),
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "thought_id": self.thought_id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "symbol": self.symbol,
            "hypothesis": self.hypothesis,
            "status": self.status.value if self.status else None,
            "duration_ms": self.duration_ms,
            "filter_a_result": self.filter_a_result.value if self.filter_a_result else None,
            "filter_b_result": self.filter_b_result.value if self.filter_b_result else None,
            "filter_c_result": self.filter_c_result.value if self.filter_c_result else None,
            "decision_signal": self.decision_signal.value if self.decision_signal else None,
            "decision_confidence": self.decision_confidence,
        }


class AuditRecord(Base):
    """Audit trail for complete trading cycles (enables deterministic replay)."""
    __tablename__ = "audit_records"
    
    id = Column(String(12), primary_key=True, default=generate_uuid)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=utc_now, index=True)
    
    cycle_id = Column(String(12), nullable=False, unique=True, index=True)
    
    inputs = Column(JSON, nullable=False)
    
    thought_ids = Column(JSON, default=list)
    thought_results = Column(JSON, default=list)
    
    arbiter_decision = Column(JSON)
    risk_check_result = Column(JSON)
    
    execution_result = Column(JSON)
    was_executed = Column(Boolean, default=False)
    
    model_versions = Column(JSON, default=dict)
    config_hash = Column(String(64))
    
    replay_count = Column(Integer, default=0)
    last_replayed_at = Column(DateTime(timezone=True))
    replay_matches = Column(Boolean)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "cycle_id": self.cycle_id,
            "thought_ids": self.thought_ids,
            "was_executed": self.was_executed,
            "replay_count": self.replay_count,
        }


def create_trading_history_tables(engine):
    """Create all trading history tables."""
    Base.metadata.create_all(engine)


def drop_trading_history_tables(engine):
    """Drop all trading history tables."""
    Base.metadata.drop_all(engine)
