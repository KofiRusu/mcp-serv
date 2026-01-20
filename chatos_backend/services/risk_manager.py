"""
Risk Manager - Safety Layer for ChatOS Trading System

This module provides risk management and safety controls including:
- Position size limits
- Daily loss limits
- Kill switches for emergency stops
- Data freshness validation
- Correlation exposure checks

All trading decisions must pass through the risk manager before execution.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import uuid

from chatos_backend.core.event_bus import get_event_bus, EventPriority
from chatos_backend.services.decision_arbiter import ArbiterDecision, ArbiterAction

logger = logging.getLogger(__name__)


class RiskCheckType(str, Enum):
    POSITION_SIZE = "position_size"
    DAILY_LOSS = "daily_loss"
    MAX_POSITIONS = "max_positions"
    DRAWDOWN = "drawdown"
    CORRELATION = "correlation"
    DATA_FRESHNESS = "data_freshness"
    EXCHANGE_STATUS = "exchange_status"
    KILL_SWITCH = "kill_switch"


class RiskSeverity(int, Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class RiskCheck:
    """Result of a single risk check."""
    check_type: RiskCheckType
    passed: bool
    severity: RiskSeverity = RiskSeverity.LOW
    reason: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "check_type": self.check_type.value,
            "passed": self.passed,
            "severity": self.severity.value,
            "reason": self.reason,
            "details": self.details,
        }


@dataclass
class RiskResult:
    """Overall result of risk validation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    approved: bool = True
    reason: str = ""
    max_severity: RiskSeverity = RiskSeverity.LOW
    
    checks: List[RiskCheck] = field(default_factory=list)
    
    warnings: List[str] = field(default_factory=list)
    
    adjusted_size: Optional[float] = None
    adjusted_leverage: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "approved": self.approved,
            "reason": self.reason,
            "max_severity": self.max_severity.value,
            "checks": [c.to_dict() for c in self.checks],
            "warnings": self.warnings,
            "adjusted_size": self.adjusted_size,
            "adjusted_leverage": self.adjusted_leverage,
        }


@dataclass
class RiskLimits:
    """Risk limit configuration."""
    max_position_size_usd: float = 10000.0
    max_position_pct: float = 0.10
    max_positions: int = 5
    
    max_daily_loss_usd: float = 500.0
    max_daily_loss_pct: float = 0.05
    
    max_drawdown_pct: float = 0.10
    rapid_drawdown_threshold: float = 0.03
    rapid_drawdown_window_minutes: int = 5
    
    max_correlation_exposure: float = 0.8
    max_same_direction_positions: int = 3
    
    max_data_age_seconds: int = 30
    
    max_leverage: float = 5.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_position_size_usd": self.max_position_size_usd,
            "max_position_pct": self.max_position_pct,
            "max_positions": self.max_positions,
            "max_daily_loss_usd": self.max_daily_loss_usd,
            "max_daily_loss_pct": self.max_daily_loss_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_leverage": self.max_leverage,
        }


