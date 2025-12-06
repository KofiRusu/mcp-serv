#!/usr/bin/env python3
"""
Sentiment Scraper - Collects market sentiment data
Runs 24/7 in Docker container
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
import httpx

# Configuration
OUTPUT_DIR = Path(os.environ.get('OUTPUT_DIR', '/app/data/sentiment'))
INTERVAL = int(os.environ.get('INTERVAL_SECONDS', 600))


def fetch_fear_greed_index():
    """Fetch Fear & Greed Index from Alternative.me"""
    try:
        response = httpx.get(
            'https://api.alternative.me/fng/',
            timeout=30,
            headers={'User-Agent': 'ChatOS-Scraper/1.0'}
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('data'):
                fng = data['data'][0]
                return {
                    'value': int(fng.get('value', 50)),
                    'label': fng.get('value_classification', 'Neutral'),
                    'timestamp': fng.get('timestamp', str(int(time.time())))
                }
    except Exception as e:
        print(f"Error fetching Fear & Greed: {e}")
    return {'value': 50, 'label': 'Neutral', 'timestamp': str(int(time.time()))}


def fetch_global_metrics():
    """Fetch global market metrics from CoinGecko"""
    try:
        response = httpx.get(
            'https://api.coingecko.com/api/v3/global',
            timeout=30,
            headers={'User-Agent': 'ChatOS-Scraper/1.0'}
        )
        if response.status_code == 200:
            data = response.json().get('data', {})
            return {
                'total_market_cap': data.get('total_market_cap', {}).get('usd', 0) / 1e12,  # In trillions
                'total_volume': data.get('total_volume', {}).get('usd', 0) / 1e9,  # In billions
                'btc_dominance': data.get('market_cap_percentage', {}).get('btc', 0),
                'eth_dominance': data.get('market_cap_percentage', {}).get('eth', 0),
                'active_cryptocurrencies': data.get('active_cryptocurrencies', 0),
                'markets': data.get('markets', 0),
            }
    except Exception as e:
        print(f"Error fetching global metrics: {e}")
    return {}


def fetch_funding_rates():
    """Fetch funding rates from Binance Futures"""
    try:
        response = httpx.get(
            'https://fapi.binance.com/fapi/v1/fundingRate',
            params={'limit': 10},
            timeout=30,
            headers={'User-Agent': 'ChatOS-Scraper/1.0'}
        )
        if response.status_code == 200:
            data = response.json()
            if data:
                # Get average funding rate
                rates = [float(item.get('fundingRate', 0)) * 100 for item in data]
                avg_rate = sum(rates) / len(rates) if rates else 0
                return {'funding_rate': round(avg_rate, 4)}
    except Exception as e:
        print(f"Error fetching funding rates: {e}")
    return {'funding_rate': 0}


def save_sentiment(sentiment_data):
    """Save sentiment data to files"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Save to daily file
    date_str = datetime.now().strftime('%Y-%m-%d')
    daily_filepath = OUTPUT_DIR / f'{date_str}.json'
    
    # Load existing daily data
    daily_data = []
    if daily_filepath.exists():
        try:
            with open(daily_filepath) as f:
                daily_data = json.load(f)
        except:
            pass
    
    daily_data.append(sentiment_data)
    
    with open(daily_filepath, 'w') as f:
        json.dump(daily_data, f, indent=2)
    
    # Also save as latest.json for easy access
    latest_filepath = OUTPUT_DIR / 'latest.json'
    with open(latest_filepath, 'w') as f:
        json.dump(sentiment_data, f, indent=2)
    
    print(f"[{datetime.now().isoformat()}] Saved sentiment data (FGI: {sentiment_data.get('fear_greed_index', 'N/A')})")


def run_scraper():
    """Main scraper loop"""
    print(f"Starting Sentiment Scraper - Interval: {INTERVAL}s")
    print(f"Output directory: {OUTPUT_DIR}")
    
    while True:
        try:
            # Fetch all sentiment data
            fng = fetch_fear_greed_index()
            global_metrics = fetch_global_metrics()
            funding = fetch_funding_rates()
            
            sentiment_data = {
                'timestamp': datetime.now().isoformat(),
                'fear_greed_index': fng.get('value'),
                'fear_greed_label': fng.get('label'),
                'total_market_cap': global_metrics.get('total_market_cap'),
                'btc_dominance': global_metrics.get('btc_dominance'),
                'eth_dominance': global_metrics.get('eth_dominance'),
                'funding_rate': funding.get('funding_rate'),
                'active_cryptocurrencies': global_metrics.get('active_cryptocurrencies'),
            }
            
            save_sentiment(sentiment_data)
            
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] Scraper error: {e}")
        
        time.sleep(INTERVAL)


if __name__ == '__main__':
    run_scraper()

