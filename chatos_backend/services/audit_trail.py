"""
Audit Trail - Deterministic Replay System for ChatOS

This module provides complete audit trail recording for all trading cycles,
enabling:
1. Full traceability of every decision
2. Deterministic replay from stored inputs
3. Compliance and debugging support
4. Performance analysis over time

Every trading cycle (thoughts → arbiter → risk → execution) is recorded
with all inputs serialized for exact replay.
"""

import asyncio
import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import sqlite3

from chatos_backend.core.event_bus import get_event_bus
from chatos_backend.services.thought_engine import ThoughtRun, ThoughtSpec
from chatos_backend.services.decision_arbiter import ArbiterDecision
from chatos_backend.services.risk_manager import RiskResult
from chatos_backend.services.execution import ExecutionResult
from chatos_backend.services.historical_context import ContextA, ContextB, ContextC

logger = logging.getLogger(__name__)


@dataclass
class CycleInputs:
    """All inputs for a trading cycle (for deterministic replay)."""
    timestamp: datetime
    symbol: str
    
    live_data: Dict[str, Any]
    context_a: Dict[str, Any]
    context_b: Dict[str, Any]
    context_c: Dict[str, Any]
    
    thought_specs: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "symbol": self.symbol,
            "live_data": self.live_data,
            "context_a": self.context_a,
            "context_b": self.context_b,
            "context_c": self.context_c,
            "thought_specs": self.thought_specs,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CycleInputs":
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            symbol=data["symbol"],
            live_data=data["live_data"],
            context_a=data["context_a"],
            context_b=data["context_b"],
            context_c=data["context_c"],
            thought_specs=data.get("thought_specs", []),
        )
    
    def get_hash(self) -> str:
        """Get deterministic hash of inputs for verification."""
        data = json.dumps(self.to_dict(), sort_keys=True, default=str)
        return hashlib.sha256(data.encode()).hexdigest()


