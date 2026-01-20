"""
Decision Arbiter - Cross-Thought Reconciliation for ChatOS

This module reconciles multiple thought outputs into a single, coherent
trading decision. When multiple thoughts generate potentially conflicting
signals, the arbiter:

1. Aggregates signals with confidence weighting
2. Detects and handles conflicts
3. Generates a unified execution decision
4. Provides reasoning for the final decision
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from chatos_backend.services.thought_engine import (
    ThoughtRun, ThoughtStatus, TradingSignal, TradingDecision
)

logger = logging.getLogger(__name__)


class ArbiterAction(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE = "CLOSE"
    HOLD = "HOLD"
    CONFLICT = "CONFLICT"


@dataclass
class ConflictInfo:
    """Information about detected conflicts between thoughts."""
    has_conflict: bool = False
    conflict_type: str = ""
    conflicting_thoughts: List[str] = field(default_factory=list)
    signals_involved: List[str] = field(default_factory=list)
    resolution: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_conflict": self.has_conflict,
            "conflict_type": self.conflict_type,
            "conflicting_thoughts": self.conflicting_thoughts,
            "signals_involved": self.signals_involved,
            "resolution": self.resolution,
        }


@dataclass
class ArbiterDecision:
    """Final decision from the arbiter after reconciling all thoughts."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    action: ArbiterAction = ArbiterAction.HOLD
    symbol: str = ""
    
    size: Optional[float] = None
    entry: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    leverage: float = 1.0
    
    confidence: float = 0.5
    reason: str = ""
    
    contributing_thoughts: List[str] = field(default_factory=list)
    thought_count: int = 0
    passed_count: int = 0
    
    conflict_info: Optional[ConflictInfo] = None
    
    signal_votes: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "symbol": self.symbol,
            "size": self.size,
            "entry": self.entry,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "leverage": self.leverage,
            "confidence": self.confidence,
            "reason": self.reason,
            "contributing_thoughts": self.contributing_thoughts,
            "thought_count": self.thought_count,
            "passed_count": self.passed_count,
            "conflict_info": self.conflict_info.to_dict() if self.conflict_info else None,
            "signal_votes": self.signal_votes,
        }


