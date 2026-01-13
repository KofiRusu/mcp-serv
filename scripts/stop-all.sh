#!/bin/bash
# ChatOS v2.0 - Stop All Services
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHATOS_DIR="$(dirname "$SCRIPT_DIR")"

echo "🛑 Stopping ChatOS v2.0 Services"
echo "=================================="

# Stop Backend
if [ -f "$CHATOS_DIR/.backend.pid" ]; then
    BACKEND_PID=$(cat "$CHATOS_DIR/.backend.pid")
    if kill -0 "$BACKEND_PID" 2>/dev/null; then
        echo "Stopping Backend (PID: $BACKEND_PID)..."
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    rm -f "$CHATOS_DIR/.backend.pid"
fi

# Also kill any uvicorn processes for ChatOS
pkill -f "uvicorn chatos_backend.app:app" 2>/dev/null || true
echo "✅ Backend stopped"

# Stop Frontend
if [ -f "$CHATOS_DIR/.frontend.pid" ]; then
    FRONTEND_PID=$(cat "$CHATOS_DIR/.frontend.pid")
    if kill -0 "$FRONTEND_PID" 2>/dev/null; then
        echo "Stopping Frontend (PID: $FRONTEND_PID)..."
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    rm -f "$CHATOS_DIR/.frontend.pid"
fi

# Also kill any next processes
pkill -f "next-server" 2>/dev/null || true
pkill -f "node.*sandbox-ui" 2>/dev/null || true
echo "✅ Frontend stopped"

# Stop Scrapers (if any running)
echo "Stopping Docker scrapers..."
cd "$CHATOS_DIR/scrapers" 2>/dev/null
docker compose -f docker-compose.scrapers.yml down 2>/dev/null || true
echo "✅ Scrapers stopped"

echo ""
echo "=================================="
echo "✅ All ChatOS v2.0 services stopped"
echo ""
echo "Note: Caddy reverse proxy continues running (system service)"
echo "      To stop: sudo systemctl stop caddy"
echo "=================================="
