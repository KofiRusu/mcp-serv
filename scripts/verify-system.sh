#!/bin/bash
# =============================================================================
# ChatOS System Verification Script
# =============================================================================
#
# This script checks that all ChatOS components are running and configured
# correctly for remote access.
#
# Usage:
#   bash scripts/verify-system.sh
#
# =============================================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "ChatOS System Verification"
echo "========================================"
echo ""

PASS=0
WARN=0
FAIL=0

check_pass() {
    echo -e "  ${GREEN}PASS${NC}: $1"
    ((PASS++))
}

check_warn() {
    echo -e "  ${YELLOW}WARN${NC}: $1"
    ((WARN++))
}

check_fail() {
    echo -e "  ${RED}FAIL${NC}: $1"
    ((FAIL++))
}

# =============================================================================
# 1. Check Services
# =============================================================================
echo "1. Checking Services..."

# Check Caddy
if systemctl is-active --quiet caddy 2>/dev/null; then
    check_pass "Caddy is running"
elif pgrep -x caddy > /dev/null; then
    check_pass "Caddy is running (not via systemd)"
else
    check_fail "Caddy is not running"
fi

# Check if port 443 is listening
if ss -tlnp 2>/dev/null | grep -q ":443 "; then
    check_pass "Port 443 is listening"
else
    check_warn "Port 443 is not listening (Caddy may not be configured)"
fi

# Check backend (port 8000)
if ss -tlnp 2>/dev/null | grep -q ":8000 "; then
    check_pass "Backend is running on port 8000"
else
    check_warn "Backend is not running on port 8000"
fi

# Check frontend (port 3000)
if ss -tlnp 2>/dev/null | grep -q ":3000 "; then
    check_pass "Frontend is running on port 3000"
else
    check_warn "Frontend is not running on port 3000"
fi

# Check PostgreSQL
if systemctl is-active --quiet postgresql 2>/dev/null; then
    check_pass "PostgreSQL is running"
elif pgrep -x postgres > /dev/null; then
    check_pass "PostgreSQL is running (not via systemd)"
else
    check_warn "PostgreSQL may not be running"
fi

# Check Keycloak (port 8080)
if ss -tlnp 2>/dev/null | grep -q ":8080 "; then
    check_pass "Keycloak is running on port 8080"
else
    check_warn "Keycloak is not running (auth may not work)"
fi

echo ""

# =============================================================================
# 2. Check Files
# =============================================================================
echo "2. Checking Configuration Files..."

CHATOS_DIR="${CHATOS_DIR:-/home/kr/ChatOS-v2.0}"

# Check Caddyfile
if [ -f "/etc/caddy/Caddyfile" ]; then
    check_pass "Caddyfile exists at /etc/caddy/Caddyfile"
elif [ -f "$CHATOS_DIR/Caddyfile" ]; then
    check_warn "Caddyfile exists but not in /etc/caddy/"
else
    check_fail "Caddyfile not found"
fi

# Check backend files
if [ -f "$CHATOS_DIR/chatos_backend/app.py" ]; then
    check_pass "Backend app.py exists"
else
    check_fail "Backend app.py not found"
fi

# Check auth middleware
if [ -f "$CHATOS_DIR/chatos_backend/api/auth_middleware.py" ]; then
    check_pass "Auth middleware exists"
else
    check_fail "Auth middleware not found"
fi

# Check admin pages
if [ -f "$CHATOS_DIR/frontend/src/app/admin/page.tsx" ]; then
    check_pass "Admin dashboard page exists"
else
    check_fail "Admin dashboard page not found"
fi

if [ -f "$CHATOS_DIR/frontend/src/app/admin/ip-whitelist/page.tsx" ]; then
    check_pass "IP whitelist page exists"
else
    check_warn "IP whitelist page not found"
fi

echo ""

# =============================================================================
# 3. Check API Endpoints
# =============================================================================
echo "3. Checking API Endpoints..."

# Health check
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null | grep -q "200"; then
    check_pass "Backend health endpoint responding"
else
    check_warn "Backend health endpoint not responding"
fi

# Check scraped data endpoint
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/api/scraped-data?type=status 2>/dev/null | grep -q "200"; then
    check_pass "Frontend scraped-data endpoint responding"
else
    check_warn "Frontend scraped-data endpoint not responding"
fi

echo ""

# =============================================================================
# 4. Check Docker Containers (if using Docker)
# =============================================================================
echo "4. Checking Docker Scrapers..."

if command -v docker &> /dev/null; then
    # Check if any chatos containers are running
    SCRAPERS=$(docker ps --filter "name=chatos" --format "{{.Names}}" 2>/dev/null | wc -l)
    if [ "$SCRAPERS" -gt 0 ]; then
        check_pass "$SCRAPERS ChatOS containers running"
        docker ps --filter "name=chatos" --format "     - {{.Names}}: {{.Status}}" 2>/dev/null
    else
        check_warn "No ChatOS Docker containers running"
    fi
else
    check_warn "Docker not installed (scrapers may not work)"
fi

echo ""

# =============================================================================
# 5. Check Firewall
# =============================================================================
echo "5. Checking Firewall..."

if command -v ufw &> /dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null | head -1)
    if echo "$UFW_STATUS" | grep -q "active"; then
        check_pass "UFW firewall is active"
        
        # Check specific rules
        if sudo ufw status 2>/dev/null | grep -q "443.*ALLOW"; then
            check_pass "Port 443 is allowed"
        else
            check_warn "Port 443 may not be allowed"
        fi
        
        if sudo ufw status 2>/dev/null | grep -q "3000.*DENY"; then
            check_pass "Port 3000 is blocked"
        else
            check_warn "Port 3000 may not be blocked (security risk)"
        fi
    else
        check_warn "UFW firewall is not active"
    fi
else
    check_warn "UFW not installed"
fi

echo ""

# =============================================================================
# Summary
# =============================================================================
echo "========================================"
echo "Summary"
echo "========================================"
echo ""
echo -e "  ${GREEN}PASS${NC}: $PASS"
echo -e "  ${YELLOW}WARN${NC}: $WARN"
echo -e "  ${RED}FAIL${NC}: $FAIL"
echo ""

if [ $FAIL -eq 0 ] && [ $WARN -lt 3 ]; then
    echo -e "${GREEN}System looks good!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. If firewall not configured: sudo bash scripts/configure-firewall.sh"
    echo "  2. If database tables not created: python -m chatos_backend.database.init_schema"
    echo "  3. Test remote access from another device"
elif [ $FAIL -eq 0 ]; then
    echo -e "${YELLOW}System has some warnings - check above${NC}"
else
    echo -e "${RED}System has failures - please fix before using${NC}"
fi

echo ""