@dataclass
class AuditRecord:
    """Complete audit record for a trading cycle."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    cycle_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    inputs: Optional[CycleInputs] = None
    input_hash: str = ""
    
    thought_runs: List[Dict[str, Any]] = field(default_factory=list)
    
    arbiter_decision: Optional[Dict[str, Any]] = None
    risk_result: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    
    was_executed: bool = False
    
    model_versions: Dict[str, str] = field(default_factory=dict)
    config_hash: str = ""
    
    replay_count: int = 0
    last_replayed_at: Optional[datetime] = None
    replay_matches: Optional[bool] = None
    
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp.isoformat(),
            "inputs": self.inputs.to_dict() if self.inputs else None,
            "input_hash": self.input_hash,
            "thought_runs": self.thought_runs,
            "arbiter_decision": self.arbiter_decision,
            "risk_result": self.risk_result,
            "execution_result": self.execution_result,
            "was_executed": self.was_executed,
            "model_versions": self.model_versions,
            "config_hash": self.config_hash,
            "replay_count": self.replay_count,
            "last_replayed_at": self.last_replayed_at.isoformat() if self.last_replayed_at else None,
            "replay_matches": self.replay_matches,
            "duration_ms": self.duration_ms,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditRecord":
        record = cls(
            id=data["id"],
            cycle_id=data["cycle_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            input_hash=data.get("input_hash", ""),
            thought_runs=data.get("thought_runs", []),
            arbiter_decision=data.get("arbiter_decision"),
            risk_result=data.get("risk_result"),
            execution_result=data.get("execution_result"),
            was_executed=data.get("was_executed", False),
            model_versions=data.get("model_versions", {}),
            config_hash=data.get("config_hash", ""),
            replay_count=data.get("replay_count", 0),
            replay_matches=data.get("replay_matches"),
            duration_ms=data.get("duration_ms", 0.0),
        )
        
        if data.get("inputs"):
            record.inputs = CycleInputs.from_dict(data["inputs"])
        
        if data.get("last_replayed_at"):
            record.last_replayed_at = datetime.fromisoformat(data["last_replayed_at"])
        
        return record


@dataclass
class ReplayResult:
    """Result of replaying an audit record."""
    original_record: AuditRecord
    replayed_thoughts: List[Dict[str, Any]] = field(default_factory=list)
    replayed_decision: Optional[Dict[str, Any]] = None
    
    decision_matches: bool = False
    differences: List[str] = field(default_factory=list)
    
    replay_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_cycle_id": self.original_record.cycle_id,
            "original_timestamp": self.original_record.timestamp.isoformat(),
            "replayed_thoughts": self.replayed_thoughts,
            "replayed_decision": self.replayed_decision,
            "decision_matches": self.decision_matches,
            "differences": self.differences,
            "replay_timestamp": self.replay_timestamp.isoformat(),
        }


class AuditTrail:
    """
    Manages audit trail recording and replay for trading cycles.
    
    Stores records in SQLite for persistence and efficient querying.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(
            Path.home() / "ChatOS-Data" / "audit" / "audit_trail.db"
        )
        self._event_bus = None
        self._ensure_db()
    
    @property
    def event_bus(self):
        if self._event_bus is None:
            self._event_bus = get_event_bus()
        return self._event_bus
    
    def _ensure_db(self):
        """Ensure the database exists with correct schema."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_records (
                    id TEXT PRIMARY KEY,
                    cycle_id TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    input_hash TEXT NOT NULL,
                    was_executed INTEGER NOT NULL,
                    decision_action TEXT,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
                ON audit_records(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_symbol 
                ON audit_records(symbol)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_executed 
                ON audit_records(was_executed)
            """)
            
            conn.commit()
        finally:
            conn.close()
    
    async def record_cycle(
        self,
        thoughts: List[ThoughtRun],
        arbiter_decision: ArbiterDecision,
        risk_result: RiskResult,
        execution_result: Optional[ExecutionResult] = None,
        context_a: Optional[ContextA] = None,
        context_b: Optional[ContextB] = None,
        context_c: Optional[ContextC] = None,
    ) -> AuditRecord:
        """Record a complete trading cycle."""
        symbol = arbiter_decision.symbol or (thoughts[0].spec.symbol if thoughts else "UNKNOWN")
        
        inputs = CycleInputs(
            timestamp=datetime.now(timezone.utc),
            symbol=symbol,
            live_data=thoughts[0].live_context if thoughts else {},
            context_a=context_a.to_dict() if context_a else {},
            context_b=context_b.to_dict() if context_b else {},
            context_c=context_c.to_dict() if context_c else {},
            thought_specs=[t.spec.to_dict() for t in thoughts],
        )
        
        record = AuditRecord(
            inputs=inputs,
            input_hash=inputs.get_hash(),
            thought_runs=[t.to_dict() for t in thoughts],
            arbiter_decision=arbiter_decision.to_dict(),
            risk_result=risk_result.to_dict(),
            execution_result=execution_result.to_dict() if execution_result else None,
            was_executed=execution_result.success if execution_result else False,
            model_versions=self._get_model_versions(),
            config_hash=self._get_config_hash(),
        )
        
        if thoughts:
            start = min(t.started_at for t in thoughts)
            end = max(t.completed_at or datetime.now(timezone.utc) for t in thoughts)
            record.duration_ms = (end - start).total_seconds() * 1000
        
        await self._persist(record)
        
        await self.event_bus.publish(
            "audit.recorded",
            {
                "record_id": record.id,
                "cycle_id": record.cycle_id,
                "symbol": symbol,
                "was_executed": record.was_executed,
            },
            source="audit_trail"
        )
        
        return record
    
    async def _persist(self, record: AuditRecord):
        """Persist a record to the database."""
        conn = sqlite3.connect(self.db_path)
        try:
            symbol = record.inputs.symbol if record.inputs else "UNKNOWN"
            action = record.arbiter_decision.get("action") if record.arbiter_decision else None
            
            conn.execute("""
                INSERT OR REPLACE INTO audit_records 
                (id, cycle_id, timestamp, symbol, input_hash, was_executed, decision_action, data, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.cycle_id,
                record.timestamp.isoformat(),
                symbol,
                record.input_hash,
                1 if record.was_executed else 0,
                action,
                json.dumps(record.to_dict()),
                datetime.now(timezone.utc).isoformat(),
            ))
            
            conn.commit()
        finally:
            conn.close()
    
    async def get_record(self, record_id: str) -> Optional[AuditRecord]:
        """Get a record by ID."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT data FROM audit_records WHERE id = ? OR cycle_id = ?",
                (record_id, record_id)
            )
            row = cursor.fetchone()
            
            if row:
                return AuditRecord.from_dict(json.loads(row[0]))
            return None
        finally:
            conn.close()
    
    async def get_records(
        self,
        symbol: Optional[str] = None,
        executed_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditRecord]:
        """Get records with optional filtering."""
        conn = sqlite3.connect(self.db_path)
        try:
            query = "SELECT data FROM audit_records WHERE 1=1"
            params = []
            
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            
            if executed_only:
                query += " AND was_executed = 1"
            
            query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cursor = conn.execute(query, params)
            
            records = []
            for row in cursor.fetchall():
                records.append(AuditRecord.from_dict(json.loads(row[0])))
            
            return records
        finally:
            conn.close()
    
    async def replay(self, record_id: str) -> Optional[ReplayResult]:
        """
        Replay a historical cycle with current logic.
        
        This re-runs the thought engine with the stored inputs
        to verify deterministic behavior.
        """
        record = await self.get_record(record_id)
        if not record or not record.inputs:
            logger.warning(f"Cannot replay record {record_id}: not found or no inputs")
            return None
        
        from chatos_backend.services.thought_engine import ThoughtEngine, ThoughtSpec
        from chatos_backend.services.decision_arbiter import DecisionArbiter
        
        engine = ThoughtEngine()
        arbiter = DecisionArbiter()
        
        specs = [
            ThoughtSpec(**spec)
            for spec in record.inputs.thought_specs
        ]
        
        if not specs:
            specs = engine.create_default_specs(record.inputs.symbol)
        
        thoughts = await engine.run_parallel_thoughts(specs)
        
        decision = await arbiter.reconcile(thoughts)
        
        result = ReplayResult(
            original_record=record,
            replayed_thoughts=[t.to_dict() for t in thoughts],
            replayed_decision=decision.to_dict(),
        )
        
        if record.arbiter_decision:
            original_action = record.arbiter_decision.get("action")
            replayed_action = decision.action.value
            result.decision_matches = original_action == replayed_action
            
            if not result.decision_matches:
                result.differences.append(
                    f"Action changed: {original_action} -> {replayed_action}"
                )
        
        record.replay_count += 1
        record.last_replayed_at = datetime.now(timezone.utc)
        record.replay_matches = result.decision_matches
        await self._persist(record)
        
        await self.event_bus.publish(
            "audit.replayed",
            {
                "record_id": record.id,
                "cycle_id": record.cycle_id,
                "matches": result.decision_matches,
            },
            source="audit_trail"
        )
        
        return result
    
    def _get_model_versions(self) -> Dict[str, str]:
        """Get current model versions."""
        return {
            "thought_engine": "1.0.0",
            "decision_arbiter": "1.0.0",
            "risk_manager": "1.0.0",
        }
    
    def _get_config_hash(self) -> str:
        """Get hash of current configuration."""
        config = {
            "thought_engine_version": "1.0.0",
            "filters": ["orderflow", "regime", "performance"],
        }
        return hashlib.sha256(
            json.dumps(config, sort_keys=True).encode()
        ).hexdigest()[:16]
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get audit trail statistics."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM audit_records")
            total = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM audit_records WHERE was_executed = 1")
            executed = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT symbol, COUNT(*) as cnt 
                FROM audit_records 
                GROUP BY symbol 
                ORDER BY cnt DESC 
                LIMIT 5
            """)
            top_symbols = [{"symbol": row[0], "count": row[1]} for row in cursor.fetchall()]
            
            return {
                "total_records": total,
                "executed_count": executed,
                "execution_rate": executed / total if total > 0 else 0,
                "top_symbols": top_symbols,
            }
        finally:
            conn.close()


_audit_trail: Optional[AuditTrail] = None


def get_audit_trail() -> AuditTrail:
    """Get the audit trail singleton."""
    global _audit_trail
    if _audit_trail is None:
        _audit_trail = AuditTrail()
    return _audit_trail
