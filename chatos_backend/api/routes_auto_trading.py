"""
routes_auto_trading.py - PersRM Auto-Trading System API

Provides endpoints for automated trading driven by PersRM model:
- Start/stop auto-trading loop
- Real-time activity streaming via SSE
- Status and statistics

The auto-trader continuously:
1. Fetches market data
2. Sends to PersRM for analysis
3. Executes trading decisions
4. Streams activity to connected clients
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List, AsyncGenerator
from enum import Enum

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/auto-trading", tags=["Auto Trading"])


# =============================================================================
# Types & Models
# =============================================================================

class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class TradingSignal(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    CLOSE = "CLOSE"
    HOLD = "HOLD"


class ActivityType(str, Enum):
    ANALYZING = "analyzing"
    SIGNAL = "signal"
    EXECUTED = "executed"
    ERROR = "error"
    INFO = "info"


class ActivityEntry(BaseModel):
    """A single activity log entry."""
    id: str
    timestamp: str
    type: ActivityType
    symbol: str
    message: str
    signal: Optional[TradingSignal] = None
    reasoning: Optional[str] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    size: Optional[float] = None
    pnl: Optional[float] = None


class Position(BaseModel):
    """An open trading position."""
    id: str
    symbol: str
    side: str  # "long" or "short"
    size: float
    entry_price: float
    current_price: float
    pnl: float
    pnl_percent: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    opened_at: str


class AutoTradingConfig(BaseModel):
    """Configuration for auto-trading."""
    mode: TradingMode = TradingMode.PAPER
    interval_seconds: int = Field(default=15, ge=5, le=300)
    symbols: List[str] = ["BTCUSDT", "ETHUSDT"]
    risk_per_trade: float = Field(default=1.0, ge=0.1, le=5.0)
    max_positions: int = Field(default=3, ge=1, le=10)


class AutoTradingStatus(BaseModel):
    """Current status of the auto-trader."""
    running: bool
    mode: TradingMode
    started_at: Optional[str] = None
    cycles_completed: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    current_pnl: float = 0.0
    positions: List[Position] = []
    config: AutoTradingConfig


class StartRequest(BaseModel):
    """Request to start auto-trading."""
    mode: TradingMode = TradingMode.PAPER
    interval_seconds: int = 15
    symbols: List[str] = ["BTCUSDT"]


class StopResponse(BaseModel):
    """Response when stopping auto-trading."""
    success: bool
    message: str
    final_pnl: float
    total_trades: int


# =============================================================================
# Global State (In production, use Redis or database)
# =============================================================================

class AutoTraderState:
    """Manages the auto-trader state."""
    
    def __init__(self):
        self.running = False
        self.mode = TradingMode.PAPER
        self.started_at: Optional[str] = None
        self.config = AutoTradingConfig()
        self.cycles_completed = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.current_pnl = 0.0
        self.positions: List[Dict[str, Any]] = []
        self.activity_log: List[ActivityEntry] = []
        self.subscribers: List[asyncio.Queue] = []
        self._task: Optional[asyncio.Task] = None
        self.paper_balance = 100000.0  # $100K paper balance
        
        # Mock market data
        self.market_prices = {
            "BTCUSDT": {"price": 89274.19, "change24h": -1.89},
            "ETHUSDT": {"price": 3019.84, "change24h": -1.82},
            "SOLUSDT": {"price": 131.87, "change24h": -4.44},
            "BNBUSDT": {"price": 880.73, "change24h": -0.89},
            "XRPUSDT": {"price": 2.028, "change24h": -2.17},
        }
    
    def get_status(self) -> AutoTradingStatus:
        """Get current status."""
        positions = [
            Position(
                id=p["id"],
                symbol=p["symbol"],
                side=p["side"],
                size=p["size"],
                entry_price=p["entry_price"],
                current_price=self.market_prices.get(p["symbol"], {}).get("price", p["entry_price"]),
                pnl=p.get("pnl", 0),
                pnl_percent=p.get("pnl_percent", 0),
                stop_loss=p.get("stop_loss"),
                take_profit=p.get("take_profit"),
                opened_at=p["opened_at"],
            )
            for p in self.positions
        ]
        
        return AutoTradingStatus(
            running=self.running,
            mode=self.mode,
            started_at=self.started_at,
            cycles_completed=self.cycles_completed,
            total_trades=self.total_trades,
            winning_trades=self.winning_trades,
            current_pnl=self.current_pnl,
            positions=positions,
            config=self.config,
        )
    
    async def broadcast_activity(self, entry: ActivityEntry):
        """Broadcast activity to all subscribers."""
        self.activity_log.append(entry)
        # Keep only last 100 entries
        if len(self.activity_log) > 100:
            self.activity_log = self.activity_log[-100:]
        
        # Send to all subscribers
        dead_queues = []
        for queue in self.subscribers:
            try:
                await queue.put(entry)
            except:
                dead_queues.append(queue)
        
        # Remove dead subscribers
        for q in dead_queues:
            self.subscribers.remove(q)
    
    def update_market_prices(self):
        """Simulate market price movement."""
        import random
        for symbol in self.market_prices:
            current = self.market_prices[symbol]["price"]
            # Random walk: -0.5% to +0.5% per cycle
            change = random.uniform(-0.005, 0.005)
            new_price = current * (1 + change)
            self.market_prices[symbol]["price"] = round(new_price, 2)
            self.market_prices[symbol]["change24h"] = round(
                self.market_prices[symbol]["change24h"] + change * 100, 2
            )
        
        # Update position PnLs
        for pos in self.positions:
            current_price = self.market_prices.get(pos["symbol"], {}).get("price", pos["entry_price"])
            if pos["side"] == "long":
                pos["pnl"] = (current_price - pos["entry_price"]) * pos["size"]
            else:
                pos["pnl"] = (pos["entry_price"] - current_price) * pos["size"]
            pos["pnl_percent"] = (pos["pnl"] / (pos["entry_price"] * pos["size"])) * 100


# Global state instance
auto_trader = AutoTraderState()


# =============================================================================
# Auto-Trading Loop
# =============================================================================

async def run_auto_trading_loop():
    """Main auto-trading loop."""
    from chatos_backend.services.trading_brain import TradingBrain
    
    brain = TradingBrain()
    
    while auto_trader.running:
        try:
            # Update market prices (simulate movement)
            auto_trader.update_market_prices()
            
            # Analyze each symbol
            for symbol in auto_trader.config.symbols:
                if not auto_trader.running:
                    break
                
                # Broadcast analyzing status
                await auto_trader.broadcast_activity(ActivityEntry(
                    id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    type=ActivityType.ANALYZING,
                    symbol=symbol,
                    message=f"Analyzing {symbol}...",
                ))
                
                # Get market context
                price_data = auto_trader.market_prices.get(symbol, {})
                current_price = price_data.get("price", 0)
                change_24h = price_data.get("change24h", 0)
                
                # Get existing position for this symbol
                existing_position = next(
                    (p for p in auto_trader.positions if p["symbol"] == symbol),
                    None
                )
                
                # Get trading decision from PersRM
                decision = await brain.get_trading_decision(
                    symbol=symbol,
                    price=current_price,
                    change_24h=change_24h,
                    existing_position=existing_position,
                    balance=auto_trader.paper_balance,
                    mode=auto_trader.mode.value,
                )
                
                # Broadcast the signal
                await auto_trader.broadcast_activity(ActivityEntry(
                    id=str(uuid.uuid4())[:8],
                    timestamp=datetime.now().strftime("%H:%M:%S"),
                    type=ActivityType.SIGNAL,
                    symbol=symbol,
                    message=f"Signal: {decision['signal']}",
                    signal=TradingSignal(decision['signal']),
                    reasoning=decision.get('reasoning', ''),
                    entry_price=current_price if decision['signal'] in ['LONG', 'SHORT'] else None,
                    stop_loss=decision.get('stop_loss'),
                    take_profit=decision.get('take_profit'),
                ))
                
                # Execute the trade if not HOLD
                if decision['signal'] != 'HOLD':
                    executed = await execute_trade(
                        symbol=symbol,
                        signal=decision['signal'],
                        price=current_price,
                        stop_loss=decision.get('stop_loss'),
                        take_profit=decision.get('take_profit'),
                        reasoning=decision.get('reasoning', ''),
                    )
                    
                    if executed:
                        await auto_trader.broadcast_activity(ActivityEntry(
                            id=str(uuid.uuid4())[:8],
                            timestamp=datetime.now().strftime("%H:%M:%S"),
                            type=ActivityType.EXECUTED,
                            symbol=symbol,
                            message=executed['message'],
                            signal=TradingSignal(decision['signal']),
                            entry_price=executed.get('entry_price'),
                            size=executed.get('size'),
                            pnl=executed.get('pnl'),
                        ))
                
                # Small delay between symbols
                await asyncio.sleep(1)
            
            auto_trader.cycles_completed += 1
            
            # Wait for next cycle
            await asyncio.sleep(auto_trader.config.interval_seconds)
            
        except asyncio.CancelledError:
            break
        except Exception as e:
            await auto_trader.broadcast_activity(ActivityEntry(
                id=str(uuid.uuid4())[:8],
                timestamp=datetime.now().strftime("%H:%M:%S"),
                type=ActivityType.ERROR,
                symbol="SYSTEM",
                message=f"Error: {str(e)}",
            ))
            await asyncio.sleep(5)


async def execute_trade(
    symbol: str,
    signal: str,
    price: float,
    stop_loss: Optional[float],
    take_profit: Optional[float],
    reasoning: str,
) -> Optional[Dict[str, Any]]:
    """Execute a trading signal."""
    
    if signal == "LONG":
        # Check if we already have a position
        existing = next((p for p in auto_trader.positions if p["symbol"] == symbol), None)
        if existing:
            return None
        
        # Calculate position size (1% risk)
        risk_amount = auto_trader.paper_balance * (auto_trader.config.risk_per_trade / 100)
        sl_distance = price * 0.02  # 2% default SL
        size = risk_amount / sl_distance
        
        # Open long position
        position = {
            "id": str(uuid.uuid4())[:8],
            "symbol": symbol,
            "side": "long",
            "size": round(size, 6),
            "entry_price": price,
            "stop_loss": stop_loss or round(price * 0.98, 2),
            "take_profit": take_profit or round(price * 1.06, 2),
            "pnl": 0,
            "pnl_percent": 0,
            "opened_at": datetime.now().isoformat(),
        }
        auto_trader.positions.append(position)
        auto_trader.total_trades += 1
        
        return {
            "message": f"Opened LONG {symbol} @ ${price:,.2f}",
            "entry_price": price,
            "size": position["size"],
        }
    
    elif signal == "SHORT":
        # Check if we already have a position
        existing = next((p for p in auto_trader.positions if p["symbol"] == symbol), None)
        if existing:
            return None
        
        # Calculate position size
        risk_amount = auto_trader.paper_balance * (auto_trader.config.risk_per_trade / 100)
        sl_distance = price * 0.02
        size = risk_amount / sl_distance
        
        # Open short position
        position = {
            "id": str(uuid.uuid4())[:8],
            "symbol": symbol,
            "side": "short",
            "size": round(size, 6),
            "entry_price": price,
            "stop_loss": stop_loss or round(price * 1.02, 2),
            "take_profit": take_profit or round(price * 0.94, 2),
            "pnl": 0,
            "pnl_percent": 0,
            "opened_at": datetime.now().isoformat(),
        }
        auto_trader.positions.append(position)
        auto_trader.total_trades += 1
        
        return {
            "message": f"Opened SHORT {symbol} @ ${price:,.2f}",
            "entry_price": price,
            "size": position["size"],
        }
    
    elif signal == "CLOSE":
        # Find and close the position
        existing = next((p for p in auto_trader.positions if p["symbol"] == symbol), None)
        if not existing:
            return None
        
        # Calculate final PnL
        current_price = auto_trader.market_prices.get(symbol, {}).get("price", price)
        if existing["side"] == "long":
            pnl = (current_price - existing["entry_price"]) * existing["size"]
        else:
            pnl = (existing["entry_price"] - current_price) * existing["size"]
        
        # Update stats
        auto_trader.current_pnl += pnl
        auto_trader.paper_balance += pnl
        if pnl > 0:
            auto_trader.winning_trades += 1
        
        # Remove position
        auto_trader.positions = [p for p in auto_trader.positions if p["symbol"] != symbol]
        
        return {
            "message": f"Closed {existing['side'].upper()} {symbol} @ ${current_price:,.2f} | PnL: ${pnl:,.2f}",
            "entry_price": current_price,
            "pnl": pnl,
        }
    
    return None


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/start")
async def start_auto_trading(request: StartRequest, background_tasks: BackgroundTasks):
    """Start the auto-trading loop."""
    if auto_trader.running:
        raise HTTPException(status_code=400, detail="Auto-trading is already running")
    
    # Configure
    auto_trader.mode = request.mode
    auto_trader.config.mode = request.mode
    auto_trader.config.interval_seconds = request.interval_seconds
    auto_trader.config.symbols = request.symbols
    auto_trader.started_at = datetime.now().isoformat()
    auto_trader.running = True
    auto_trader.cycles_completed = 0
    
    # Start the loop
    auto_trader._task = asyncio.create_task(run_auto_trading_loop())
    
    # Broadcast start
    await auto_trader.broadcast_activity(ActivityEntry(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now().strftime("%H:%M:%S"),
        type=ActivityType.INFO,
        symbol="SYSTEM",
        message=f"Auto-trading started in {request.mode.value.upper()} mode",
    ))
    
    return {
        "success": True,
        "message": f"Auto-trading started in {request.mode.value} mode",
        "config": auto_trader.config.dict(),
    }


@router.post("/stop", response_model=StopResponse)
async def stop_auto_trading():
    """Stop the auto-trading loop."""
    if not auto_trader.running:
        raise HTTPException(status_code=400, detail="Auto-trading is not running")
    
    auto_trader.running = False
    
    if auto_trader._task:
        auto_trader._task.cancel()
        try:
            await auto_trader._task
        except asyncio.CancelledError:
            pass
        auto_trader._task = None
    
    # Broadcast stop
    await auto_trader.broadcast_activity(ActivityEntry(
        id=str(uuid.uuid4())[:8],
        timestamp=datetime.now().strftime("%H:%M:%S"),
        type=ActivityType.INFO,
        symbol="SYSTEM",
        message=f"Auto-trading stopped. Final PnL: ${auto_trader.current_pnl:,.2f}",
    ))
    
    return StopResponse(
        success=True,
        message="Auto-trading stopped",
        final_pnl=auto_trader.current_pnl,
        total_trades=auto_trader.total_trades,
    )


@router.get("/status", response_model=AutoTradingStatus)
async def get_status():
    """Get current auto-trading status."""
    return auto_trader.get_status()


@router.get("/activity")
async def stream_activity():
    """
    Stream auto-trading activity via Server-Sent Events (SSE).
    
    Connect to this endpoint to receive real-time updates about:
    - Market analysis
    - Trading signals
    - Executed trades
    - Errors and info messages
    """
    async def event_generator() -> AsyncGenerator[str, None]:
        queue: asyncio.Queue = asyncio.Queue()
        auto_trader.subscribers.append(queue)
        
        try:
            # Send initial connection message
            yield f"data: {json.dumps({'type': 'connected', 'message': 'Connected to auto-trading stream'})}\n\n"
            
            # Send recent activity
            for entry in auto_trader.activity_log[-10:]:
                yield f"data: {entry.json()}\n\n"
            
            # Stream new activity
            while True:
                try:
                    entry = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {entry.json()}\n\n"
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if queue in auto_trader.subscribers:
                auto_trader.subscribers.remove(queue)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/activity/history")
async def get_activity_history(limit: int = 50):
    """Get recent activity history."""
    return {
        "activities": [entry.dict() for entry in auto_trader.activity_log[-limit:]],
        "total": len(auto_trader.activity_log),
    }


@router.post("/reset")
async def reset_auto_trading():
    """Reset auto-trading state (paper balance, stats, positions)."""
    if auto_trader.running:
        raise HTTPException(status_code=400, detail="Stop auto-trading first")
    
    auto_trader.paper_balance = 100000.0
    auto_trader.current_pnl = 0.0
    auto_trader.total_trades = 0
    auto_trader.winning_trades = 0
    auto_trader.cycles_completed = 0
    auto_trader.positions = []
    auto_trader.activity_log = []
    
    return {
        "success": True,
        "message": "Auto-trading state reset",
        "balance": auto_trader.paper_balance,
    }

