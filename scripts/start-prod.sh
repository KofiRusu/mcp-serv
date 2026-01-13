#!/bin/bash
# ChatOS v2.2 - Production Startup Script
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CHATOS_DIR="$(dirname "$SCRIPT_DIR")"

echo "🚀 Starting ChatOS v2.2 in Production Mode"
echo "=============================================="

# Load production environment
if [ -f "$CHATOS_DIR/config/.env.production" ]; then
    export $(cat "$CHATOS_DIR/config/.env.production" | grep -v '^#' | xargs)
fi

# Check Caddy
if command -v caddy &> /dev/null; then
    echo "🔒 Checking Caddy..."
    if ! systemctl is-active --quiet caddy; then
        echo "   Starting Caddy..."
        sudo systemctl start caddy
    else
        echo "✅ Caddy already running"
    fi
fi

# Start Backend (Gunicorn with Uvicorn workers for production)
echo ""
echo "🔧 Starting Backend (FastAPI with Uvicorn)..."
cd "$CHATOS_DIR"
export PYTHONPATH="$CHATOS_DIR:$CHATOS_DIR/venv/lib/python3.13/site-packages"
python3 -m uvicorn ChatOS.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info &
BACKEND_PID=$!
echo "   Backend PID: $BACKEND_PID"

sleep 3

# Build and start Frontend (production mode)
echo ""
echo "🎨 Building and Starting Frontend..."
cd "$CHATOS_DIR/sandbox-ui"
npm run build
npm start &
FRONTEND_PID=$!
echo "   Frontend PID: $FRONTEND_PID"

# Start scrapers
echo ""
echo "📊 Starting Scrapers..."
cd "$CHATOS_DIR/scrapers"
docker compose -f docker-compose.scrapers.yml up -d

# Save PIDs
echo "$BACKEND_PID" > "$CHATOS_DIR/.backend.pid"
echo "$FRONTEND_PID" > "$CHATOS_DIR/.frontend.pid"

echo ""
echo "=============================================="
echo "✅ ChatOS v2.2 Production Mode Started!"
echo ""
echo "📍 Backend API:    http://localhost:8000"
echo "📍 Frontend UI:    http://localhost:3000"
echo "📍 Via Caddy:      https://your-domain.com"
echo ""
echo "📊 Scrapers Status:"
docker ps --filter "name=chatos-" --format "   {{.Names}}: {{.Status}}"
echo ""
echo "To stop: ./scripts/stop-all.sh"
echo "=============================================="

# Wait for processes
wait
