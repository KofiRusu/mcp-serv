"""
Thought-Lines API Routes

FastAPI endpoints for the thought-line processing system, providing:
- DAG manifest for UI visualization
- Thought execution endpoints
- Real-time status streaming via WebSocket
- Audit trail access and replay
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from chatos_backend.core.event_bus import get_event_bus, Event
from chatos_backend.services.thought_engine import (
    ThoughtEngine, ThoughtSpec, ThoughtRun, ThoughtStatus,
    get_thought_engine
)
from chatos_backend.services.decision_arbiter import (
    DecisionArbiter, ArbiterDecision,
    get_arbiter
)
from chatos_backend.services.risk_manager import get_risk_manager
from chatos_backend.services.execution import get_execution_router, TradingMode
from chatos_backend.services.audit_trail import get_audit_trail
from chatos_backend.services.historical_context import get_context_builder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/thought-lines", tags=["thought-lines"])


class DAGNode(BaseModel):
    id: str
    type: str
    label: str
    status: str = "idle"
    x: float = 0
    y: float = 0


class DAGEdge(BaseModel):
    id: str
    source: str
    target: str
    animated: bool = False


class DAGManifest(BaseModel):
    nodes: List[DAGNode]
    edges: List[DAGEdge]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ThoughtSpecRequest(BaseModel):
    name: str = "custom_thought"
    symbol: str = "BTCUSDT"
    hypothesis: str = ""
    required_contexts: List[str] = ["A", "B", "C"]
    timeout_ms: int = 30000


class ExecuteCycleRequest(BaseModel):
    symbol: str = "BTCUSDT"
    thought_specs: Optional[List[ThoughtSpecRequest]] = None
    mode: str = "paper"


class ExecuteCycleResponse(BaseModel):
    cycle_id: str
    symbol: str
    thoughts: List[Dict[str, Any]]
    arbiter_decision: Dict[str, Any]
    risk_result: Dict[str, Any]
    execution_result: Optional[Dict[str, Any]] = None
    audit_record_id: str
    duration_ms: float


@router.get("/dag", response_model=DAGManifest)
async def get_dag_manifest() -> DAGManifest:
    """Return the DAG structure for UI visualization."""
    nodes = [
        DAGNode(id="live_feed", type="input", label="Live Market Feed", x=50, y=150),
        
        DAGNode(id="thought_trend", type="thought", label="Trend Following", x=200, y=50),
        DAGNode(id="thought_mean_rev", type="thought", label="Mean Reversion", x=200, y=150),
        DAGNode(id="thought_momentum", type="thought", label="Momentum", x=200, y=250),
        
        DAGNode(id="filter_a", type="filter", label="Filter A: Orderflow", x=400, y=100),
        DAGNode(id="filter_b", type="filter", label="Filter B: Regime", x=400, y=200),
        DAGNode(id="filter_c", type="filter", label="Filter C: Performance", x=400, y=300),
        
        DAGNode(id="arbiter", type="arbiter", label="Decision Arbiter", x=600, y=150),
        DAGNode(id="risk", type="risk", label="Risk Manager", x=750, y=150),
        DAGNode(id="execution", type="execution", label="Execution", x=900, y=150),
        DAGNode(id="audit", type="audit", label="Audit Trail", x=1050, y=150),
    ]
    
    edges = [
        DAGEdge(id="e1", source="live_feed", target="thought_trend"),
        DAGEdge(id="e2", source="live_feed", target="thought_mean_rev"),
        DAGEdge(id="e3", source="live_feed", target="thought_momentum"),
        
        DAGEdge(id="e4", source="thought_trend", target="filter_a"),
        DAGEdge(id="e5", source="thought_mean_rev", target="filter_a"),
        DAGEdge(id="e6", source="thought_momentum", target="filter_a"),
        
        DAGEdge(id="e7", source="filter_a", target="filter_b"),
        DAGEdge(id="e8", source="filter_b", target="filter_c"),
        DAGEdge(id="e9", source="filter_c", target="arbiter"),
        DAGEdge(id="e10", source="arbiter", target="risk"),
        DAGEdge(id="e11", source="risk", target="execution"),
        DAGEdge(id="e12", source="execution", target="audit"),
    ]
    
    return DAGManifest(nodes=nodes, edges=edges)


@router.post("/execute", response_model=ExecuteCycleResponse)
async def execute_cycle(request: ExecuteCycleRequest) -> ExecuteCycleResponse:
    """Execute a complete thought-line cycle."""
    import time
    start_time = time.time()
    
    engine = get_thought_engine()
    arbiter = get_arbiter()
    risk_manager = get_risk_manager()
    execution_router = get_execution_router()
    audit_trail = get_audit_trail()
    context_builder = get_context_builder()
    
    if request.mode == "live":
        execution_router.set_mode(TradingMode.LIVE)
    else:
        execution_router.set_mode(TradingMode.PAPER)
    
    if request.thought_specs:
        specs = [
            ThoughtSpec(
                name=ts.name,
                symbol=request.symbol,
                hypothesis=ts.hypothesis,
                required_contexts=ts.required_contexts,
                timeout_ms=ts.timeout_ms,
            )
            for ts in request.thought_specs
        ]
    else:
        specs = engine.create_default_specs(request.symbol)
    
    thoughts = await engine.run_parallel_thoughts(specs)
    
    decision = await arbiter.reconcile(thoughts)
    
    balance = await execution_router.get_balance()
    risk_result = await risk_manager.validate_decision(decision, balance)
    
    execution_result = None
    if risk_result.approved and decision.action.value not in ["HOLD", "CONFLICT"]:
        execution_result = await execution_router.execute(decision, risk_result)
    
    context_a = thoughts[0].context_a if thoughts else None
    context_b = thoughts[0].context_b if thoughts else None
    context_c = thoughts[0].context_c if thoughts else None
    
    audit_record = await audit_trail.record_cycle(
        thoughts=thoughts,
        arbiter_decision=decision,
        risk_result=risk_result,
        execution_result=execution_result,
        context_a=context_a,
        context_b=context_b,
        context_c=context_c,
    )
    
    duration_ms = (time.time() - start_time) * 1000
    
    return ExecuteCycleResponse(
        cycle_id=audit_record.cycle_id,
        symbol=request.symbol,
        thoughts=[t.to_dict() for t in thoughts],
        arbiter_decision=decision.to_dict(),
        risk_result=risk_result.to_dict(),
        execution_result=execution_result.to_dict() if execution_result else None,
        audit_record_id=audit_record.id,
        duration_ms=duration_ms,
    )


@router.get("/thoughts/{thought_id}")
async def get_thought_trace(thought_id: str) -> Dict[str, Any]:
    """Get detailed trace for a specific thought."""
    engine = get_thought_engine()
    
    if thought_id in engine.active_thoughts:
        return engine.active_thoughts[thought_id].to_dict()
    
    raise HTTPException(status_code=404, detail=f"Thought {thought_id} not found")


@router.get("/audit")
async def list_audit_records(
    symbol: Optional[str] = None,
    executed_only: bool = False,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
) -> Dict[str, Any]:
    """List audit records with optional filtering."""
    audit_trail = get_audit_trail()
    records = await audit_trail.get_records(
        symbol=symbol,
        executed_only=executed_only,
        limit=limit,
        offset=offset,
    )
    
    return {
        "records": [r.to_dict() for r in records],
        "count": len(records),
        "limit": limit,
        "offset": offset,
    }


@router.get("/audit/stats")
async def get_audit_stats() -> Dict[str, Any]:
    """Get audit trail statistics."""
    audit_trail = get_audit_trail()
    return await audit_trail.get_stats()


@router.get("/audit/{record_id}")
async def get_audit_record(record_id: str) -> Dict[str, Any]:
    """Get a specific audit record."""
    audit_trail = get_audit_trail()
    record = await audit_trail.get_record(record_id)
    
    if not record:
        raise HTTPException(status_code=404, detail=f"Record {record_id} not found")
    
    return record.to_dict()


@router.post("/audit/{record_id}/replay")
async def replay_audit_record(record_id: str) -> Dict[str, Any]:
    """Replay a historical cycle with current logic."""
    audit_trail = get_audit_trail()
    result = await audit_trail.replay(record_id)
    
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Record {record_id} not found or cannot be replayed"
        )
    
    return result.to_dict()


@router.get("/risk/status")
async def get_risk_status() -> Dict[str, Any]:
    """Get current risk manager status."""
    risk_manager = get_risk_manager()
    return risk_manager.get_status()


@router.post("/risk/kill-switch/reset")
async def reset_kill_switch(admin_key: str) -> Dict[str, Any]:
    """Reset the kill switch (requires admin key)."""
    expected_key = "chatos_admin_2024"
    
    if admin_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    risk_manager = get_risk_manager()
    success = await risk_manager.reset_kill_switch(admin_override=True)
    
    return {"success": success}


@router.get("/execution/status")
async def get_execution_status() -> Dict[str, Any]:
    """Get current execution status."""
    router = get_execution_router()
    
    positions = await router.get_positions()
    balance = await router.get_balance()
    
    return {
        "mode": router.mode.value,
        "balance": balance,
        "positions": positions,
        "position_count": len(positions),
    }


@router.websocket("/ws/status")
async def thought_status_stream(websocket: WebSocket):
    """Stream real-time thought execution status via WebSocket."""
    await websocket.accept()
    
    event_bus = get_event_bus()
    event_queue: asyncio.Queue = asyncio.Queue()
    
    async def event_handler(event: Event):
        await event_queue.put(event)
    
    event_bus.subscribe("thought.*", event_handler)
    event_bus.subscribe("filter.*", event_handler)
    event_bus.subscribe("execution.*", event_handler)
    event_bus.subscribe("risk.*", event_handler)
    event_bus.subscribe("audit.*", event_handler)
    
    try:
        await websocket.send_json({
            "type": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        while True:
            try:
                event = await asyncio.wait_for(event_queue.get(), timeout=30.0)
                
                await websocket.send_json({
                    "type": "event",
                    "event_type": event.event_type,
                    "payload": event.payload,
                    "timestamp": event.timestamp.isoformat(),
                })
                
            except asyncio.TimeoutError:
                await websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    finally:
        event_bus.unsubscribe("thought.*", event_handler)
        event_bus.unsubscribe("filter.*", event_handler)
        event_bus.unsubscribe("execution.*", event_handler)
        event_bus.unsubscribe("risk.*", event_handler)
        event_bus.unsubscribe("audit.*", event_handler)


@router.get("/contexts/{symbol}")
async def get_contexts(symbol: str) -> Dict[str, Any]:
    """Get current contexts A/B/C for a symbol."""
    context_builder = get_context_builder()
    
    context_a, context_b, context_c = await context_builder.build_all_contexts(symbol)
    
    return {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "context_a": context_a.to_dict(),
        "context_b": context_b.to_dict(),
        "context_c": context_c.to_dict(),
    }


@router.get("/health")
async def thought_lines_health() -> Dict[str, Any]:
    """Health check for thought-lines system."""
    event_bus = get_event_bus()
    engine = get_thought_engine()
    risk_manager = get_risk_manager()
    
    return {
        "status": "healthy",
        "components": {
            "event_bus": "running" if event_bus._running else "stopped",
            "thought_engine": "ready",
            "risk_manager": "active" if not risk_manager._kill_switch_active else "kill_switch_active",
        },
        "active_thoughts": len(engine.active_thoughts),
        "event_bus_metrics": event_bus.get_metrics(),
    }
