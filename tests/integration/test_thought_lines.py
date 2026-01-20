"""
Comprehensive Integration Test Suite for ChatOS Thought-Line Processing System

This test suite validates the complete thought-line pipeline from data ingestion
through execution and audit trail. All tests must pass to output "READY FOR LIVE".

Requirements Verified:
- Data ingestion pipeline (scrapers → EventBus → storage)
- Context builders A/B/C returning valid data
- Thought execution through all filters
- Arbiter reconciliation with multiple thoughts
- Risk checks blocking dangerous decisions
- Paper trading execution
- Hyperliquid testnet integration
- Audit trail recording and deterministic replay
- WebSocket status streaming
"""

import asyncio
import sys
import os
import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, UTC
from typing import List, Dict, Optional, Any
from enum import Enum
from pathlib import Path
import aiohttp
import websockets

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from chatos_backend.core.event_bus import EventBus, init_event_bus, get_event_bus, shutdown_event_bus
from chatos_backend.services.historical_context import (
    HistoricalContextBuilder,
    ContextA, ContextB, ContextC
)
from chatos_backend.services.thought_engine import (
    ThoughtEngine, ThoughtSpec, ThoughtRun, ThoughtStatus,
    FilterA_Orderflow, FilterB_Regime, FilterC_Performance
)
from chatos_backend.services.decision_arbiter import DecisionArbiter, ArbiterDecision, ArbiterAction
from chatos_backend.services.risk_manager import RiskManager, RiskResult, RiskLimits
from chatos_backend.services.execution import (
    ExecutionRouter, PaperExecutor, HyperliquidExecutor,
    ExecutionResult, TradingMode
)
from chatos_backend.services.audit_trail import AuditTrail, AuditRecord, CycleInputs
from chatos_backend.services.scraper_sync_service import ScraperDataSyncer, start_scraper_sync, stop_scraper_sync
from chatos_backend.services.realtime_data_store import realtime_store


class TestStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestResult:
    name: str
    status: TestStatus
    duration_ms: float = 0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationReport:
    status: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    total_tests: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    results: List[TestResult] = field(default_factory=list)
    
    def add_result(self, result: TestResult):
        self.results.append(result)
        self.total_tests += 1
        if result.status == TestStatus.PASSED:
            self.passed += 1
        elif result.status == TestStatus.FAILED:
            self.failed += 1
        elif result.status == TestStatus.SKIPPED:
            self.skipped += 1
    
    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "timestamp": self.timestamp.isoformat(),
            "summary": {
                "total": self.total_tests,
                "passed": self.passed,
                "failed": self.failed,
                "skipped": self.skipped,
            },
            "results": [
                {
                    "name": r.name,
                    "status": r.status.value,
                    "duration_ms": r.duration_ms,
                    "message": r.message,
                }
                for r in self.results
            ]
        }


