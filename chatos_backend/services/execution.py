"""
Execution Integration - Trade Execution Layer for ChatOS

This module provides the execution layer for trading decisions, supporting:
- Paper trading simulation
- Live trading via Hyperliquid
- Order management (entry, stop-loss, take-profit)
- Execution tracking and reporting

The executor receives validated decisions from the risk manager and
converts them into actual orders on the connected exchange.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import hashlib

from chatos_backend.core.event_bus import get_event_bus, EventPriority
from chatos_backend.services.decision_arbiter import ArbiterDecision, ArbiterAction
from chatos_backend.services.risk_manager import RiskResult

logger = logging.getLogger(__name__)


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    STOP_LIMIT = "stop_limit"
    TAKE_PROFIT = "take_profit"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """Represents a trading order."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    symbol: str = ""
    side: OrderSide = OrderSide.BUY
    order_type: OrderType = OrderType.MARKET
    
    quantity: float = 0.0
    price: Optional[float] = None
    stop_price: Optional[float] = None
    
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    filled_price: float = 0.0
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None
    
    exchange_order_id: Optional[str] = None
    
    decision_id: Optional[str] = None
    thought_ids: List[str] = field(default_factory=list)
    
    fees: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "quantity": self.quantity,
            "price": self.price,
            "stop_price": self.stop_price,
            "status": self.status.value,
            "filled_quantity": self.filled_quantity,
            "filled_price": self.filled_price,
            "created_at": self.created_at.isoformat(),
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "exchange_order_id": self.exchange_order_id,
            "decision_id": self.decision_id,
            "fees": self.fees,
        }


