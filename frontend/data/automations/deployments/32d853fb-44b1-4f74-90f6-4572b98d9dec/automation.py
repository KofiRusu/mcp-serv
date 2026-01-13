import asyncio
import json
from datetime import datetime
from pathlib import Path
import websockets

OUTPUT_DIR = Path("/app/data")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SYMBOL = "BTCUSDT"
STREAM = "btcusdt@aggTrade"

async def connect_and_stream():
    url = f"wss://fstream.binance.com/ws/{STREAM}"
    print(f"Connecting to {url}...")
    
    async with websockets.connect(url) as ws:
        print(f"Connected! Streaming {STREAM} data...")
        
        while True:
            try:
                message = await ws.recv()
                data = json.loads(message)
                
                timestamp = datetime.utcnow().isoformat()
                record = {"timestamp": timestamp, "symbol": SYMBOL, "data": data}
                
                output_file = OUTPUT_DIR / f"{SYMBOL}_trades.jsonl"
                with open(output_file, "a") as f:
                    f.write(json.dumps(record) + "\n")
                
                print(f"[{timestamp}] Received trade update")
                
            except Exception as e:
                print(f"Error: {e}")
                await asyncio.sleep(1)

async def main():
    while True:
        try:
            await connect_and_stream()
        except Exception as e:
            print(f"Reconnecting in 5s... Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
