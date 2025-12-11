"""
Real-time Data Store Service

Manages real-time market data including news, sentiment, and tickers.
Supports WebSocket broadcasting to connected clients.

This store can be populated by:
1. Docker scrapers pushing data via REST endpoints
2. WebSocket connections from external data sources
3. Manual data ingestion
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from fastapi import WebSocket
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

class NewsItem(BaseModel):
    """Real-time news item."""
    id: str
    title: str
    content: Optional[str] = None
    source: str
    url: Optional[str] = None
    timestamp: str
    symbols: List[str] = Field(default_factory=list)
    sentiment: Optional[str] = None  # 'bullish', 'bearish', 'neutral'


class SentimentData(BaseModel):
    """Market sentiment data (Fear & Greed Index style)."""
    value: float  # 0-100
    label: str  # 'Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed'
    timestamp: str
    
    @classmethod
    def from_value(cls, value: float) -> "SentimentData":
        """Create sentiment data from a value."""
        if value < 20:
            label = "Extreme Fear"
        elif value < 40:
            label = "Fear"
        elif value < 60:
            label = "Neutral"
        elif value < 80:
            label = "Greed"
        else:
            label = "Extreme Greed"
        
        return cls(
            value=value,
            label=label,
            timestamp=datetime.utcnow().isoformat()
        )


class MarketTicker(BaseModel):
    """Real-time market ticker."""
    symbol: str
    price: float
    change_24h: float
    volume_24h: float
    timestamp: str


class TradeData(BaseModel):
    """Real-time trade data."""
    symbol: str
    price: float
    amount: float
    side: str  # 'buy' or 'sell'
    timestamp: str


class OrderBookUpdate(BaseModel):
    """Order book update."""
    symbol: str
    bids: List[List[float]]  # [[price, amount], ...]
    asks: List[List[float]]
    timestamp: str


class RealtimeMessage(BaseModel):
    """WebSocket message format for broadcasting."""
    type: str  # 'news', 'sentiment', 'ticker', 'trade', 'orderbook', 'init', 'heartbeat'
    data: Any
    timestamp: float


# ============================================================================
# Real-time Data Store
# ============================================================================

class RealtimeDataStore:
    """
    In-memory store for real-time market data with WebSocket broadcasting.
    
    Features:
    - News items with automatic expiry
    - Market sentiment tracking
    - Ticker price updates
    - Trade streaming
    - WebSocket client management
    """
    
    def __init__(self, data_dir: Optional[str] = None):
        """Initialize the store."""
        self.news: List[NewsItem] = []
        self.sentiment: Optional[SentimentData] = None
        self.tickers: Dict[str, MarketTicker] = {}
        self.recent_trades: Dict[str, List[TradeData]] = {}  # symbol -> recent trades
        self.orderbooks: Dict[str, OrderBookUpdate] = {}
        
        self.connected_clients: List[WebSocket] = []
        self._last_update = datetime.utcnow()
        
        # Data directory for persistence
        self.data_dir = Path(data_dir) if data_dir else None
        
        # Load persisted data if available
        if self.data_dir:
            self._load_persisted_data()
    
    def _load_persisted_data(self):
        """Load persisted data from disk."""
        if not self.data_dir:
            return
        
        try:
            # Load news
            news_file = self.data_dir / "news.json"
            if news_file.exists():
                with open(news_file) as f:
                    data = json.load(f)
                    self.news = [NewsItem(**item) for item in data[-100:]]
            
            # Load sentiment
            sentiment_file = self.data_dir / "sentiment.json"
            if sentiment_file.exists():
                with open(sentiment_file) as f:
                    data = json.load(f)
                    self.sentiment = SentimentData(**data)
        except Exception as e:
            logger.warning(f"Failed to load persisted data: {e}")
    
    def _persist_news(self):
        """Persist news to disk."""
        if not self.data_dir:
            return
        
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            news_file = self.data_dir / "news.json"
            with open(news_file, 'w') as f:
                json.dump([n.model_dump() for n in self.news], f)
        except Exception as e:
            logger.warning(f"Failed to persist news: {e}")
    
    def _persist_sentiment(self):
        """Persist sentiment to disk."""
        if not self.data_dir and self.sentiment:
            return
        
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            sentiment_file = self.data_dir / "sentiment.json"
            with open(sentiment_file, 'w') as f:
                json.dump(self.sentiment.model_dump(), f)
        except Exception as e:
            logger.warning(f"Failed to persist sentiment: {e}")
    
    # ========================================================================
    # News Management
    # ========================================================================
    
    def add_news(self, item: NewsItem):
        """Add a news item."""
        # Check for duplicates
        if any(n.id == item.id for n in self.news):
            return
        
        self.news.insert(0, item)
        # Keep only last 100 items
        self.news = self.news[:100]
        self._last_update = datetime.utcnow()
        self._persist_news()
    
    def get_news(self, limit: int = 20, symbol: Optional[str] = None) -> List[NewsItem]:
        """Get news items, optionally filtered by symbol."""
        news = self.news
        if symbol:
            news = [n for n in news if symbol in n.symbols or not n.symbols]
        return news[:limit]
    
    # ========================================================================
    # Sentiment Management
    # ========================================================================
    
    def update_sentiment(self, sentiment: SentimentData):
        """Update sentiment data."""
        self.sentiment = sentiment
        self._last_update = datetime.utcnow()
        self._persist_sentiment()
    
    def get_sentiment(self) -> Optional[SentimentData]:
        """Get current sentiment."""
        return self.sentiment
    
    # ========================================================================
    # Ticker Management
    # ========================================================================
    
    def update_ticker(self, ticker: MarketTicker):
        """Update a ticker."""
        self.tickers[ticker.symbol] = ticker
        self._last_update = datetime.utcnow()
    
    def get_ticker(self, symbol: str) -> Optional[MarketTicker]:
        """Get a specific ticker."""
        return self.tickers.get(symbol)
    
    def get_tickers(self, symbols: Optional[List[str]] = None) -> List[MarketTicker]:
        """Get tickers, optionally filtered by symbols."""
        tickers = list(self.tickers.values())
        if symbols:
            tickers = [t for t in tickers if t.symbol in symbols]
        return tickers
    
    # ========================================================================
    # Trade Management
    # ========================================================================
    
    def add_trade(self, trade: TradeData):
        """Add a trade."""
        symbol = trade.symbol
        if symbol not in self.recent_trades:
            self.recent_trades[symbol] = []
        
        self.recent_trades[symbol].insert(0, trade)
        # Keep only last 100 trades per symbol
        self.recent_trades[symbol] = self.recent_trades[symbol][:100]
        self._last_update = datetime.utcnow()
    
    def get_recent_trades(self, symbol: str, limit: int = 20) -> List[TradeData]:
        """Get recent trades for a symbol."""
        return self.recent_trades.get(symbol, [])[:limit]
    
    # ========================================================================
    # Order Book Management
    # ========================================================================
    
    def update_orderbook(self, update: OrderBookUpdate):
        """Update order book for a symbol."""
        self.orderbooks[update.symbol] = update
        self._last_update = datetime.utcnow()
    
    def get_orderbook(self, symbol: str) -> Optional[OrderBookUpdate]:
        """Get order book for a symbol."""
        return self.orderbooks.get(symbol)
    
    # ========================================================================
    # WebSocket Management
    # ========================================================================
    
    async def broadcast(self, message: RealtimeMessage):
        """Broadcast message to all connected WebSocket clients."""
        if not self.connected_clients:
            return
        
        data = message.model_dump_json()
        disconnected = []
        
        for client in self.connected_clients:
            try:
                await client.send_text(data)
            except Exception:
                disconnected.append(client)
        
        # Remove disconnected clients
        for client in disconnected:
            if client in self.connected_clients:
                self.connected_clients.remove(client)
    
    def add_client(self, websocket: WebSocket):
        """Add a WebSocket client."""
        if websocket not in self.connected_clients:
            self.connected_clients.append(websocket)
    
    def remove_client(self, websocket: WebSocket):
        """Remove a WebSocket client."""
        if websocket in self.connected_clients:
            self.connected_clients.remove(websocket)
    
    # ========================================================================
    # Dashboard Data
    # ========================================================================
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get combined dashboard data."""
        return {
            "news": [n.model_dump() for n in self.news[:20]],
            "sentiment": self.sentiment.model_dump() if self.sentiment else None,
            "tickers": [t.model_dump() for t in self.tickers.values()],
            "last_update": self._last_update.isoformat()
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get store status."""
        return {
            "status": "ok",
            "connected_clients": len(self.connected_clients),
            "news_count": len(self.news),
            "tickers_count": len(self.tickers),
            "has_sentiment": self.sentiment is not None,
            "last_update": self._last_update.isoformat()
        }


# ============================================================================
# Singleton Instance
# ============================================================================

_store: Optional[RealtimeDataStore] = None

def get_realtime_store() -> RealtimeDataStore:
    """Get the realtime data store singleton."""
    global _store
    if _store is None:
        # Use data directory from environment or default
        data_dir = os.environ.get(
            "REALTIME_DATA_DIR",
            str(Path.home() / "ChatOS-v2.0" / "sandbox-ui" / "data" / "realtime")
        )
        _store = RealtimeDataStore(data_dir=data_dir)
    return _store

