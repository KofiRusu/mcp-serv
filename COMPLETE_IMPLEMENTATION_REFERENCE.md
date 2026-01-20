# ChatOS Thought-Line Processing - COMPLETE IMPLEMENTATION REFERENCE

## Implementation Summary

This document contains all the critical information needed to continue or verify the ChatOS thought-line processing system implementation.

---

## COMPLETED BACKEND FILES

### 1. Core Module
**`/chatos_backend/core/__init__.py`**
```python
from chatos_backend.core.event_bus import EventBus, get_event_bus, Event
__all__ = ["EventBus", "get_event_bus", "Event"]
```

**`/chatos_backend/core/event_bus.py`**
- Central pub-sub system with EventBus class
- Event types: market.*, thought.*, filter.*, execution.*, risk.*, audit.*
- Wildcard subscriptions, event history, dead letter queue
- Functions: `get_event_bus()`, `init_event_bus()`, `shutdown_event_bus()`

### 2. Services Created

| File | Purpose |
|------|---------|
| `/chatos_backend/services/model_context_injector.py` | Injects real-time market data into LLM prompts |
| `/chatos_backend/services/scraper_sync_service.py` | Syncs scraper output to RealtimeDataStore |
| `/chatos_backend/services/historical_context.py` | ContextA/B/C builders |
| `/chatos_backend/services/thought_engine.py` | ThoughtSpec, ThoughtRun, FilterA/B/C, ThoughtEngine |
| `/chatos_backend/services/decision_arbiter.py` | ArbiterDecision, DecisionArbiter |
| `/chatos_backend/services/risk_manager.py` | RiskLimits, RiskManager, kill switches |
| `/chatos_backend/services/execution.py` | PaperExecutor, HyperliquidExecutor, ExecutionRouter |
| `/chatos_backend/services/audit_trail.py` | AuditRecord, AuditTrail, replay system |

### 3. Database Models
**`/chatos_backend/database/trading_history_models.py`**

Tables for Historical Data Types:
- **Type A (Orderflow)**: OrderflowSnapshot, LiquidationEvent, FundingRate, OpenInterest
- **Type B (Regime)**: RegimeClassification, VolatilitySnapshot, CorrelationMatrix, DrawdownTracker
- **Type C (Performance)**: TradingDecisionLog, TradeOutcome, RiskBreach, ModelConfidenceCalibration
- **Traces**: ThoughtTrace, AuditRecord

### 4. API Routes
**`/chatos_backend/api/routes_thought_lines.py`**

Endpoints:
- `GET /api/thought-lines/dag` - DAG manifest
- `POST /api/thought-lines/execute` - Execute cycle
- `GET /api/thought-lines/thoughts/{id}` - Get thought trace
- `GET /api/thought-lines/audit` - List records
- `GET /api/thought-lines/audit/stats` - Statistics
- `GET /api/thought-lines/audit/{id}` - Get record
- `POST /api/thought-lines/audit/{id}/replay` - Replay
- `GET /api/thought-lines/risk/status` - Risk status
- `POST /api/thought-lines/risk/kill-switch/reset` - Reset kill switch
- `GET /api/thought-lines/execution/status` - Execution status
- `WS /api/thought-lines/ws/status` - Real-time WebSocket
- `GET /api/thought-lines/contexts/{symbol}` - Get A/B/C contexts
- `GET /api/thought-lines/health` - Health check

---

## MODIFIED FILES

### app.py Changes

1. Added import at line 103:
```python
from chatos_backend.api.routes_thought_lines import router as thought_lines_router
```

2. Modified lifespan() (lines 109-171):
- Added EventBus initialization via `init_event_bus()`
- Added ScraperSyncService startup via `start_scraper_sync()`
- Added cleanup in shutdown

3. Added router registration at line 230:
```python
app.include_router(thought_lines_router)
```

---

## REMAINING TASKS

### 1. Frontend UI Components (Phase 8)
Create in `/frontend/src/components/trading/thought-network/`:

```
thought-network/
├── thought-network-panel.tsx      # Main container
├── dag-canvas.tsx                 # React Flow visualization
├── thought-node.tsx               # Thought block component
├── filter-node.tsx                # Filter with PASS/WARN/BLOCK
├── connection-line.tsx            # Animated connections
├── status-indicator.tsx           # Per-node status
├── execution-log.tsx              # Real-time trace
├── thought-network-store.ts       # Zustand store
└── index.ts                       # Exports
```

### 2. Trading Page Integration
Modify `/frontend/src/app/trading/page.tsx`:
- Import ThoughtNetworkPanel
- Add to bottom of layout above BottomBar

### 3. Validation Test Suite (Phase 9)
Create `/tests/integration/test_thought_lines.py` with tests for:
- Data ingestion pipeline
- Context builders A/B/C
- Thought execution through filters
- Arbiter reconciliation
- Risk checks
- Paper/Live execution
- Audit trail and replay
- WebSocket streaming

---

## KEY SINGLETON FUNCTIONS

```python
from chatos_backend.core.event_bus import get_event_bus
from chatos_backend.services.thought_engine import get_thought_engine
from chatos_backend.services.decision_arbiter import get_arbiter
from chatos_backend.services.risk_manager import get_risk_manager
from chatos_backend.services.execution import get_execution_router
from chatos_backend.services.audit_trail import get_audit_trail
from chatos_backend.services.historical_context import get_context_builder
from chatos_backend.services.realtime_data_store import get_realtime_store
```

---

## TESTING THE SYSTEM

### Quick API Test
```bash
# Health check
curl http://localhost:8000/api/thought-lines/health

# Execute a cycle
curl -X POST http://localhost:8000/api/thought-lines/execute \
  -H "Content-Type: application/json" \
  -d '{"symbol": "BTCUSDT", "mode": "paper"}'

# Get DAG manifest
curl http://localhost:8000/api/thought-lines/dag

# Get contexts
curl http://localhost:8000/api/thought-lines/contexts/BTCUSDT

# List audit records
curl http://localhost:8000/api/thought-lines/audit?limit=10
```

### WebSocket Test
```javascript
const ws = new WebSocket('ws://localhost:8000/api/thought-lines/ws/status');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

---

## ARCHITECTURE FLOW

```
Scrapers (AGGR, CoinGlass) → ScraperSyncService → EventBus → RealtimeDataStore
                                                      ↓
                                              HistoricalContextBuilder
                                                      ↓
User Request → ThoughtEngine → [ThoughtRun] → Filters A/B/C → DecisionArbiter
                                                                    ↓
                                                              RiskManager
                                                                    ↓
                                                            ExecutionRouter
                                                                    ↓
                                                              AuditTrail
                                                                    ↓
                                                              WebSocket UI
```

---

## ENVIRONMENT VARIABLES

```bash
SCRAPED_DATA_DIR=~/ChatOS-Data/scraped
REALTIME_DATA_DIR=~/ChatOS-Data/realtime
OLLAMA_HOST=http://localhost:11434
```

---

## SUCCESS CRITERIA

The system is "READY FOR LIVE" when:
1. ✅ All scrapers producing real data
2. ✅ Context A/B/C builders return valid data
3. ✅ Thoughts traverse all filters correctly
4. ✅ Arbiter produces consistent decisions
5. ✅ Risk checks properly block dangerous decisions
6. ✅ Paper trading executes correctly
7. ✅ Hyperliquid testnet integration works
8. ✅ Audit trail records all cycles
9. ✅ Replay produces deterministic results
10. ✅ UI shows real-time status updates
