"""
Real-time Data API Routes - WebSocket and REST endpoints for real-time market data.

Integrates with the frontend useRealtimeWebSocket hook for live data streaming.
Provides fallback REST endpoints for polling when WebSocket is unavailable.
"""

from typing import Optional, List, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field
import asyncio
import json
from datetime import datetime
import logging

from chatos_backend.services.realtime_data_store import (
    RealtimeDataStore,
    NewsItem,
    SentimentData,
    MarketTicker,
    RealtimeMessage,
    get_realtime_store
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/realtime", tags=["realtime"])


# ============================================================================
# Response Models
# ============================================================================

class DashboardData(BaseModel):
    """Dashboard summary data."""
    news: List[NewsItem] = Field(default_factory=list)
    sentiment: Optional[SentimentData] = None
    tickers: List[MarketTicker] = Field(default_factory=list)
    last_update: str


class FeedResponse(BaseModel):
    """REST feed response."""
    news: List[NewsItem] = Field(default_factory=list)
    sentiment: Optional[SentimentData] = None
    timestamp: str


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, channel: str = "all"):
    """
    WebSocket endpoint for real-time data streaming.
    
    Channels: 'all', 'news', 'sentiment', 'tickers'
    """
    await websocket.accept()
    store = get_realtime_store()
    store.add_client(websocket)
    
    logger.info(f"WebSocket client connected, channel: {channel}")
    
    try:
        # Send initial data
        dashboard_data = store.get_dashboard_data()
        initial_message = RealtimeMessage(
            type="init",
            data=dashboard_data,
            timestamp=datetime.utcnow().timestamp()
        )
        await websocket.send_text(initial_message.model_dump_json())
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages with timeout
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0  # 30 second timeout for ping/pong
                )
                
                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
                    continue
                
                # Handle subscription changes
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "subscribe":
                        channel = msg.get("channel", "all")
                        logger.debug(f"Client subscribed to channel: {channel}")
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                try:
                    await websocket.send_text(json.dumps({
                        "type": "heartbeat",
                        "timestamp": datetime.utcnow().timestamp()
                    }))
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        store.remove_client(websocket)


# ============================================================================
# REST Endpoints (fallback for polling)
# ============================================================================

@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard():
    """
    Get dashboard data with news, sentiment, and tickers.
    Use this as a fallback when WebSocket is unavailable.
    """
    store = get_realtime_store()
    data = store.get_dashboard_data()
    return DashboardData(
        news=[NewsItem(**n) if isinstance(n, dict) else n for n in data.get("news", [])],
        sentiment=SentimentData(**data["sentiment"]) if data.get("sentiment") else None,
        tickers=[MarketTicker(**t) if isinstance(t, dict) else t for t in data.get("tickers", [])],
        last_update=data.get("last_update", datetime.utcnow().isoformat())
    )


@router.get("/feed", response_model=FeedResponse)
async def get_feed(symbol: Optional[str] = Query(None, description="Filter by symbol")):
    """
    Get real-time feed data.
    Optionally filter by symbol.
    """
    store = get_realtime_store()
    news = store.get_news(limit=20, symbol=symbol)
    return FeedResponse(
        news=news,
        sentiment=store.get_sentiment(),
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/news", response_model=List[NewsItem])
async def get_news(
    limit: int = Query(20, ge=1, le=100),
    symbol: Optional[str] = Query(None)
):
    """Get latest news items."""
    store = get_realtime_store()
    return store.get_news(limit=limit, symbol=symbol)


@router.get("/sentiment", response_model=Optional[SentimentData])
async def get_sentiment():
    """Get current market sentiment."""
    store = get_realtime_store()
    return store.get_sentiment()


@router.get("/tickers", response_model=List[MarketTicker])
async def get_tickers(symbols: Optional[str] = Query(None, description="Comma-separated symbols")):
    """Get market tickers."""
    store = get_realtime_store()
    symbol_list = None
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",")]
    return store.get_tickers(symbols=symbol_list)


# ============================================================================
# Admin/Ingestion Endpoints (for scrapers to push data)
# ============================================================================

@router.post("/ingest/news")
async def ingest_news(item: NewsItem):
    """Ingest a news item (for scrapers)."""
    store = get_realtime_store()
    store.add_news(item)
    
    # Broadcast to WebSocket clients
    await store.broadcast(RealtimeMessage(
        type="news",
        data=[item.model_dump()],
        timestamp=datetime.utcnow().timestamp()
    ))
    
    return {"status": "ok", "id": item.id}


@router.post("/ingest/sentiment")
async def ingest_sentiment(sentiment: SentimentData):
    """Ingest sentiment data (for scrapers)."""
    store = get_realtime_store()
    store.update_sentiment(sentiment)
    
    # Broadcast to WebSocket clients
    await store.broadcast(RealtimeMessage(
        type="sentiment",
        data=sentiment.model_dump(),
        timestamp=datetime.utcnow().timestamp()
    ))
    
    return {"status": "ok"}


@router.post("/ingest/ticker")
async def ingest_ticker(ticker: MarketTicker):
    """Ingest a ticker update (for scrapers)."""
    store = get_realtime_store()
    store.update_ticker(ticker)
    
    # Broadcast to WebSocket clients
    await store.broadcast(RealtimeMessage(
        type="ticker",
        data=ticker.model_dump(),
        timestamp=datetime.utcnow().timestamp()
    ))
    
    return {"status": "ok", "symbol": ticker.symbol}


@router.get("/status")
async def get_realtime_status():
    """Get realtime data service status."""
    store = get_realtime_store()
    return store.get_status()

