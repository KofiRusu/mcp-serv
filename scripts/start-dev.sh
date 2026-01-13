#!/bin/bash
# ChatOS v2.0 - Development Startup Script
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHATOS_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting ChatOS v2.0 in Development Mode"
echo "=============================================="

# Load environment
if [ -f "$CHATOS_DIR/config/.env.development" ]; then
    export $(cat "$CHATOS_DIR/config/.env.development" | grep -v '^#' | xargs)
elif [ -f "$CHATOS_DIR/.env" ]; then
    export $(cat "$CHATOS_DIR/.env" | grep -v '^#' | xargs)
fi

# Check Ollama
if command -v ollama &> /dev/null; then
    if ! pgrep -x "ollama" > /dev/null; then
        echo "📦 Starting Ollama..."
        ollama serve &
        sleep 2
    else
        echo "✅ Ollama already running"
    fi
fi

# Start Backend (using chatos_backend.app as shown in running process)
echo ""
echo "🔧 Starting Backend (FastAPI)..."
cd "$CHATOS_DIR"
python -m uvicorn chatos_backend.app:app --host 127.0.0.1 --port 8000 --reload &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

sleep 3

# Start Frontend
echo ""
echo "🎨 Starting Frontend (Next.js)..."
cd "$CHATOS_DIR/sandbox-ui"
npm run dev -- -H 127.0.0.1 -p 3000 &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# Save PIDs
echo "$BACKEND_PID" > "$CHATOS_DIR/.backend.pid"
echo "$FRONTEND_PID" > "$CHATOS_DIR/.frontend.pid"

echo ""
echo "=============================================="
echo "✅ ChatOS v2.0 Development Mode Started!"
echo ""
echo "📍 Public Access:  http://192.168.0.249/"
echo "📍 Backend API:    http://127.0.0.1:8000 (localhost only)"
echo "📍 Frontend UI:    http://127.0.0.1:3000 (localhost only)"
echo "📍 API Docs:       http://192.168.0.249/api/docs"
echo ""
echo "Press Ctrl+C to stop all services"
echo "Or run: ./scripts/stop-all.sh"
echo "=============================================="

# Wait for processes
wait