class RiskManager:
    """
    Central risk management and safety system.
    
    Validates all trading decisions against risk limits and can
    trigger emergency shutdowns via kill switches.
    """
    
    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self._event_bus = None
        self._store = None
        
        self._kill_switch_active = False
        self._kill_switch_reason: Optional[str] = None
        self._kill_switch_time: Optional[datetime] = None
        
        self._daily_pnl: float = 0.0
        self._daily_pnl_reset: Optional[datetime] = None
        
        self._open_positions: List[Dict[str, Any]] = []
        self._recent_checks: List[RiskResult] = []
        
        self._blocked_symbols: Set[str] = set()
    
    @property
    def event_bus(self):
        if self._event_bus is None:
            self._event_bus = get_event_bus()
        return self._event_bus
    
    @property
    def store(self):
        if self._store is None:
            from chatos_backend.services.realtime_data_store import get_realtime_store
            self._store = get_realtime_store()
        return self._store
    
    async def validate_decision(
        self,
        decision: ArbiterDecision,
        account_balance: float = 100000.0,
    ) -> RiskResult:
        """
        Validate a trading decision against all risk checks.
        
        Args:
            decision: The arbiter decision to validate
            account_balance: Current account balance in USD
        
        Returns:
            RiskResult indicating approval status and any adjustments
        """
        result = RiskResult()
        
        if decision.action in (ArbiterAction.HOLD, ArbiterAction.CONFLICT):
            result.approved = True
            result.reason = "No execution required"
            return result
        
        checks = await asyncio.gather(
            self._check_kill_switch(decision),
            self._check_position_size(decision, account_balance),
            self._check_daily_loss(decision, account_balance),
            self._check_max_positions(decision),
            self._check_data_freshness(decision),
        )
        
        result.checks = list(checks)
        
        failed_checks = [c for c in result.checks if not c.passed]
        
        if failed_checks:
            result.approved = False
            result.max_severity = max(c.severity for c in failed_checks)
            result.reason = "; ".join(c.reason for c in failed_checks)
            
            await self._record_breach(decision, failed_checks)
        else:
            result.approved = True
            result.reason = "All risk checks passed"
            
            warnings = [c for c in result.checks if c.severity >= RiskSeverity.MEDIUM]
            result.warnings = [c.reason for c in warnings]
        
        result = self._apply_adjustments(result, decision, account_balance)
        
        self._recent_checks.append(result)
        if len(self._recent_checks) > 100:
            self._recent_checks = self._recent_checks[-100:]
        
        return result
    
    async def _check_kill_switch(self, decision: ArbiterDecision) -> RiskCheck:
        """Check if kill switch is active."""
        if self._kill_switch_active:
            return RiskCheck(
                check_type=RiskCheckType.KILL_SWITCH,
                passed=False,
                severity=RiskSeverity.CRITICAL,
                reason=f"Kill switch active: {self._kill_switch_reason}",
                details={
                    "triggered_at": self._kill_switch_time.isoformat() if self._kill_switch_time else None,
                },
            )
        
        return RiskCheck(
            check_type=RiskCheckType.KILL_SWITCH,
            passed=True,
            reason="Kill switch not active",
        )
    
    async def _check_position_size(
        self,
        decision: ArbiterDecision,
        account_balance: float
    ) -> RiskCheck:
        """Check position size limits."""
        if not decision.size:
            return RiskCheck(
                check_type=RiskCheckType.POSITION_SIZE,
                passed=True,
                reason="No position size specified",
            )
        
        position_usd = decision.size * account_balance
        position_pct = decision.size
        
        if position_usd > self.limits.max_position_size_usd:
            return RiskCheck(
                check_type=RiskCheckType.POSITION_SIZE,
                passed=False,
                severity=RiskSeverity.HIGH,
                reason=f"Position size ${position_usd:.0f} exceeds max ${self.limits.max_position_size_usd:.0f}",
                details={
                    "requested_usd": position_usd,
                    "max_usd": self.limits.max_position_size_usd,
                },
            )
        
        if position_pct > self.limits.max_position_pct:
            return RiskCheck(
                check_type=RiskCheckType.POSITION_SIZE,
                passed=False,
                severity=RiskSeverity.HIGH,
                reason=f"Position size {position_pct:.1%} exceeds max {self.limits.max_position_pct:.1%}",
                details={
                    "requested_pct": position_pct,
                    "max_pct": self.limits.max_position_pct,
                },
            )
        
        return RiskCheck(
            check_type=RiskCheckType.POSITION_SIZE,
            passed=True,
            reason=f"Position size ${position_usd:.0f} within limits",
        )
    
    async def _check_daily_loss(
        self,
        decision: ArbiterDecision,
        account_balance: float
    ) -> RiskCheck:
        """Check daily loss limits."""
        self._reset_daily_pnl_if_needed()
        
        daily_loss_pct = abs(self._daily_pnl) / account_balance if account_balance > 0 else 0
        
        if self._daily_pnl < 0:
            if abs(self._daily_pnl) >= self.limits.max_daily_loss_usd:
                return RiskCheck(
                    check_type=RiskCheckType.DAILY_LOSS,
                    passed=False,
                    severity=RiskSeverity.CRITICAL,
                    reason=f"Daily loss ${abs(self._daily_pnl):.0f} exceeds max ${self.limits.max_daily_loss_usd:.0f}",
                    details={
                        "daily_pnl": self._daily_pnl,
                        "max_loss": self.limits.max_daily_loss_usd,
                    },
                )
            
            if daily_loss_pct >= self.limits.max_daily_loss_pct:
                return RiskCheck(
                    check_type=RiskCheckType.DAILY_LOSS,
                    passed=False,
                    severity=RiskSeverity.CRITICAL,
                    reason=f"Daily loss {daily_loss_pct:.1%} exceeds max {self.limits.max_daily_loss_pct:.1%}",
                )
        
        severity = RiskSeverity.LOW
        if daily_loss_pct > self.limits.max_daily_loss_pct * 0.5:
            severity = RiskSeverity.MEDIUM
        
        return RiskCheck(
            check_type=RiskCheckType.DAILY_LOSS,
            passed=True,
            severity=severity,
            reason=f"Daily P&L: ${self._daily_pnl:+.0f}",
        )
    
    async def _check_max_positions(self, decision: ArbiterDecision) -> RiskCheck:
        """Check maximum number of positions."""
        current_positions = len(self._open_positions)
        
        if decision.action in (ArbiterAction.LONG, ArbiterAction.SHORT):
            if current_positions >= self.limits.max_positions:
                return RiskCheck(
                    check_type=RiskCheckType.MAX_POSITIONS,
                    passed=False,
                    severity=RiskSeverity.MEDIUM,
                    reason=f"Max positions ({self.limits.max_positions}) reached",
                    details={
                        "current_positions": current_positions,
                        "max_positions": self.limits.max_positions,
                    },
                )
        
        return RiskCheck(
            check_type=RiskCheckType.MAX_POSITIONS,
            passed=True,
            reason=f"Position count OK ({current_positions}/{self.limits.max_positions})",
        )
    
    async def _check_data_freshness(self, decision: ArbiterDecision) -> RiskCheck:
        """Check that market data is fresh enough for trading."""
        ticker = self.store.get_ticker(decision.symbol)
        
        if not ticker:
            return RiskCheck(
                check_type=RiskCheckType.DATA_FRESHNESS,
                passed=False,
                severity=RiskSeverity.HIGH,
                reason=f"No market data for {decision.symbol}",
            )
        
        try:
            if isinstance(ticker.timestamp, str):
                data_time = datetime.fromisoformat(ticker.timestamp.replace('Z', '+00:00'))
            else:
                data_time = ticker.timestamp
            
            age_seconds = (datetime.now(timezone.utc) - data_time).total_seconds()
            
            if age_seconds > self.limits.max_data_age_seconds:
                return RiskCheck(
                    check_type=RiskCheckType.DATA_FRESHNESS,
                    passed=False,
                    severity=RiskSeverity.HIGH,
                    reason=f"Data for {decision.symbol} is {age_seconds:.0f}s old (max {self.limits.max_data_age_seconds}s)",
                    details={
                        "data_age_seconds": age_seconds,
                        "max_age_seconds": self.limits.max_data_age_seconds,
                    },
                )
        except Exception as e:
            logger.warning(f"Could not parse data timestamp: {e}")
        
        return RiskCheck(
            check_type=RiskCheckType.DATA_FRESHNESS,
            passed=True,
            reason=f"Data for {decision.symbol} is current",
        )
    
    def _reset_daily_pnl_if_needed(self):
        """Reset daily P&L at midnight UTC."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        if self._daily_pnl_reset is None or self._daily_pnl_reset < today_start:
            self._daily_pnl = 0.0
            self._daily_pnl_reset = now
    
    def _apply_adjustments(
        self,
        result: RiskResult,
        decision: ArbiterDecision,
        account_balance: float
    ) -> RiskResult:
        """Apply risk-based adjustments to position sizing."""
        if not result.approved:
            return result
        
        if decision.size:
            max_size_pct = self.limits.max_position_pct
            if decision.size > max_size_pct:
                result.adjusted_size = max_size_pct
                result.warnings.append(f"Size reduced from {decision.size:.1%} to {max_size_pct:.1%}")
        
        if decision.leverage > self.limits.max_leverage:
            result.adjusted_leverage = self.limits.max_leverage
            result.warnings.append(f"Leverage reduced from {decision.leverage}x to {self.limits.max_leverage}x")
        
        return result
    
    async def _record_breach(
        self,
        decision: ArbiterDecision,
        failed_checks: List[RiskCheck]
    ):
        """Record a risk breach event."""
        max_severity = max(c.severity for c in failed_checks)
        
        await self.event_bus.publish(
            "risk.blocked",
            {
                "decision_id": decision.id,
                "symbol": decision.symbol,
                "action": decision.action.value,
                "failed_checks": [c.to_dict() for c in failed_checks],
                "max_severity": max_severity.value,
            },
            priority=EventPriority.HIGH,
            source="risk_manager"
        )
        
        if max_severity >= RiskSeverity.CRITICAL:
            await self.trigger_kill_switch(f"Critical risk breach: {failed_checks[0].reason}")
    
    async def trigger_kill_switch(self, reason: str):
        """Activate the kill switch to stop all trading."""
        self._kill_switch_active = True
        self._kill_switch_reason = reason
        self._kill_switch_time = datetime.now(timezone.utc)
        
        logger.critical(f"KILL SWITCH ACTIVATED: {reason}")
        
        await self.event_bus.publish(
            "risk.kill_switch",
            {
                "reason": reason,
                "timestamp": self._kill_switch_time.isoformat(),
            },
            priority=EventPriority.CRITICAL,
            source="risk_manager"
        )
    
    async def reset_kill_switch(self, admin_override: bool = False):
        """Reset the kill switch (requires admin override)."""
        if not admin_override:
            logger.warning("Kill switch reset attempted without admin override")
            return False
        
        self._kill_switch_active = False
        self._kill_switch_reason = None
        self._kill_switch_time = None
        
        logger.info("Kill switch reset by admin")
        
        await self.event_bus.publish(
            "risk.kill_switch_reset",
            {"admin_override": True},
            source="risk_manager"
        )
        
        return True
    
    def update_daily_pnl(self, pnl_change: float):
        """Update the daily P&L tracker."""
        self._reset_daily_pnl_if_needed()
        self._daily_pnl += pnl_change
    
    def update_positions(self, positions: List[Dict[str, Any]]):
        """Update the list of open positions."""
        self._open_positions = positions
    
    def get_status(self) -> Dict[str, Any]:
        """Get current risk manager status."""
        return {
            "kill_switch_active": self._kill_switch_active,
            "kill_switch_reason": self._kill_switch_reason,
            "daily_pnl": self._daily_pnl,
            "open_positions": len(self._open_positions),
            "blocked_symbols": list(self._blocked_symbols),
            "limits": self.limits.to_dict(),
            "recent_checks": len(self._recent_checks),
        }


_risk_manager: Optional[RiskManager] = None


def get_risk_manager() -> RiskManager:
    """Get the risk manager singleton."""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager()
    return _risk_manager
