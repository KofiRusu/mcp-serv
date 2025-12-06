#!/usr/bin/env python3
"""
News Scraper - Collects crypto news from various sources
Runs 24/7 in Docker container
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
import httpx

# Configuration
OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', '/app/data/news'))
INTERVAL = int(os.environ.get('INTERVAL_SECONDS', 300))

# News sources
NEWS_SOURCES = [
    {
        'name': 'CoinGecko',
        'url': 'https://api.coingecko.com/api/v3/news',
        'parser': 'coingecko'
    },
]


def fetch_coingecko_news():
    """Fetch news from CoinGecko API"""
    try:
        response = httpx.get(
            'https://api.coingecko.com/api/v3/news',
            timeout=30,
            headers={'User-Agent': 'ChatOS-Scraper/1.0'}
        )
        if response.status_code == 200:
            data = response.json()
            articles = []
            for item in data.get('data', [])[:20]:
                articles.append({
                    'id': item.get('id', str(hash(item.get('title', '')))),
                    'title': item.get('title', ''),
                    'source': item.get('author', 'CoinGecko'),
                    'url': item.get('url', '#'),
                    'timestamp': item.get('updated_at', datetime.now().isoformat()),
                    'description': item.get('description', '')[:500] if item.get('description') else '',
                })
            return articles
    except Exception as e:
        print(f"Error fetching CoinGecko news: {e}")
    return []


def analyze_sentiment(title, description=''):
    """Simple sentiment analysis based on keywords"""
    text = (title + ' ' + description).lower()
    
    bullish_keywords = ['surge', 'bull', 'rally', 'gain', 'up', 'high', 'record', 
                        'adoption', 'institutional', 'etf', 'approval', 'buy']
    bearish_keywords = ['crash', 'bear', 'fall', 'drop', 'low', 'sell', 'fear',
                        'hack', 'scam', 'ban', 'regulation', 'lawsuit']
    
    bullish_count = sum(1 for kw in bullish_keywords if kw in text)
    bearish_count = sum(1 for kw in bearish_keywords if kw in text)
    
    if bullish_count > bearish_count:
        return 'bullish'
    elif bearish_count > bullish_count:
        return 'bearish'
    return 'neutral'


def extract_symbols(text):
    """Extract crypto symbols from text"""
    symbols = []
    symbol_map = {
        'bitcoin': 'BTCUSDT', 'btc': 'BTCUSDT',
        'ethereum': 'ETHUSDT', 'eth': 'ETHUSDT',
        'solana': 'SOLUSDT', 'sol': 'SOLUSDT',
        'xrp': 'XRPUSDT', 'ripple': 'XRPUSDT',
        'cardano': 'ADAUSDT', 'ada': 'ADAUSDT',
        'bnb': 'BNBUSDT', 'binance': 'BNBUSDT',
    }
    
    text_lower = text.lower()
    for keyword, symbol in symbol_map.items():
        if keyword in text_lower and symbol not in symbols:
            symbols.append(symbol)
    
    return symbols if symbols else ['BTCUSDT']


def save_news(articles):
    """Save news to daily JSON file"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime('%Y-%m-%d')
    filepath = OUTPUT_DIR / f'{date_str}.json'
    
    # Add sentiment and symbols
    for article in articles:
        article['sentiment'] = analyze_sentiment(
            article.get('title', ''), 
            article.get('description', '')
        )
        article['symbols'] = extract_symbols(
            article.get('title', '') + ' ' + article.get('description', '')
        )
    
    # Load existing and merge
    existing = []
    if filepath.exists():
        try:
            with open(filepath) as f:
                existing = json.load(f)
        except:
            pass
    
    # Deduplicate by ID
    seen_ids = {a['id'] for a in existing}
    new_articles = [a for a in articles if a['id'] not in seen_ids]
    
    combined = existing + new_articles
    
    with open(filepath, 'w') as f:
        json.dump(combined, f, indent=2)
    
    print(f"[{datetime.now().isoformat()}] Saved {len(new_articles)} new articles ({len(combined)} total)")


def run_scraper():
    """Main scraper loop"""
    print(f"Starting News Scraper - Interval: {INTERVAL}s")
    print(f"Output directory: {OUTPUT_DIR}")
    
    while True:
        try:
            # Fetch from all sources
            all_articles = []
            all_articles.extend(fetch_coingecko_news())
            
            if all_articles:
                save_news(all_articles)
            else:
                print(f"[{datetime.now().isoformat()}] No articles fetched")
                
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Scraper error: {e}")
        
        time.sleep(INTERVAL)


if __name__ == '__main__':
    run_scraper()

