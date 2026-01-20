#!/usr/bin/env python3
"""
Remote Data Client - Connects Mac client to Linux server's data stream.
Replaces local scrapers with remote WebSocket feed.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Callable, List
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('RemoteDataClient')

try:
    import websockets
    import httpx
except ImportError:
    logger.error("Install dependencies: pip install websockets httpx")
    raise

SERVER_URL = os.environ.get('CHATOS_DATA_URL', 'http://localhost:8080')
API_KEY = os.environ.get('CHATOS_API_KEY', 'chatos_api_key_change_me')
LOCAL_DATA_DIR = Path(os.environ.get('SCRAPED_DATA_DIR', '~/ChatOS-Data/scraped')).expanduser()


class RemoteDataClient:
    """Connects to remote ChatOS data server and streams data locally."""
    
    def __init__(self, server_url: str = SERVER_URL, api_key: str = API_KEY):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.running = False
        self.handlers: Dict[str, List[Callable]] = {}
        self._reconnect_delay = 1
    
    async def connect(self) -> bool:
        """Establish connection to remote server."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.server_url}/health",
                    timeout=5
                )
                if resp.status_code != 200:
                    logger.error(f"Server health check failed: {resp.status_code}")
                    return False
            logger.info(f"Connected to {self.server_url}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    async def get_latest(self, data_type: str, symbol: str) -> Optional[dict]:
        """Fetch latest data for a symbol."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.server_url}/api/latest/{data_type}/{symbol}",
                    headers={"X-API-Key": self.api_key},
                    timeout=10
                )
                if resp.status_code == 200:
                    return resp.json()
                return None
        except Exception as e:
            logger.error(f"get_latest error: {e}")
            return None
    
    async def get_history(self, data_type: str, symbol: str, limit: int = 100) -> Optional[dict]:
        """Fetch historical data."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.server_url}/api/history/{data_type}/{symbol}",
                    params={"limit": limit},
                    headers={"X-API-Key": self.api_key},
                    timeout=30
                )
                if resp.status_code == 200:
                    return resp.json()
                return None
        except Exception as e:
            logger.error(f"get_history error: {e}")
            return None
    
    def on(self, channel: str, handler: Callable):
        """Register handler for a channel."""
        if channel not in self.handlers:
            self.handlers[channel] = []
        self.handlers[channel].append(handler)
    
    async def stream(self, channels: List[str]):
        """Start streaming data from remote server."""
        self.running = True
        ws_url = self.server_url.replace('http', 'ws')
        
        while self.running:
            try:
                channel_param = ','.join(channels)
                url = f"{ws_url}/ws/stream?api_key={self.api_key}&channels={channel_param}"
                
                async with websockets.connect(url) as ws:
                    self.ws = ws
                    self._reconnect_delay = 1
                    logger.info(f"Streaming from {channels}")
                    
                    async for message in ws:
                        data = json.loads(message)
                        channel = data.get('channel', '')
                        payload = data.get('data', {})
                        
                        await self._save_locally(channel, payload)
                        
                        if channel in self.handlers:
                            for handler in self.handlers[channel]:
                                try:
                                    if asyncio.iscoroutinefunction(handler):
                                        await handler(payload)
                                    else:
                                        handler(payload)
                                except Exception as e:
                                    logger.error(f"Handler error: {e}")
                        
                        for pattern, handlers in self.handlers.items():
                            if '*' in pattern:
                                prefix = pattern.replace('*', '')
                                if channel.startswith(prefix):
                                    for handler in handlers:
                                        try:
                                            if asyncio.iscoroutinefunction(handler):
                                                await handler(payload)
                                            else:
                                                handler(payload)
                                        except Exception as e:
                                            logger.error(f"Handler error: {e}")
                                            
            except websockets.ConnectionClosed:
                logger.warning("WebSocket closed, reconnecting...")
            except Exception as e:
                logger.error(f"Stream error: {e}")
            
            if self.running:
                await asyncio.sleep(self._reconnect_delay)
                self._reconnect_delay = min(self._reconnect_delay * 2, 30)
    
    async def _save_locally(self, channel: str, data: dict):
        """Save streamed data to local filesystem for compatibility."""
        try:
            parts = channel.split(':')
            if len(parts) < 2:
                return
            
            data_type, symbol = parts[0], parts[1]
            dir_path = LOCAL_DATA_DIR / data_type
            dir_path.mkdir(parents=True, exist_ok=True)
            
            file_path = dir_path / f"latest_{symbol}.json"
            with open(file_path, 'w') as f:
                json.dump(data, f)
                
        except Exception as e:
            logger.debug(f"Local save error: {e}")
    
    async def subscribe(self, channels: List[str]):
        """Subscribe to additional channels."""
        if self.ws:
            await self.ws.send(json.dumps({
                'type': 'subscribe',
                'channels': channels
            }))
    
    async def unsubscribe(self, channels: List[str]):
        """Unsubscribe from channels."""
        if self.ws:
            await self.ws.send(json.dumps({
                'type': 'unsubscribe',
                'channels': channels
            }))
    
    def stop(self):
        """Stop streaming."""
        self.running = False


async def main():
    """Example usage."""
    client = RemoteDataClient()
    
    if not await client.connect():
        print("Failed to connect to server")
        return
    
    def on_trade(data):
        print(f"Trade: {data['symbol']} @ {data['price']}")
    
    def on_funding(data):
        print(f"Funding: {data['symbol']} = {data['funding_rate']}")
    
    client.on('trades:BTCUSDT', on_trade)
    client.on('funding:*', on_funding)
    
    await client.stream([
        'trades:BTCUSDT',
        'trades:ETHUSDT',
        'funding:BTCUSDT',
        'funding:ETHUSDT',
        'oi:BTCUSDT'
    ])


if __name__ == '__main__':
    asyncio.run(main())
