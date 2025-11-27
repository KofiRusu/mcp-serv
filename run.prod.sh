#!/bin/bash
# =============================================================================
# ChatOS Production Server
# 
# This script runs the production server accessible on the network.
# Usage: ./run.prod.sh [port]
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

PORT="${1:-8000}"

echo "🚀 ChatOS Production Server"
echo "=============================="

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip --quiet
pip install -r ChatOS/requirements.txt --quiet

# Get local IP for display
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "localhost")

echo ""
echo "=============================="
echo "✅ Environment ready!"
echo "🌐 Server will be accessible at:"
echo "   - http://localhost:$PORT"
echo "   - http://$LOCAL_IP:$PORT"
echo "📖 API docs: http://localhost:$PORT/docs"
echo "⏹️  Press Ctrl+C to stop"
echo "=============================="
echo ""

# Run the production server (accessible on all interfaces)
uvicorn ChatOS.app:app --host 0.0.0.0 --port "$PORT" --workers 1

