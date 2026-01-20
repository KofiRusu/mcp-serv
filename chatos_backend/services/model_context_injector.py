"""
model_context_injector.py - Automatic Real-Time Data Injection for ChatOS Models

This module provides middleware for injecting real-time scraped data
into model conversations, enabling accurate and current responses
without requiring the model to be trained on the data.

Ported from ChatOS v2.1 with adaptations for v2.2 architecture.

Usage:
    from chatos_backend.services.model_context_injector import inject_context

    # In your chat handler:
    enriched_messages = inject_context(messages, user_message)
    response = model.generate(enriched_messages)
"""

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


SYMBOL_PATTERNS = {
    r'\bBTC\b|\bBitcoin\b': 'BTCUSDT',
    r'\bETH\b|\bEthereum\b': 'ETHUSDT',
    r'\bSOL\b|\bSolana\b': 'SOLUSDT',
    r'\bBNB\b|\bBinance Coin\b': 'BNBUSDT',
    r'\bXRP\b|\bRipple\b': 'XRPUSDT',
    r'\bADA\b|\bCardano\b': 'ADAUSDT',
    r'\bDOGE\b|\bDogecoin\b': 'DOGEUSDT',
    r'\bAVAX\b|\bAvalanche\b': 'AVAXUSDT',
    r'\bDOT\b|\bPolkadot\b': 'DOTUSDT',
    r'\bMATIC\b|\bPolygon\b': 'MATICUSDT',
    r'\bLINK\b|\bChainlink\b': 'LINKUSDT',
    r'\bUNI\b|\bUniswap\b': 'UNIUSDT',
    r'\bARB\b|\bArbitrum\b': 'ARBUSDT',
    r'\bOP\b|\bOptimism\b': 'OPUSDT',
}

TOPIC_PATTERNS = {
    'price': [r'\bprice\b', r'\bhow much\b', r'\bworth\b', r'\bcost\b', r'\bvalue\b', r'\btrading at\b'],
    'market': [r'\bmarket\b', r'\bmarkets\b', r'\bcrypto market\b', r'\boverall\b'],
    'sentiment': [r'\bsentiment\b', r'\bfear\b', r'\bgreed\b', r'\bmood\b', r'\bfeeling\b', r'\bbullish\b', r'\bbearish\b'],
    'news': [r'\bnews\b', r'\bheadlines?\b', r'\brecent\b', r'\blatest\b', r'\bhappening\b', r'\bupdates?\b'],
    'trading': [r'\btrade\b', r'\btrading\b', r'\bbuy\b', r'\bsell\b', r'\blong\b', r'\bshort\b', r'\bposition\b'],
    'technical': [r'\banalysis\b', r'\btechnical\b', r'\bchart\b', r'\bsupport\b', r'\bresistance\b', r'\brsi\b', r'\bmacd\b'],
    'volume': [r'\bvolume\b', r'\bliquidity\b', r'\bflow\b', r'\bwhale\b'],
    'liquidation': [r'\bliquidation\b', r'\bliquidated\b', r'\brekt\b', r'\bwipeout\b'],
    'funding': [r'\bfunding\b', r'\bfunding rate\b', r'\bperp\b', r'\bperpetual\b'],
    'orderflow': [r'\borderflow\b', r'\bbuys\b', r'\bsells\b', r'\bdelta\b', r'\bcvd\b'],
}


def detect_symbols(text: str) -> List[str]:
    """Detect cryptocurrency symbols mentioned in text."""
    detected = []
    text_clean = text.strip()
    
    for pattern, symbol in SYMBOL_PATTERNS.items():
        if re.search(pattern, text_clean, re.IGNORECASE):
            if symbol not in detected:
                detected.append(symbol)
    
    return detected


def detect_topics(text: str) -> Dict[str, bool]:
    """Detect what topics the user is asking about."""
    topics = {}
    text_lower = text.lower()
    
    for topic, patterns in TOPIC_PATTERNS.items():
        topics[topic] = any(re.search(p, text_lower) for p in patterns)
    
    return topics


def is_market_related(text: str) -> bool:
    """Check if the message is related to markets/trading."""
    topics = detect_topics(text)
    symbols = detect_symbols(text)
    
    return bool(symbols) or any(topics.values())