@dataclass
class ExecutionResult:
    """Result of an execution attempt."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    success: bool = False
    error: Optional[str] = None
    
    decision_id: str = ""
    order: Optional[Order] = None
    
    fill_price: float = 0.0
    slippage_bps: float = 0.0
    latency_ms: float = 0.0
    
    stop_loss_order: Optional[Order] = None
    take_profit_order: Optional[Order] = None
    
    pre_state: Dict[str, Any] = field(default_factory=dict)
    post_state: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "success": self.success,
            "error": self.error,
            "decision_id": self.decision_id,
            "order": self.order.to_dict() if self.order else None,
            "fill_price": self.fill_price,
            "slippage_bps": self.slippage_bps,
            "latency_ms": self.latency_ms,
            "stop_loss_order": self.stop_loss_order.to_dict() if self.stop_loss_order else None,
            "take_profit_order": self.take_profit_order.to_dict() if self.take_profit_order else None,
        }


class BaseExecutor(ABC):
    """Base class for trade executors."""
    
    @abstractmethod
    async def execute(
        self,
        decision: ArbiterDecision,
        risk_result: RiskResult,
    ) -> ExecutionResult:
        pass
    
    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def get_balance(self) -> float:
        pass


class PaperExecutor(BaseExecutor):
    """
    Paper trading executor for simulation.
    
    Simulates order execution with realistic slippage and fees.
    """
    
    def __init__(self):
        self._event_bus = None
        self._store = None
        
        self._balance: float = 100000.0
        self._positions: List[Dict[str, Any]] = []
        self._orders: List[Order] = []
        self._trade_history: List[Dict[str, Any]] = []
        
        self.slippage_bps: float = 5.0
        self.fee_rate: float = 0.0006
    
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
    
    async def execute(
        self,
        decision: ArbiterDecision,
        risk_result: RiskResult,
    ) -> ExecutionResult:
        """Execute a paper trade."""
        start_time = time.time()
        result = ExecutionResult(decision_id=decision.id)
        
        if decision.action == ArbiterAction.HOLD:
            result.success = True
            result.error = "No action required for HOLD"
            return result
        
        result.pre_state = {
            "balance": self._balance,
            "positions": len(self._positions),
        }
        
        ticker = self.store.get_ticker(decision.symbol)
        if not ticker:
            result.success = False
            result.error = f"No market data for {decision.symbol}"
            return result
        
        current_price = ticker.price
        
        if decision.action == ArbiterAction.CLOSE:
            return await self._close_position(decision, result, current_price)
        
        size = risk_result.adjusted_size or decision.size or 0.02
        position_usd = self._balance * size
        quantity = position_usd / current_price
        
        slippage_mult = 1 + (self.slippage_bps / 10000) if decision.action == ArbiterAction.LONG else 1 - (self.slippage_bps / 10000)
        fill_price = current_price * slippage_mult
        
        fees = position_usd * self.fee_rate
        
        order = Order(
            symbol=decision.symbol,
            side=OrderSide.BUY if decision.action == ArbiterAction.LONG else OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=fill_price,
            status=OrderStatus.FILLED,
            filled_quantity=quantity,
            filled_price=fill_price,
            filled_at=datetime.now(timezone.utc),
            decision_id=decision.id,
            fees=fees,
        )
        
        position = {
            "id": str(uuid.uuid4())[:12],
            "symbol": decision.symbol,
            "side": "long" if decision.action == ArbiterAction.LONG else "short",
            "entry_price": fill_price,
            "quantity": quantity,
            "size_usd": position_usd,
            "unrealized_pnl": 0.0,
            "stop_loss": decision.stop_loss,
            "take_profit": decision.take_profit,
            "leverage": risk_result.adjusted_leverage or decision.leverage or 1.0,
            "opened_at": datetime.now(timezone.utc).isoformat(),
        }
        
        self._positions.append(position)
        self._orders.append(order)
        self._balance -= fees
        
        result.success = True
        result.order = order
        result.fill_price = fill_price
        result.slippage_bps = self.slippage_bps
        result.latency_ms = (time.time() - start_time) * 1000
        
        result.post_state = {
            "balance": self._balance,
            "positions": len(self._positions),
        }
        
        await self.event_bus.publish(
            "execution.completed",
            {
                "execution_id": result.id,
                "decision_id": decision.id,
                "symbol": decision.symbol,
                "action": decision.action.value,
                "fill_price": fill_price,
                "quantity": quantity,
                "mode": "paper",
            },
            source="paper_executor"
        )
        
        return result
    
    async def _close_position(
        self,
        decision: ArbiterDecision,
        result: ExecutionResult,
        current_price: float
    ) -> ExecutionResult:
        """Close an existing position."""
        position = next(
            (p for p in self._positions if p["symbol"] == decision.symbol),
            None
        )
        
        if not position:
            result.success = False
            result.error = f"No position found for {decision.symbol}"
            return result
        
        entry_price = position["entry_price"]
        quantity = position["quantity"]
        
        slippage_mult = 1 - (self.slippage_bps / 10000) if position["side"] == "long" else 1 + (self.slippage_bps / 10000)
        exit_price = current_price * slippage_mult
        
        if position["side"] == "long":
            pnl = (exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price) * quantity
        
        fees = position["size_usd"] * self.fee_rate
        net_pnl = pnl - fees
        
        self._balance += net_pnl
        self._positions = [p for p in self._positions if p["id"] != position["id"]]
        
        order = Order(
            symbol=decision.symbol,
            side=OrderSide.SELL if position["side"] == "long" else OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=quantity,
            price=exit_price,
            status=OrderStatus.FILLED,
            filled_quantity=quantity,
            filled_price=exit_price,
            filled_at=datetime.now(timezone.utc),
            decision_id=decision.id,
            fees=fees,
        )
        
        self._orders.append(order)
        
        self._trade_history.append({
            "position_id": position["id"],
            "symbol": decision.symbol,
            "side": position["side"],
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "pnl": net_pnl,
            "fees": fees,
            "closed_at": datetime.now(timezone.utc).isoformat(),
        })
        
        result.success = True
        result.order = order
        result.fill_price = exit_price
        
        result.post_state = {
            "balance": self._balance,
            "positions": len(self._positions),
            "trade_pnl": net_pnl,
        }
        
        await self.event_bus.publish(
            "execution.closed",
            {
                "execution_id": result.id,
                "position_id": position["id"],
                "symbol": decision.symbol,
                "pnl": net_pnl,
                "mode": "paper",
            },
            source="paper_executor"
        )
        
        return result
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a pending order."""
        for order in self._orders:
            if order.id == order_id and order.status == OrderStatus.PENDING:
                order.status = OrderStatus.CANCELLED
                return True
        return False
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions."""
        for position in self._positions:
            ticker = self.store.get_ticker(position["symbol"])
            if ticker:
                current_price = ticker.price
                entry_price = position["entry_price"]
                quantity = position["quantity"]
                
                if position["side"] == "long":
                    pnl = (current_price - entry_price) * quantity
                else:
                    pnl = (entry_price - current_price) * quantity
                
                position["current_price"] = current_price
                position["unrealized_pnl"] = pnl
        
        return self._positions
    
    async def get_balance(self) -> float:
        """Get current balance."""
        return self._balance
    
    def reset(self):
        """Reset paper trading state."""
        self._balance = 100000.0
        self._positions = []
        self._orders = []
        self._trade_history = []


class HyperliquidExecutor(BaseExecutor):
    """
    Live trading executor for Hyperliquid DEX.
    
    Requires wallet address and private key for signing transactions.
    """
    
    def __init__(
        self,
        wallet_address: Optional[str] = None,
        private_key: Optional[str] = None,
        testnet: bool = True,
    ):
        self.wallet_address = wallet_address
        self.private_key = private_key
        self.testnet = testnet
        
        self._event_bus = None
        self._client = None
        self._connected = False
        
        self.base_url = (
            "https://api.hyperliquid-testnet.xyz"
            if testnet
            else "https://api.hyperliquid.xyz"
        )
    
    @property
    def event_bus(self):
        if self._event_bus is None:
            self._event_bus = get_event_bus()
        return self._event_bus
    
    async def connect(self) -> bool:
        """Connect to Hyperliquid."""
        if not self.wallet_address or not self.private_key:
            logger.error("Wallet address and private key required for Hyperliquid")
            return False
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/info",
                    json={
                        "type": "clearinghouseState",
                        "user": self.wallet_address,
                    }
                )
                
                if response.status_code == 200:
                    self._connected = True
                    logger.info(f"Connected to Hyperliquid {'testnet' if self.testnet else 'mainnet'}")
                    return True
                else:
                    logger.error(f"Failed to connect to Hyperliquid: {response.status_code}")
                    return False
                    
        except ImportError:
            logger.error("httpx not available for Hyperliquid connection")
            return False
        except Exception as e:
            logger.error(f"Hyperliquid connection error: {e}")
            return False
    
    async def execute(
        self,
        decision: ArbiterDecision,
        risk_result: RiskResult,
    ) -> ExecutionResult:
        """Execute a live trade on Hyperliquid."""
        result = ExecutionResult(decision_id=decision.id)
        
        if not self._connected:
            if not await self.connect():
                result.success = False
                result.error = "Not connected to Hyperliquid"
                return result
        
        if decision.action == ArbiterAction.HOLD:
            result.success = True
            return result
        
        try:
            logger.info(f"[LIVE] Would execute {decision.action.value} on {decision.symbol}")
            
            result.success = False
            result.error = "Live execution not yet implemented - use paper trading"
            
            await self.event_bus.publish(
                "execution.attempted",
                {
                    "decision_id": decision.id,
                    "action": decision.action.value,
                    "symbol": decision.symbol,
                    "mode": "live",
                    "testnet": self.testnet,
                },
                priority=EventPriority.HIGH,
                source="hyperliquid_executor"
            )
            
        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error(f"Hyperliquid execution error: {e}")
        
        return result
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order on Hyperliquid."""
        logger.warning("Hyperliquid order cancellation not yet implemented")
        return False
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get positions from Hyperliquid."""
        if not self._connected:
            return []
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/info",
                    json={
                        "type": "clearinghouseState",
                        "user": self.wallet_address,
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    positions = data.get("assetPositions", [])
                    return [
                        {
                            "symbol": p.get("position", {}).get("coin", ""),
                            "size": float(p.get("position", {}).get("szi", 0)),
                            "entry_price": float(p.get("position", {}).get("entryPx", 0)),
                            "unrealized_pnl": float(p.get("position", {}).get("unrealizedPnl", 0)),
                            "liquidation_price": float(p.get("position", {}).get("liquidationPx", 0)),
                        }
                        for p in positions
                        if float(p.get("position", {}).get("szi", 0)) != 0
                    ]
        except Exception as e:
            logger.error(f"Error getting Hyperliquid positions: {e}")
        
        return []
    
    async def get_balance(self) -> float:
        """Get account balance from Hyperliquid."""
        if not self._connected:
            return 0.0
        
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/info",
                    json={
                        "type": "clearinghouseState",
                        "user": self.wallet_address,
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    margin = data.get("marginSummary", {})
                    return float(margin.get("accountValue", 0))
        except Exception as e:
            logger.error(f"Error getting Hyperliquid balance: {e}")
        
        return 0.0


class ExecutionRouter:
    """
    Routes execution requests to the appropriate executor based on mode.
    """
    
    def __init__(self, mode: TradingMode = TradingMode.PAPER):
        self.mode = mode
        self.paper_executor = PaperExecutor()
        self.live_executor: Optional[HyperliquidExecutor] = None
        self._event_bus = None
    
    @property
    def event_bus(self):
        if self._event_bus is None:
            self._event_bus = get_event_bus()
        return self._event_bus
    
    def set_mode(self, mode: TradingMode):
        """Set the trading mode."""
        self.mode = mode
        logger.info(f"Execution mode set to: {mode.value}")
    
    def configure_live(
        self,
        wallet_address: str,
        private_key: str,
        testnet: bool = True
    ):
        """Configure the live executor."""
        self.live_executor = HyperliquidExecutor(
            wallet_address=wallet_address,
            private_key=private_key,
            testnet=testnet,
        )
    
    async def execute(
        self,
        decision: ArbiterDecision,
        risk_result: RiskResult,
    ) -> ExecutionResult:
        """Execute via the appropriate executor."""
        await self.event_bus.publish(
            "execution.started",
            {
                "decision_id": decision.id,
                "symbol": decision.symbol,
                "action": decision.action.value,
                "mode": self.mode.value,
            },
            source="execution_router"
        )
        
        if self.mode == TradingMode.PAPER:
            result = await self.paper_executor.execute(decision, risk_result)
        elif self.mode == TradingMode.LIVE:
            if not self.live_executor:
                result = ExecutionResult(decision_id=decision.id)
                result.success = False
                result.error = "Live executor not configured"
            else:
                result = await self.live_executor.execute(decision, risk_result)
        else:
            result = ExecutionResult(decision_id=decision.id)
            result.success = False
            result.error = f"Unknown mode: {self.mode}"
        
        if not result.success:
            await self.event_bus.publish(
                "execution.error",
                {
                    "execution_id": result.id,
                    "decision_id": decision.id,
                    "error": result.error,
                    "mode": self.mode.value,
                },
                priority=EventPriority.HIGH,
                source="execution_router"
            )
        
        return result
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get positions from the current executor."""
        if self.mode == TradingMode.PAPER:
            return await self.paper_executor.get_positions()
        elif self.mode == TradingMode.LIVE and self.live_executor:
            return await self.live_executor.get_positions()
        return []
    
    async def get_balance(self) -> float:
        """Get balance from the current executor."""
        if self.mode == TradingMode.PAPER:
            return await self.paper_executor.get_balance()
        elif self.mode == TradingMode.LIVE and self.live_executor:
            return await self.live_executor.get_balance()
        return 0.0


_execution_router: Optional[ExecutionRouter] = None


def get_execution_router() -> ExecutionRouter:
    """Get the execution router singleton."""
    global _execution_router
    if _execution_router is None:
        _execution_router = ExecutionRouter()
    return _execution_router