class DecisionArbiter:
    """
    Reconciles multiple thought outputs into a single execution decision.
    
    Voting Strategy:
    - Each thought's signal is weighted by its confidence
    - Conflicting signals (LONG vs SHORT) require resolution
    - CLOSE signals are prioritized if any thought recommends closing
    - HOLD is the fallback when no clear consensus
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        
        self.min_confidence_threshold = self.config.get("min_confidence_threshold", 0.4)
        self.consensus_threshold = self.config.get("consensus_threshold", 0.6)
        self.conflict_penalty = self.config.get("conflict_penalty", 0.3)
        self.close_priority = self.config.get("close_priority", True)
    
    async def reconcile(self, thoughts: List[ThoughtRun]) -> ArbiterDecision:
        """
        Reconcile multiple thoughts into a single decision.
        
        Args:
            thoughts: List of completed ThoughtRun objects
        
        Returns:
            ArbiterDecision with the final action and reasoning
        """
        passed = [t for t in thoughts if t.status in (ThoughtStatus.PASSED, ThoughtStatus.WARNED)]
        
        decision = ArbiterDecision(
            thought_count=len(thoughts),
            passed_count=len(passed),
        )
        
        if not passed:
            decision.action = ArbiterAction.HOLD
            decision.reason = "No thoughts passed filters"
            decision.confidence = 0.2
            return decision
        
        if passed:
            decision.symbol = passed[0].spec.symbol
        
        weighted_votes = self._calculate_weighted_votes(passed)
        decision.signal_votes = weighted_votes
        
        conflict_info = self._detect_conflicts(passed, weighted_votes)
        decision.conflict_info = conflict_info
        
        if conflict_info.has_conflict:
            decision = self._resolve_conflict(decision, passed, weighted_votes, conflict_info)
        else:
            decision = self._determine_action(decision, passed, weighted_votes)
        
        decision = self._calculate_execution_params(decision, passed)
        decision.contributing_thoughts = [t.id for t in passed if t.decision]
        
        return decision
    
    def _calculate_weighted_votes(self, thoughts: List[ThoughtRun]) -> Dict[str, float]:
        """Calculate confidence-weighted votes for each signal type."""
        votes = {
            "LONG": 0.0,
            "SHORT": 0.0,
            "CLOSE": 0.0,
            "HOLD": 0.0,
        }
        
        total_confidence = sum(
            t.decision.confidence for t in thoughts
            if t.decision and t.decision.confidence > 0
        )
        
        for thought in thoughts:
            if not thought.decision:
                continue
            
            signal = thought.decision.signal.value
            confidence = thought.decision.confidence
            
            if total_confidence > 0:
                weight = confidence / total_confidence
            else:
                weight = 1.0 / len(thoughts)
            
            votes[signal] += weight * confidence
        
        return votes
    
    def _detect_conflicts(
        self,
        thoughts: List[ThoughtRun],
        votes: Dict[str, float]
    ) -> ConflictInfo:
        """Detect conflicts between thought signals."""
        long_vote = votes.get("LONG", 0)
        short_vote = votes.get("SHORT", 0)
        
        if long_vote > 0.2 and short_vote > 0.2:
            long_thoughts = [t.id for t in thoughts if t.decision and t.decision.signal == TradingSignal.LONG]
            short_thoughts = [t.id for t in thoughts if t.decision and t.decision.signal == TradingSignal.SHORT]
            
            return ConflictInfo(
                has_conflict=True,
                conflict_type="directional_conflict",
                conflicting_thoughts=long_thoughts + short_thoughts,
                signals_involved=["LONG", "SHORT"],
            )
        
        return ConflictInfo(has_conflict=False)
    
    def _resolve_conflict(
        self,
        decision: ArbiterDecision,
        thoughts: List[ThoughtRun],
        votes: Dict[str, float],
        conflict_info: ConflictInfo
    ) -> ArbiterDecision:
        """Resolve conflicts between signals."""
        long_vote = votes.get("LONG", 0)
        short_vote = votes.get("SHORT", 0)
        
        diff = abs(long_vote - short_vote)
        
        if diff < 0.2:
            decision.action = ArbiterAction.HOLD
            decision.reason = "Conflicting signals with no clear winner - defaulting to HOLD"
            decision.confidence = max(long_vote, short_vote) * (1 - self.conflict_penalty)
            conflict_info.resolution = "hold_due_to_conflict"
        else:
            if long_vote > short_vote:
                decision.action = ArbiterAction.LONG
                decision.reason = f"LONG wins conflict ({long_vote:.2f} vs {short_vote:.2f} SHORT)"
            else:
                decision.action = ArbiterAction.SHORT
                decision.reason = f"SHORT wins conflict ({short_vote:.2f} vs {long_vote:.2f} LONG)"
            
            decision.confidence = max(long_vote, short_vote) * (1 - self.conflict_penalty * 0.5)
            conflict_info.resolution = "majority_wins"
        
        return decision
    
    def _determine_action(
        self,
        decision: ArbiterDecision,
        thoughts: List[ThoughtRun],
        votes: Dict[str, float]
    ) -> ArbiterDecision:
        """Determine action when there's no conflict."""
        if self.close_priority and votes.get("CLOSE", 0) > 0.3:
            decision.action = ArbiterAction.CLOSE
            decision.confidence = votes["CLOSE"]
            decision.reason = "CLOSE signal prioritized"
            return decision
        
        max_signal = max(votes, key=votes.get)
        max_vote = votes[max_signal]
        
        if max_vote < self.min_confidence_threshold:
            decision.action = ArbiterAction.HOLD
            decision.reason = f"No signal meets confidence threshold ({max_vote:.2f} < {self.min_confidence_threshold})"
            decision.confidence = max_vote
            return decision
        
        action_map = {
            "LONG": ArbiterAction.LONG,
            "SHORT": ArbiterAction.SHORT,
            "CLOSE": ArbiterAction.CLOSE,
            "HOLD": ArbiterAction.HOLD,
        }
        
        decision.action = action_map.get(max_signal, ArbiterAction.HOLD)
        decision.confidence = max_vote
        decision.reason = f"Consensus on {max_signal} ({max_vote:.2f})"
        
        return decision
    
    def _calculate_execution_params(
        self,
        decision: ArbiterDecision,
        thoughts: List[ThoughtRun]
    ) -> ArbiterDecision:
        """Calculate execution parameters from contributing thoughts."""
        if decision.action in (ArbiterAction.HOLD, ArbiterAction.CONFLICT):
            return decision
        
        relevant = [
            t for t in thoughts
            if t.decision and t.decision.signal.value == decision.action.value
        ]
        
        if not relevant:
            return decision
        
        entries = [t.decision.entry_price for t in relevant if t.decision.entry_price]
        if entries:
            decision.entry = sum(entries) / len(entries)
        
        stop_losses = [t.decision.stop_loss for t in relevant if t.decision.stop_loss]
        if stop_losses:
            if decision.action == ArbiterAction.LONG:
                decision.stop_loss = max(stop_losses)
            else:
                decision.stop_loss = min(stop_losses)
        
        take_profits = [t.decision.take_profit for t in relevant if t.decision.take_profit]
        if take_profits:
            if decision.action == ArbiterAction.LONG:
                decision.take_profit = min(take_profits)
            else:
                decision.take_profit = max(take_profits)
        
        if decision.entry and decision.stop_loss:
            risk_pct = abs(decision.entry - decision.stop_loss) / decision.entry
            base_size = 0.02
            decision.size = base_size / risk_pct if risk_pct > 0 else 0.01
            decision.size = min(decision.size, 0.1)
        
        return decision


_arbiter: Optional[DecisionArbiter] = None


def get_arbiter() -> DecisionArbiter:
    """Get the decision arbiter singleton."""
    global _arbiter
    if _arbiter is None:
        _arbiter = DecisionArbiter()
    return _arbiter
