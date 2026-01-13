#!/bin/bash
# =============================================================================
# ChatOS System Validation Script
# =============================================================================
#
# This script checks if all ChatOS components are working correctly
# for private remote access.
#
# Usage:
#   bash scripts/validate-system.sh
#
# =============================================================================

CHATOS_DIR="${CHATOS_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"

echo "=================================================="
echo "ChatOS System Validation"
echo "=================================================="
echo ""
echo "Checking all components for remote access readiness..."
echo ""

PASS=0
FAIL=0
WARN=0

# Helper functions
check_pass() {
    echo "  ✓ $1"
    ((PASS++))
}

check_fail() {
    echo "  ✗ $1"
    ((FAIL++))
}

check_warn() {
    echo "  ⚠ $1"
    ((WARN++))
}

# =============================================================================
# 1. Check Files Exist
# =============================================================================
echo "[1/8] Checking required files..."

if [ -f "$CHATOS_DIR/chatos_backend/api/auth_middleware.py" ]; then
    check_pass "auth_middleware.py exists"
else
    check_fail "auth_middleware.py MISSING"
fi

if [ -f "$CHATOS_DIR/chatos_backend/api/routes_ip_whitelist.py" ]; then
    check_pass "routes_ip_whitelist.py exists"
else
    check_fail "routes_ip_whitelist.py MISSING"
fi

if [ -f "$CHATOS_DIR/chatos_backend/api/routes_monitoring.py" ]; then
    check_pass "routes_monitoring.py exists"
else
    check_fail "routes_monitoring.py MISSING"
fi

if [ -f "$CHATOS_DIR/chatos_backend/database/init_schema.py" ]; then
    check_pass "init_schema.py exists"
else
    check_fail "init_schema.py MISSING"
fi

if [ -f "$CHATOS_DIR/Caddyfile" ]; then
    check_pass "Caddyfile exists"
else
    check_fail "Caddyfile MISSING"
fi

# =============================================================================
# 2. Check Frontend Admin Pages
# =============================================================================
echo ""
echo "[2/8] Checking frontend admin pages..."

if [ -f "$CHATOS_DIR/frontend/src/app/admin/page.tsx" ]; then
    check_pass "Admin dashboard page exists"
else
    check_fail "Admin dashboard page MISSING"
fi

if [ -f "$CHATOS_DIR/frontend/src/app/admin/ip-whitelist/page.tsx" ]; then
    check_pass "IP whitelist page exists"
else
    check_fail "IP whitelist page MISSING"
fi

if [ -f "$CHATOS_DIR/frontend/src/app/admin/monitoring/page.tsx" ]; then
    check_pass "Monitoring page exists"
else
    check_fail "Monitoring page MISSING"
fi

if [ -f "$CHATOS_DIR/frontend/src/app/admin/sessions/page.tsx" ]; then
    check_pass "Sessions page exists"
else
    check_fail "Sessions page MISSING"
fi

# =============================================================================
# 3. Check sandbox-ui Admin Pages
# =============================================================================
echo ""
echo "[3/8] Checking sandbox-ui admin pages..."

if [ -f "$CHATOS_DIR/sandbox-ui/src/app/admin/page.tsx" ]; then
    check_pass "sandbox-ui admin dashboard exists"
else
    check_fail "sandbox-ui admin dashboard MISSING"
fi

if [ -f "$CHATOS_DIR/sandbox-ui/src/app/admin/ip-whitelist/page.tsx" ]; then
    check_pass "sandbox-ui IP whitelist page exists"
else
    check_warn "sandbox-ui IP whitelist page missing (optional)"
fi

# =============================================================================
# 4. Check WebSocket Auto-Detection
# =============================================================================
echo ""
echo "[4/8] Checking WebSocket auto-detection..."

if grep -q "getWebSocketUrl" "$CHATOS_DIR/frontend/src/hooks/use-realtime-websocket.ts" 2>/dev/null; then
    check_pass "Frontend WebSocket auto-detection implemented"
else
    check_fail "Frontend WebSocket still uses hardcoded URL"
fi