class ContextBuilder:
    """Builds context strings based on detected intent."""
    
    def __init__(self):
        self._store = None
    
    @property
    def store(self):
        if self._store is None:
            from chatos_backend.services.realtime_data_store import get_realtime_store
            self._store = get_realtime_store()
        return self._store
    
    def build_context(
        self,
        user_message: str,
        max_length: int = 2000,
        force_symbols: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Build appropriate context based on user message.
        
        Returns:
            Tuple of (context_string, metadata_dict)
        """
        symbols = force_symbols or detect_symbols(user_message)
        topics = detect_topics(user_message)
        
        if not symbols and any(topics.values()):
            symbols = ['BTCUSDT', 'ETHUSDT']
        
        if len(symbols) == 1 and (topics['price'] or topics['technical']):
            context = self._build_symbol_detail_context(symbols[0])
        elif topics['news']:
            context = self._build_news_context(symbols)
        elif topics['sentiment']:
            context = self._build_sentiment_context()
        elif topics['liquidation'] or topics['funding'] or topics['orderflow']:
            context = self._build_derivatives_context(symbols, topics)
        elif topics['market'] or symbols:
            context = self._build_market_overview_context(symbols, topics)
        elif topics['trading']:
            context = self._build_trading_context(symbols)
        else:
            return "", {"context_type": "none", "symbols": []}
        
        if len(context) > max_length:
            context = context[:max_length - 20] + "\n... [truncated]"
        
        metadata = {
            "context_type": self._get_context_type(topics),
            "symbols": symbols,
            "topics": {k: v for k, v in topics.items() if v},
            "length": len(context),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        
        return context, metadata
    
    def _get_context_type(self, topics: Dict[str, bool]) -> str:
        """Determine primary context type."""
        if topics.get('news'):
            return "news"
        if topics.get('sentiment'):
            return "sentiment"
        if topics.get('technical'):
            return "technical"
        if topics.get('trading'):
            return "trading"
        if topics.get('liquidation') or topics.get('funding') or topics.get('orderflow'):
            return "derivatives"
        if topics.get('price'):
            return "price"
        return "market"
    
    def _build_symbol_detail_context(self, symbol: str) -> str:
        """Build detailed context for a single symbol."""
        parts = []
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        parts.append(f"=== {symbol} DETAIL ({now}) ===\n")
        
        ticker = self.store.get_ticker(symbol)
        if ticker:
            parts.append(f"Price: ${ticker.price:,.2f}")
            parts.append(f"24h Change: {ticker.change_24h:+.2f}%")
            parts.append(f"24h Volume: ${ticker.volume_24h/1e6:.2f}M")
        else:
            parts.append(f"Price data for {symbol} currently unavailable")
        
        trades = self.store.get_recent_trades(symbol, limit=20)
        if trades:
            buy_vol = sum(t.amount for t in trades if t.side == 'buy')
            sell_vol = sum(t.amount for t in trades if t.side == 'sell')
            total = buy_vol + sell_vol
            if total > 0:
                parts.append(f"\nRecent Trade Flow:")
                parts.append(f"  Buy Pressure: {buy_vol/total*100:.1f}%")
                parts.append(f"  Sell Pressure: {sell_vol/total*100:.1f}%")
        
        return "\n".join(parts)
    
    def _build_news_context(self, symbols: List[str]) -> str:
        """Build news-focused context."""
        parts = []
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        parts.append(f"=== CRYPTO NEWS UPDATE ({now}) ===\n")
        
        if symbols:
            for sym in symbols[:2]:
                news = self.store.get_news(limit=3, symbol=sym)
                if news:
                    parts.append(f"\n{sym} News:")
                    for n in news:
                        sentiment_icon = {"bullish": "+", "bearish": "-", "neutral": "="}.get(n.sentiment, "")
                        parts.append(f"  [{sentiment_icon}] {n.title} ({n.source})")
        
        general_news = self.store.get_news(limit=5)
        if general_news:
            parts.append("\nGeneral Crypto News:")
            for n in general_news[:5]:
                sentiment_icon = {"bullish": "+", "bearish": "-", "neutral": "="}.get(n.sentiment, "")
                parts.append(f"  [{sentiment_icon}] {n.title} ({n.source})")
        
        parts.append("\nCurrent Prices:")
        for sym in symbols or ['BTCUSDT', 'ETHUSDT']:
            ticker = self.store.get_ticker(sym)
            if ticker:
                parts.append(f"  {sym}: ${ticker.price:,.2f} ({ticker.change_24h:+.2f}%)")
        
        return "\n".join(parts)
    
    def _build_sentiment_context(self) -> str:
        """Build sentiment-focused context."""
        parts = []
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        parts.append(f"=== MARKET SENTIMENT ({now}) ===\n")
        
        sentiment = self.store.get_sentiment()
        if sentiment:
            parts.append(f"Fear & Greed Index: {sentiment.value:.0f}/100 ({sentiment.label})")
        else:
            parts.append("Sentiment data currently unavailable")
        
        parts.append("\nCurrent Prices:")
        for sym in ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']:
            ticker = self.store.get_ticker(sym)
            if ticker:
                parts.append(f"  {sym}: ${ticker.price:,.2f} ({ticker.change_24h:+.2f}%)")
        
        news = self.store.get_news(limit=10)
        if news:
            bullish = sum(1 for n in news if n.sentiment == 'bullish')
            bearish = sum(1 for n in news if n.sentiment == 'bearish')
            parts.append(f"\nRecent News Sentiment: {bullish} bullish, {bearish} bearish")
        
        return "\n".join(parts)
    
    def _build_derivatives_context(self, symbols: List[str], topics: Dict[str, bool]) -> str:
        """Build derivatives/orderflow context."""
        parts = []
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        parts.append(f"=== DERIVATIVES DATA ({now}) ===\n")
        
        symbols = symbols or ['BTCUSDT', 'ETHUSDT']
        
        for sym in symbols:
            ticker = self.store.get_ticker(sym)
            if ticker:
                parts.append(f"\n{sym}:")
                parts.append(f"  Price: ${ticker.price:,.2f} ({ticker.change_24h:+.2f}%)")
            
            trades = self.store.get_recent_trades(sym, limit=50)
            if trades:
                buy_vol = sum(t.amount * t.price for t in trades if t.side == 'buy')
                sell_vol = sum(t.amount * t.price for t in trades if t.side == 'sell')
                delta = buy_vol - sell_vol
                parts.append(f"  Recent Delta: ${delta/1e3:+,.1f}K (CVD direction)")
                parts.append(f"  Buy Value: ${buy_vol/1e3:.1f}K | Sell Value: ${sell_vol/1e3:.1f}K")
        
        return "\n".join(parts)
    
    def _build_market_overview_context(self, symbols: List[str], topics: Dict[str, bool]) -> str:
        """Build general market overview context."""
        parts = []
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        parts.append(f"=== MARKET OVERVIEW ({now}) ===\n")
        
        symbols = symbols or ['BTCUSDT', 'ETHUSDT', 'SOLUSDT']
        
        for sym in symbols:
            ticker = self.store.get_ticker(sym)
            if ticker:
                parts.append(f"{sym}: ${ticker.price:,.2f} ({ticker.change_24h:+.2f}%) | Vol: ${ticker.volume_24h/1e6:.1f}M")
        
        sentiment = self.store.get_sentiment()
        if sentiment:
            parts.append(f"\nMarket Sentiment: {sentiment.value:.0f}/100 ({sentiment.label})")
        
        if topics.get('news', True):
            news = self.store.get_news(limit=3)
            if news:
                parts.append("\nLatest Headlines:")
                for n in news[:3]:
                    parts.append(f"  - {n.title}")
        
        return "\n".join(parts)
    
    def _build_trading_context(self, symbols: List[str]) -> str:
        """Build trading-specific context with recent trades."""
        parts = []
        now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        parts.append(f"=== TRADING DATA ({now}) ===\n")
        
        symbols = symbols or ['BTCUSDT', 'ETHUSDT']
        
        for sym in symbols:
            ticker = self.store.get_ticker(sym)
            if ticker:
                parts.append(f"\n{sym}:")
                parts.append(f"  Price: ${ticker.price:,.2f} ({ticker.change_24h:+.2f}%)")
                parts.append(f"  24h Volume: ${ticker.volume_24h/1e6:.1f}M")
            
            trades = self.store.get_recent_trades(sym, limit=50)
            if trades:
                buy_vol = sum(t.amount * t.price for t in trades if t.side == 'buy')
                sell_vol = sum(t.amount * t.price for t in trades if t.side == 'sell')
                total_vol = buy_vol + sell_vol
                if total_vol > 0:
                    parts.append(f"  Recent Flow: Buy {buy_vol/total_vol*100:.1f}% | Sell {sell_vol/total_vol*100:.1f}%")
        
        sentiment = self.store.get_sentiment()
        if sentiment:
            parts.append(f"\nMarket Sentiment: {sentiment.value:.0f}/100 ({sentiment.label})")
        
        return "\n".join(parts)


def inject_context(
    messages: List[Dict[str, str]],
    user_message: Optional[str] = None,
    max_context_length: int = 2000,
    always_inject: bool = False,
) -> List[Dict[str, str]]:
    """
    Inject real-time data context into chat messages.
    
    This function modifies the messages list to include real-time
    market data when the conversation is market-related.
    
    Args:
        messages: List of chat messages (role, content format)
        user_message: Latest user message (if not in messages)
        max_context_length: Maximum context string length
        always_inject: Always inject context regardless of topic
    
    Returns:
        Modified messages list with context injected
    """
    if not messages:
        return messages
    
    if user_message is None:
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
    
    if not user_message:
        return messages
    
    if not always_inject and not is_market_related(user_message):
        return messages
    
    builder = ContextBuilder()
    context, metadata = builder.build_context(user_message, max_context_length)
    
    if not context:
        return messages
    
    enriched = messages.copy()
    
    system_idx = None
    for i, msg in enumerate(enriched):
        if msg.get("role") == "system":
            system_idx = i
            break
    
    context_block = (
        f"\n\n--- REAL-TIME MARKET DATA ---\n"
        f"{context}\n"
        f"--- END MARKET DATA ---\n\n"
        f"Use the above data to provide accurate, current market information. "
        f"Cite specific numbers when relevant."
    )
    
    if system_idx is not None:
        enriched[system_idx] = {
            "role": "system",
            "content": enriched[system_idx]["content"] + context_block,
        }
    else:
        enriched.insert(0, {
            "role": "system",
            "content": f"You are a helpful trading assistant with access to real-time market data.{context_block}",
        })
    
    logger.debug(f"Injected {metadata['context_type']} context ({metadata['length']} chars) for symbols: {metadata['symbols']}")
    
    return enriched


def get_context_for_message(
    message: str,
    max_length: int = 2000,
) -> Tuple[str, Dict[str, Any]]:
    """
    Get context string for a message (without modifying messages list).
    
    Useful for custom integration or when you need just the context.
    """
    builder = ContextBuilder()
    return builder.build_context(message, max_length)


def format_for_ollama(
    prompt: str,
    system: Optional[str] = None,
    include_context: bool = True,
) -> Dict[str, str]:
    """
    Format prompt with context for Ollama API.
    
    Returns dict ready for ollama.generate() or ollama.chat()
    """
    if include_context and is_market_related(prompt):
        builder = ContextBuilder()
        context, _ = builder.build_context(prompt)
        
        if context:
            enriched_system = (
                f"{system or 'You are a helpful trading assistant.'}\n\n"
                f"--- REAL-TIME DATA ---\n{context}\n--- END DATA ---"
            )
            return {
                "prompt": prompt,
                "system": enriched_system,
            }
    
    return {
        "prompt": prompt,
        "system": system or "You are a helpful assistant.",
    }


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        message = "What's the current price of Bitcoin and is the market bullish?"
    
    print(f"User: {message}\n")
    print("=" * 60)
    
    context, metadata = get_context_for_message(message)
    
    print(f"Context Type: {metadata['context_type']}")
    print(f"Symbols: {metadata['symbols']}")
    print(f"Topics: {metadata['topics']}")
    print(f"Length: {metadata['length']} chars")
    print("=" * 60)
    print("\nGenerated Context:\n")
    print(context)
