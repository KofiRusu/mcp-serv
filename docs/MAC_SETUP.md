# ChatOS Trading Platform - Mac Setup Guide

Complete guide for setting up and running the ChatOS trading platform on macOS.

## Prerequisites

### Required Software

1. **Node.js 18+**
   ```bash
   brew install node
   ```

2. **Python 3.9+**
   ```bash
   brew install python3
   ```

3. **Ollama** (recommended for AI features)
   ```bash
   brew install ollama
   ```

### Verify Installation

```bash
node --version  # Should be 18.x or higher
npm --version   # Should be 9.x or higher
python3 --version  # Should be 3.9 or higher
```

## Quick Start

### Option 1: Using the Launch Script (Recommended)

```bash
# Clone the repository
git clone -b trade https://github.com/KofiRusu/ChatOS-v2.0.git
cd ChatOS-v2.0

# Make launch script executable
chmod +x run-mac.sh

# Start everything
./run-mac.sh
```

The launch script will:
- Check all prerequisites
- Set up Python virtual environment
- Install Node.js dependencies
- Start the Python backend (port 8000)
- Start the Next.js UI (port 3000)

### Option 2: Manual Setup

```bash
# Clone the repository
git clone -b trade https://github.com/KofiRusu/ChatOS-v2.0.git
cd ChatOS-v2.0

# 1. Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r ChatOS/requirements.txt

# 2. Set up UI
cd sandbox-ui
npm install
cp .env.example .env.local

# 3. Start backend (in separate terminal)
cd /path/to/ChatOS-v2.0
source .venv/bin/activate
uvicorn ChatOS.app:app --host 0.0.0.0 --port 8000 --reload

# 4. Start UI (in separate terminal)
cd /path/to/ChatOS-v2.0/sandbox-ui
npm run dev
```

## Access the Trading Platform

Once running, open your browser:

- **Trading UI**: http://localhost:3000/trading
- **API Docs**: http://localhost:8000/docs

## Setting Up AI Features

The trading assistant requires Ollama with a model installed:

```bash
# Start Ollama
ollama serve

# In another terminal, pull a model
ollama pull mistral:7b
# Or for better performance:
ollama pull qwen2.5:7b
```

## Connecting Hyperliquid

1. Click the **"Connect"** button in the trading header
2. Select **Hyperliquid** from the exchange list
3. Choose **Testnet** for paper trading or **Mainnet** for live
4. Enter your wallet address and private key
5. Click **Verify & Connect**

**Security Note**: Private keys are stored only in browser session storage and never persisted to disk.

## Features Overview

| Feature | Description | Status |
|---------|-------------|--------|
| Live Market Data | Real-time prices from Binance via CCXT | ✅ Working |
| Trading Chart | Interactive candlestick chart with indicators | ✅ Working |
| Order Book | Live order book with spread display | ✅ Working |
| Hyperliquid | Wallet connection and trading | ✅ Working |
| AI Assistant | Trading assistant powered by Ollama | ✅ Working |
| Paper Trading | Practice trading without real funds | ✅ Working |
| Backtesting | Test strategies on historical data | ✅ Working |
| Data Recording | Capture market data for training | ✅ Working |

## Troubleshooting

### "Port already in use" error

```bash
# Find and kill the process using the port
lsof -i :3000  # or :8000 for backend
kill -9 <PID>
```

### Node.js dependency errors

```bash
# Clear node_modules and reinstall
cd sandbox-ui
rm -rf node_modules package-lock.json
npm install
```

### Python dependency errors

```bash
# Recreate virtual environment
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r ChatOS/requirements.txt
```

### Ollama not responding

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Chart not loading data

1. Check that the backend is running (http://localhost:8000/docs)
2. Check browser console for CORS errors
3. Verify CCXT is working:
   ```bash
   curl "http://localhost:3000/api/market?action=ticker&symbol=BTCUSDT"
   ```

## Data Persistence

- **UI State**: Stored in browser localStorage (persists across refreshes)
- **Hyperliquid Credentials**: Stored in sessionStorage (cleared when browser closes)
- **Backtest Results**: Saved to `sandbox-ui/data/backtests/`
- **Training Data**: Saved to `sandbox-ui/data/training/`
- **Market History**: Saved to `sandbox-ui/data/market-history/`

## Environment Variables

Copy `.env.example` to `.env.local` in the sandbox-ui directory:

```bash
cd sandbox-ui
cp .env.example .env.local
```

Key variables:
- `NEXT_PUBLIC_API_URL`: Backend API URL (default: http://localhost:8000)
- `OLLAMA_URL`: Ollama server URL (default: http://localhost:11434)
- `DEFAULT_MODE`: Initial trading mode (paper/live)

## Getting Help

- Check the API docs at http://localhost:8000/docs
- View console logs in both terminal windows
- Open browser developer tools (F12) for frontend errors

## Contributing

1. Fork the repository
2. Create a feature branch from `trade`
3. Make your changes
4. Submit a pull request

---

Happy Trading! 🚀