if grep -q "getWebSocketUrl" "$CHATOS_DIR/sandbox-ui/src/hooks/use-realtime-websocket.ts" 2>/dev/null; then
    check_pass "sandbox-ui WebSocket auto-detection implemented"
else
    check_warn "sandbox-ui WebSocket may need update"
fi

# =============================================================================
# 5. Check Services
# =============================================================================
echo ""
echo "[5/8] Checking services..."

# Check if Caddy is installed
if command -v caddy &> /dev/null; then
    check_pass "Caddy is installed"
    
    # Check if Caddy is running
    if systemctl is-active --quiet caddy 2>/dev/null; then
        check_pass "Caddy service is running"
    else
        check_warn "Caddy service is not running"
    fi
else
    check_warn "Caddy not installed (needed for remote access)"
fi

# Check if PostgreSQL is running
if systemctl is-active --quiet postgresql 2>/dev/null; then
    check_pass "PostgreSQL is running"
else
    check_warn "PostgreSQL may not be running"
fi

# =============================================================================
# 6. Check Backend API (if running)
# =============================================================================
echo ""
echo "[6/8] Checking backend API..."

if curl -s -o /dev/null -w "%{http_code}" "http://localhost:8000/api/health" 2>/dev/null | grep -q "200"; then
    check_pass "Backend API is responding"
    
    # Check for new endpoints
    if curl -s "http://localhost:8000/docs" 2>/dev/null | grep -q "whitelist"; then
        check_pass "Whitelist endpoints registered"
    else
        check_warn "Whitelist endpoints may not be registered yet"
    fi
else
    check_warn "Backend not running (start with: uvicorn chatos_backend.app:app --host 0.0.0.0 --port 8000)"
fi

# =============================================================================
# 7. Check Frontend (if running)
# =============================================================================
echo ""
echo "[7/8] Checking frontend..."

if curl -s -o /dev/null -w "%{http_code}" "http://localhost:3000" 2>/dev/null | grep -q "200"; then
    check_pass "Frontend is responding"
else
    check_warn "Frontend not running (cd frontend && npm run dev)"
fi

# =============================================================================
# 8. Check Firewall
# =============================================================================
echo ""
echo "[8/8] Checking firewall..."

if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null | head -1)
    if echo "$UFW_STATUS" | grep -q "active"; then
        check_pass "UFW firewall is active"
        
        if sudo ufw status 2>/dev/null | grep -q "443.*ALLOW"; then
            check_pass "Port 443 is allowed"
        else
            check_warn "Port 443 may not be allowed"
        fi
    else
        check_warn "UFW is not active (run: sudo bash scripts/configure-firewall.sh)"
    fi
else
    check_warn "UFW not available"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "=================================================="
echo "Validation Summary"
echo "=================================================="
echo ""
echo "  Passed:   $PASS"
echo "  Failed:   $FAIL"
echo "  Warnings: $WARN"
echo ""

if [ $FAIL -gt 0 ]; then
    echo "STATUS: FAILED - Some critical checks failed"
    echo ""
    echo "Please fix the failed items before running the system."
    exit 1
elif [ $WARN -gt 0 ]; then
    echo "STATUS: READY (with warnings)"
    echo ""
    echo "The system should work, but check the warnings."
else
    echo "STATUS: ALL GOOD!"
    echo ""
    echo "Your system is ready for private remote access!"
fi

echo ""
echo "=================================================="
echo "Quick Start Guide"
echo "=================================================="
echo ""
echo "1. Initialize database (first time only):"
echo "   python -m chatos_backend.database.init_schema"
echo ""
echo "2. Start backend:"
echo "   cd $CHATOS_DIR"
echo "   python -m uvicorn chatos_backend.app:app --host 0.0.0.0 --port 8000"
echo ""
echo "3. Start frontend:"
echo "   cd $CHATOS_DIR/frontend"
echo "   npm run build && npm start"
echo ""
echo "4. Configure firewall (if not done):"
echo "   sudo bash $CHATOS_DIR/scripts/configure-firewall.sh"
echo ""
echo "5. Access from remote:"
echo "   https://your-domain.com"
echo ""
echo "=================================================="