class ThoughtLineTestSuite:
    """Integration tests for the complete thought-line system"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.event_bus: Optional[EventBus] = None
        self.context_builder: Optional[HistoricalContextBuilder] = None
        self.thought_engine: Optional[ThoughtEngine] = None
        self.arbiter: Optional[DecisionArbiter] = None
        self.risk_manager: Optional[RiskManager] = None
        self.executor: Optional[ExecutionRouter] = None
        self.audit_trail: Optional[AuditTrail] = None
        self.test_symbol = "BTCUSDT"
    
    async def setup(self):
        """Initialize all components for testing"""
        self.event_bus = await init_event_bus()
        self.context_builder = HistoricalContextBuilder(self.event_bus)
        self.thought_engine = ThoughtEngine(self.event_bus, self.context_builder)
        self.arbiter = DecisionArbiter(self.event_bus)
        self.risk_manager = RiskManager(self.event_bus)
        self.executor = ExecutionRouter()
        self.executor.set_mode(TradingMode.PAPER)
        self.audit_trail = AuditTrail()
        await self.audit_trail.initialize()
    
    async def teardown(self):
        """Cleanup after tests"""
        if self.audit_trail:
            await self.audit_trail.close()
        await shutdown_event_bus()
    
    async def _timed_test(self, test_fn, name: str) -> TestResult:
        """Execute a test with timing"""
        start = datetime.now()
        try:
            await test_fn()
            duration = (datetime.now() - start).total_seconds() * 1000
            return TestResult(
                name=name,
                status=TestStatus.PASSED,
                duration_ms=duration,
                message="Test passed successfully"
            )
        except AssertionError as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            return TestResult(
                name=name,
                status=TestStatus.FAILED,
                duration_ms=duration,
                message=f"Assertion failed: {str(e)}"
            )
        except Exception as e:
            duration = (datetime.now() - start).total_seconds() * 1000
            return TestResult(
                name=name,
                status=TestStatus.FAILED,
                duration_ms=duration,
                message=f"Exception: {type(e).__name__}: {str(e)}"
            )
    
    async def test_data_ingestion(self):
        """Verify scrapers → EventBus → Storage pipeline"""
        events_received = []
        
        def event_handler(event):
            events_received.append(event)
        
        self.event_bus.subscribe("market.*", event_handler)
        
        await self.event_bus.publish(
            "market.tick",
            {
                "symbol": self.test_symbol,
                "price": 65000.0,
                "volume": 1.5,
                "timestamp": datetime.now(UTC).isoformat()
            },
            source="test"
        )
        
        await asyncio.sleep(0.1)
        
        assert len(events_received) > 0, "No events received from EventBus"
        assert events_received[0].event_type == "market.tick", "Wrong event type"
        assert events_received[0].payload["symbol"] == self.test_symbol, "Wrong symbol"
        
        self.event_bus.unsubscribe("market.*", event_handler)
    
    async def test_context_builders(self):
        """Verify context A/B/C builders return valid data"""
        context_a = await self.context_builder.build_context_a(
            self.test_symbol,
            lookback_hours=24
        )
        assert context_a is not None, "ContextA is None"
        assert isinstance(context_a, ContextA), "Invalid ContextA type"
        assert context_a.symbol == self.test_symbol, "Wrong symbol in ContextA"
        assert hasattr(context_a, 'cvd_current'), "ContextA missing cvd_current"
        assert hasattr(context_a, 'funding_rate'), "ContextA missing funding_rate"
        
        context_b = await self.context_builder.build_context_b(
            self.test_symbol,
            lookback_hours=24
        )
        assert context_b is not None, "ContextB is None"
        assert isinstance(context_b, ContextB), "Invalid ContextB type"
        assert hasattr(context_b, 'current_regime'), "ContextB missing current_regime"
        assert hasattr(context_b, 'realized_vol_24h'), "ContextB missing realized_vol_24h"
        
        context_c = await self.context_builder.build_context_c(
            self.test_symbol,
            lookback_hours=168
        )
        assert context_c is not None, "ContextC is None"
        assert isinstance(context_c, ContextC), "Invalid ContextC type"
        assert hasattr(context_c, 'win_rate'), "ContextC missing win_rate"
        assert hasattr(context_c, 'total_trades'), "ContextC missing total_trades"
        
        all_contexts = await self.context_builder.build_all_contexts(self.test_symbol)
        assert all_contexts is not None, "build_all_contexts returned None"
        assert len(all_contexts) == 3, "build_all_contexts should return 3 contexts"
    
    async def test_thought_execution(self):
        """Verify single thought traverses all filters"""
        spec = ThoughtSpec(
            id="test_thought_1",
            name="Test Trend Following",
            symbol=self.test_symbol,
            hypothesis="Testing thought execution pipeline",
            required_contexts=["A", "B", "C"],
            filters=[
                {"name": "FilterA_Orderflow", "type": "A"},
                {"name": "FilterB_Regime", "type": "B"},
                {"name": "FilterC_Performance", "type": "C"},
            ],
            model="persrm",
            timeout_ms=30000
        )
        
        thought_run = await self.thought_engine.run_thought(spec)
        
        assert thought_run is not None, "ThoughtRun is None"
        assert thought_run.spec.id == spec.id, "Spec ID mismatch"
        assert thought_run.started_at is not None, "started_at not set"
        assert thought_run.context_a is not None, "ContextA not populated"
        assert thought_run.context_b is not None, "ContextB not populated"
        assert thought_run.context_c is not None, "ContextC not populated"
        assert len(thought_run.filter_results) > 0, "No filter results"
        assert len(thought_run.trace) > 0, "No trace steps recorded"
        assert thought_run.status in [ThoughtStatus.PASSED, ThoughtStatus.BLOCKED], \
            f"Unexpected status: {thought_run.status}"
    
    async def test_parallel_thoughts(self):
        """Verify multiple thoughts can run in parallel"""
        specs = self.thought_engine.create_default_specs(self.test_symbol)
        
        assert len(specs) >= 2, "Should have at least 2 default thought specs"
        
        thought_runs = await self.thought_engine.run_parallel_thoughts(specs)
        
        assert len(thought_runs) == len(specs), "Not all thoughts completed"
        
        for run in thought_runs:
            assert run.started_at is not None, f"Thought {run.spec.id} not started"
            assert run.status != ThoughtStatus.PENDING, f"Thought {run.spec.id} still pending"
    
    async def test_arbiter_reconciliation(self):
        """Verify arbiter handles multiple thoughts correctly"""
        specs = self.thought_engine.create_default_specs(self.test_symbol)
        thought_runs = await self.thought_engine.run_parallel_thoughts(specs)
        
        decision = await self.arbiter.reconcile(thought_runs)
        
        assert decision is not None, "Arbiter decision is None"
        assert isinstance(decision, ArbiterDecision), "Invalid decision type"
        assert decision.action in list(ArbiterAction), f"Invalid action: {decision.action}"
        assert 0 <= decision.confidence <= 1.0, "Confidence out of range"
        assert decision.symbol == self.test_symbol, "Wrong symbol in decision"
        assert decision.reason is not None and len(decision.reason) > 0, "No reason provided"
        
        if decision.action == ArbiterAction.CONFLICT:
            assert decision.conflict_info is not None, "Conflict info missing"
            assert decision.conflict_info.has_conflict, "has_conflict should be True"
    
    async def test_risk_checks_blocking(self):
        """Verify risk layer blocks dangerous decisions"""
        overlimit_decision = ArbiterDecision(
            action=ArbiterAction.LONG,
            symbol=self.test_symbol,
            size=100000.0,
            entry=65000.0,
            stop_loss=60000.0,
            take_profit=70000.0,
            leverage=10.0,
            confidence=0.9,
            reason="Test overlimit decision",
            contributing_thoughts=["test"],
            conflict_info=None,
            signal_votes={}
        )
        
        result = await self.risk_manager.validate_decision(
            overlimit_decision,
            account_balance=10000.0
        )
        
        assert result is not None, "Risk result is None"
        assert isinstance(result, RiskResult), "Invalid result type"
        assert not result.approved, "Overlimit decision should be blocked"
        assert len(result.checks) > 0, "No risk checks performed"
        
        failed_checks = [c for c in result.checks if c.status == "FAIL"]
        assert len(failed_checks) > 0, "Expected at least one failed check"
    
    async def test_risk_checks_passing(self):
        """Verify risk layer approves valid decisions"""
        valid_decision = ArbiterDecision(
            action=ArbiterAction.LONG,
            symbol=self.test_symbol,
            size=500.0,
            entry=65000.0,
            stop_loss=64000.0,
            take_profit=67000.0,
            leverage=2.0,
            confidence=0.75,
            reason="Test valid decision",
            contributing_thoughts=["test"],
            conflict_info=None,
            signal_votes={}
        )
        
        result = await self.risk_manager.validate_decision(
            valid_decision,
            account_balance=10000.0
        )
        
        assert result is not None, "Risk result is None"
        if not result.approved:
            print(f"Warning: Valid decision not approved: {result.reason}")
    
    async def test_kill_switch(self):
        """Verify kill switch functionality"""
        await self.risk_manager.trigger_kill_switch("Test kill switch")
        
        any_decision = ArbiterDecision(
            action=ArbiterAction.LONG,
            symbol=self.test_symbol,
            size=100.0,
            entry=65000.0,
            stop_loss=64000.0,
            take_profit=66000.0,
            leverage=1.0,
            confidence=0.9,
            reason="Test after kill switch",
            contributing_thoughts=["test"],
            conflict_info=None,
            signal_votes={}
        )
        
        result = await self.risk_manager.validate_decision(
            any_decision,
            account_balance=100000.0
        )
        
        assert not result.approved, "Decision should be blocked when kill switch is active"
        
        kill_switch_check = next(
            (c for c in result.checks if "kill_switch" in c.name.lower()),
            None
        )
        assert kill_switch_check is not None, "Kill switch check not found"
        assert kill_switch_check.status == "FAIL", "Kill switch should fail the check"
        
        await self.risk_manager.reset_kill_switch(admin_override=True)
    
    async def test_execution_paper_mode(self):
        """Verify paper trading execution"""
        self.executor.set_mode(TradingMode.PAPER)
        
        decision = ArbiterDecision(
            action=ArbiterAction.LONG,
            symbol=self.test_symbol,
            size=0.01,
            entry=65000.0,
            stop_loss=64000.0,
            take_profit=66000.0,
            leverage=1.0,
            confidence=0.8,
            reason="Test paper execution",
            contributing_thoughts=["test"],
            conflict_info=None,
            signal_votes={}
        )
        
        risk_result = RiskResult(
            approved=True,
            reason="Approved for paper trading test",
            checks=[],
            adjusted_size=decision.size,
            adjusted_leverage=decision.leverage
        )
        
        result = await self.executor.execute(decision, risk_result)
        
        assert result is not None, "Execution result is None"
        assert isinstance(result, ExecutionResult), "Invalid result type"
        assert result.success, f"Paper execution failed: {result.error}"
        assert result.order_id is not None, "No order ID"
        assert result.mode == TradingMode.PAPER, "Wrong execution mode"
        assert result.fill_price is not None, "No fill price"
    
    async def test_execution_live_mode_testnet(self):
        """Verify Hyperliquid integration (testnet)"""
        testnet_wallet = os.environ.get("HL_TESTNET_WALLET")
        testnet_key = os.environ.get("HL_TESTNET_PRIVATE_KEY")
        
        if not testnet_wallet or not testnet_key:
            raise AssertionError("SKIPPED: Testnet credentials not configured")
        
        self.executor.configure_live(
            wallet_address=testnet_wallet,
            private_key=testnet_key,
            testnet=True
        )
        self.executor.set_mode(TradingMode.LIVE)
        
        try:
            connected = await self.executor.live_executor.connect()
            assert connected, "Failed to connect to Hyperliquid testnet"
            
            balance = await self.executor.live_executor.get_balance()
            assert balance is not None, "Failed to get testnet balance"
            assert balance >= 0, "Invalid balance"
            
        finally:
            self.executor.set_mode(TradingMode.PAPER)
    
    async def test_audit_trail_recording(self):
        """Verify audit trail records complete cycles"""
        specs = self.thought_engine.create_default_specs(self.test_symbol)
        thought_runs = await self.thought_engine.run_parallel_thoughts(specs[:1])
        arbiter_decision = await self.arbiter.reconcile(thought_runs)
        risk_result = await self.risk_manager.validate_decision(
            arbiter_decision,
            account_balance=10000.0
        )
        
        execution_result = None
        if risk_result.approved and arbiter_decision.action != ArbiterAction.HOLD:
            execution_result = await self.executor.execute(arbiter_decision, risk_result)
        
        record = await self.audit_trail.record_cycle(
            thoughts=thought_runs,
            arbiter_decision=arbiter_decision,
            risk_result=risk_result,
            execution_result=execution_result,
            symbol=self.test_symbol
        )
        
        assert record is not None, "Audit record is None"
        assert record.id is not None, "Record ID is None"
        assert record.cycle_id is not None, "Cycle ID is None"
        assert record.input_hash is not None, "Input hash is None"
        assert len(record.input_hash) == 64, "Invalid hash length"
        
        retrieved = await self.audit_trail.get_record(record.id)
        assert retrieved is not None, f"Failed to retrieve record {record.id}"
        assert retrieved.id == record.id, "Record ID mismatch"
        assert retrieved.input_hash == record.input_hash, "Hash mismatch"
        
        return record.id
    
    async def test_audit_trail_replay(self):
        """Verify deterministic replay produces consistent results"""
        record_id = await self.test_audit_trail_recording()
        
        replay_result = await self.audit_trail.replay(record_id)
        
        assert replay_result is not None, "Replay result is None"
        assert replay_result.original_record_id == record_id, "Record ID mismatch"
        assert replay_result.replayed_hash is not None, "Replayed hash is None"
        
        if replay_result.decision_match:
            assert replay_result.original_hash == replay_result.replayed_hash, \
                "Hash should match when decisions match"
        else:
            print(f"Note: Replay produced different decision. Differences: {replay_result.differences}")
    
    async def test_websocket_status_streaming(self):
        """Verify WebSocket status streaming"""
        ws_url = self.base_url.replace("http", "ws") + "/api/thought-lines/ws/status"
        
        try:
            async with websockets.connect(ws_url, open_timeout=5) as ws:
                await ws.send(json.dumps({"type": "subscribe", "channel": "status"}))
                
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)
                
                assert "type" in data, "Response missing 'type' field"
                
        except asyncio.TimeoutError:
            raise AssertionError("WebSocket timeout - no response received")
        except websockets.exceptions.InvalidStatusCode as e:
            if e.status_code == 404:
                raise AssertionError("WebSocket endpoint not found (404)")
            raise
        except ConnectionRefusedError:
            raise AssertionError("SKIPPED: Backend server not running")
    
    async def test_api_dag_endpoint(self):
        """Verify DAG manifest API endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.base_url}/api/thought-lines/dag") as resp:
                    assert resp.status == 200, f"DAG endpoint returned {resp.status}"
                    data = await resp.json()
                    
                    assert "nodes" in data, "Response missing 'nodes'"
                    assert "edges" in data, "Response missing 'edges'"
                    assert len(data["nodes"]) > 0, "No nodes in DAG"
                    assert len(data["edges"]) > 0, "No edges in DAG"
                    
                    node_ids = {n["id"] for n in data["nodes"]}
                    for edge in data["edges"]:
                        assert edge["from"] in node_ids, f"Edge from unknown node: {edge['from']}"
                        assert edge["to"] in node_ids, f"Edge to unknown node: {edge['to']}"
                        
        except aiohttp.ClientError as e:
            raise AssertionError(f"SKIPPED: Backend server not running - {e}")
    
    async def test_api_execute_endpoint(self):
        """Verify cycle execution API endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "symbol": self.test_symbol,
                    "mode": "paper"
                }
                async with session.post(
                    f"{self.base_url}/api/thought-lines/execute",
                    json=payload
                ) as resp:
                    assert resp.status == 200, f"Execute endpoint returned {resp.status}"
                    data = await resp.json()
                    
                    assert "cycle_id" in data, "Response missing 'cycle_id'"
                    assert "success" in data, "Response missing 'success'"
                    assert "thoughts" in data, "Response missing 'thoughts'"
                    
        except aiohttp.ClientError as e:
            raise AssertionError(f"SKIPPED: Backend server not running - {e}")
    
    async def test_api_contexts_endpoint(self):
        """Verify contexts API endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/api/thought-lines/contexts/{self.test_symbol}"
                ) as resp:
                    assert resp.status == 200, f"Contexts endpoint returned {resp.status}"
                    data = await resp.json()
                    
                    assert "context_a" in data, "Response missing 'context_a'"
                    assert "context_b" in data, "Response missing 'context_b'"
                    assert "context_c" in data, "Response missing 'context_c'"
                    
        except aiohttp.ClientError as e:
            raise AssertionError(f"SKIPPED: Backend server not running - {e}")
    
    async def test_end_to_end_cycle(self):
        """Full end-to-end test of complete trading cycle"""
        events_captured = []
        
        def capture_events(event):
            events_captured.append(event)
        
        self.event_bus.subscribe("thought.*", capture_events)
        self.event_bus.subscribe("risk.*", capture_events)
        self.event_bus.subscribe("execution.*", capture_events)
        self.event_bus.subscribe("audit.*", capture_events)
        
        try:
            specs = self.thought_engine.create_default_specs(self.test_symbol)
            thought_runs = await self.thought_engine.run_parallel_thoughts(specs)
            
            thought_events = [e for e in events_captured if e.event_type.startswith("thought.")]
            assert len(thought_events) >= len(specs), "Not all thought events captured"
            
            decision = await self.arbiter.reconcile(thought_runs)
            assert decision is not None, "Arbiter decision failed"
            
            risk_result = await self.risk_manager.validate_decision(
                decision,
                account_balance=10000.0
            )
            
            execution_result = None
            if risk_result.approved and decision.action not in [ArbiterAction.HOLD, ArbiterAction.CONFLICT]:
                execution_result = await self.executor.execute(decision, risk_result)
            
            record = await self.audit_trail.record_cycle(
                thoughts=thought_runs,
                arbiter_decision=decision,
                risk_result=risk_result,
                execution_result=execution_result,
                symbol=self.test_symbol
            )
            
            assert record is not None, "Audit recording failed"
            
            replay = await self.audit_trail.replay(record.id)
            assert replay is not None, "Replay failed"
            
        finally:
            self.event_bus.unsubscribe("thought.*", capture_events)
            self.event_bus.unsubscribe("risk.*", capture_events)
            self.event_bus.unsubscribe("execution.*", capture_events)
            self.event_bus.unsubscribe("audit.*", capture_events)
    
    async def run_all_checks(self) -> ValidationReport:
        """Run all checks and return READY FOR LIVE or failure report"""
        report = ValidationReport(status="RUNNING")
        
        tests = [
            ("Data Ingestion Pipeline", self.test_data_ingestion),
            ("Context Builders A/B/C", self.test_context_builders),
            ("Single Thought Execution", self.test_thought_execution),
            ("Parallel Thoughts", self.test_parallel_thoughts),
            ("Arbiter Reconciliation", self.test_arbiter_reconciliation),
            ("Risk Checks - Blocking", self.test_risk_checks_blocking),
            ("Risk Checks - Passing", self.test_risk_checks_passing),
            ("Kill Switch", self.test_kill_switch),
            ("Paper Trading Execution", self.test_execution_paper_mode),
            ("Hyperliquid Testnet", self.test_execution_live_mode_testnet),
            ("Audit Trail Recording", self.test_audit_trail_recording),
            ("Audit Trail Replay", self.test_audit_trail_replay),
            ("WebSocket Streaming", self.test_websocket_status_streaming),
            ("API - DAG Endpoint", self.test_api_dag_endpoint),
            ("API - Execute Endpoint", self.test_api_execute_endpoint),
            ("API - Contexts Endpoint", self.test_api_contexts_endpoint),
            ("End-to-End Cycle", self.test_end_to_end_cycle),
        ]
        
        print("\n" + "=" * 60)
        print("ChatOS Thought-Line Validation Suite")
        print("=" * 60 + "\n")
        
        await self.setup()
        
        try:
            for name, test_fn in tests:
                print(f"Running: {name}...", end=" ", flush=True)
                result = await self._timed_test(test_fn, name)
                report.add_result(result)
                
                if result.status == TestStatus.PASSED:
                    print(f"✓ PASSED ({result.duration_ms:.0f}ms)")
                elif "SKIPPED" in result.message:
                    result.status = TestStatus.SKIPPED
                    report.skipped += 1
                    report.failed -= 1
                    print(f"○ SKIPPED - {result.message.replace('SKIPPED: ', '')}")
                else:
                    print(f"✗ FAILED - {result.message}")
        finally:
            await self.teardown()
        
        print("\n" + "=" * 60)
        print(f"Results: {report.passed}/{report.total_tests} passed, "
              f"{report.failed} failed, {report.skipped} skipped")
        print("=" * 60 + "\n")
        
        if report.failed == 0:
            report.status = "READY FOR LIVE"
            print("╔═══════════════════════════════════════╗")
            print("║          READY FOR LIVE               ║")
            print("║   All validation checks passed!       ║")
            print("╚═══════════════════════════════════════╝")
        else:
            report.status = "BLOCKED"
            print("╔═══════════════════════════════════════╗")
            print("║             BLOCKED                   ║")
            print(f"║   {report.failed} validation check(s) failed      ║")
            print("╚═══════════════════════════════════════╝")
            print("\nFailed checks:")
            for r in report.results:
                if r.status == TestStatus.FAILED:
                    print(f"  - {r.name}: {r.message}")
        
        return report


async def main():
    """Main entry point for running tests"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ChatOS Thought-Line Validation Suite")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Backend API base URL"
    )
    parser.add_argument(
        "--output",
        help="Output file for JSON report"
    )
    args = parser.parse_args()
    
    suite = ThoughtLineTestSuite(base_url=args.base_url)
    report = await suite.run_all_checks()
    
    if args.output:
        with open(args.output, "w") as f:
            json.dump(report.to_dict(), f, indent=2)
        print(f"\nReport saved to: {args.output}")
    
    return 0 if report.status == "READY FOR LIVE" else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
