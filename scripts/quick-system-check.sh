#!/bin/bash
# =============================================================================
# ChatOS v2.0 Quick System Check
# =============================================================================
# Run this script to verify all system components are operational
# Usage: bash scripts/quick-system-check.sh
# =============================================================================

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "========================================"
echo "  ChatOS v2.0 System Validation"
echo "========================================"
echo ""

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

check_pass() {
    echo -e "   ${GREEN}✓${NC} $1"
    ((PASS_COUNT++))
}

check_fail() {
    echo -e "   ${RED}✗${NC} $1"
    ((FAIL_COUNT++))
}

check_warn() {
    echo -e "   ${YELLOW}⚠${NC} $1"
    ((WARN_COUNT++))
}

# =============================================================================
# 1. Service Checks
# =============================================================================
echo "1. SERVICE STATUS"
echo "   ─────────────────────────────"

# Caddy
if systemctl is-active --quiet caddy 2>/dev/null; then
    check_pass "Caddy reverse proxy: Running"
else
    check_fail "Caddy reverse proxy: Not running"
fi

# Backend on 8000
if curl -s http://localhost:8000/api/health | grep -q "healthy" 2>/dev/null; then
    check_pass "Backend API (8000): Healthy"
else
    check_fail "Backend API (8000): Not responding"
fi

# Frontend on 3000
if curl -s http://localhost:3000 2>/dev/null | grep -q "ChatOS"; then
    check_pass "Frontend (3000): Running"
else
    check_fail "Frontend (3000): Not responding"
fi

# Docker
if systemctl is-active --quiet docker 2>/dev/null; then
    check_pass "Docker daemon: Running"
else
    check_warn "Docker daemon: Not running"
fi

# Docker containers
CONTAINER_COUNT=$(docker ps -q 2>/dev/null | wc -l)
if [ "$CONTAINER_COUNT" -gt 0 ]; then
    check_pass "Docker containers: $CONTAINER_COUNT running"
else
    check_warn "Docker containers: None running (scrapers stopped)"
fi

echo ""

# =============================================================================
# 2. Database Check
# =============================================================================
echo "2. DATABASE STATUS"
echo "   ─────────────────────────────"

DB_PATH="/home/kr/ChatOS-v2.0/data/chatos.db"
if [ -f "$DB_PATH" ]; then
    DB_SIZE=$(du -h "$DB_PATH" | cut -f1)
    check_pass "Database file: Exists ($DB_SIZE)"
else
    check_fail "Database file: Missing"
fi

echo ""

# =============================================================================
# 3. Network Access
# =============================================================================
echo "3. NETWORK ACCESS"
echo "   ─────────────────────────────"

# Localhost via Caddy
if curl -s http://localhost/ 2>/dev/null | grep -q "ChatOS"; then
    check_pass "Localhost (port 80): Accessible"
else
    check_fail "Localhost (port 80): Not accessible"
fi

# Public IP
PUBLIC_IP="192.168.0.249"
if curl -s --connect-timeout 5 http://$PUBLIC_IP/ 2>/dev/null | grep -q "ChatOS"; then
    check_pass "Public IP ($PUBLIC_IP): Accessible"
else
    check_warn "Public IP ($PUBLIC_IP): Not accessible from localhost"
fi

echo ""

# =============================================================================
# 4. API Endpoints
# =============================================================================
echo "4. API ENDPOINTS"
echo "   ─────────────────────────────"

# Health
if curl -s http://localhost/api/health | grep -q "healthy" 2>/dev/null; then
    check_pass "GET /api/health: OK"
else
    check_fail "GET /api/health: Failed"
fi

# Council
if curl -s http://localhost/api/council 2>/dev/null | head -1 | grep -q "{" ; then
    check_pass "GET /api/council: OK"
else
    check_warn "GET /api/council: No response"
fi

# Scraped data
if curl -s "http://localhost/api/scraped-data?type=status" 2>/dev/null | head -1 | grep -q "{"; then
    check_pass "GET /api/scraped-data: OK"
else
    check_warn "GET /api/scraped-data: No response"
fi

echo ""

# =============================================================================
# 5. File System
# =============================================================================
echo "5. FILE SYSTEM"
echo "   ─────────────────────────────"

# Symlink
if [ -L "/home/kr/ChatOS-v2.0" ]; then
    TARGET=$(readlink -f /home/kr/ChatOS-v2.0)
    check_pass "Symlink: /home/kr/ChatOS-v2.0 → $TARGET"
else
    check_warn "Symlink: Not configured (using direct path)"
fi

# Data directories
if [ -d "/home/kr/ChatOS-v2.0/frontend/data" ]; then
    check_pass "Data directory: Exists"
else
    check_warn "Data directory: Missing"
fi

# Logs directory
if [ -d "/home/kr/ChatOS-v2.0/logs" ]; then
    check_pass "Logs directory: Exists"
else
    check_warn "Logs directory: Missing"
fi

echo ""

# =============================================================================
# 6. Frontend Build
# =============================================================================
echo "6. FRONTEND BUILD"
echo "   ─────────────────────────────"

if [ -d "/home/kr/ChatOS-v2.0/frontend/.next" ]; then
    check_pass "Next.js build: Present"
else
    check_warn "Next.js build: Not found (may need npm run build)"
fi

# Check if ignoreBuildErrors is disabled
if grep -q "ignoreBuildErrors: true" /home/kr/ChatOS-v2.0/frontend/next.config.ts 2>/dev/null; then
    check_warn "TypeScript: ignoreBuildErrors is enabled"
else
    check_pass "TypeScript: Full validation enabled"
fi

echo ""

# =============================================================================
# Summary
# =============================================================================
echo "========================================"
echo "  SUMMARY"
echo "========================================"
echo ""
echo -e "   ${GREEN}Passed:${NC}   $PASS_COUNT"
echo -e "   ${YELLOW}Warnings:${NC} $WARN_COUNT"
echo -e "   ${RED}Failed:${NC}   $FAIL_COUNT"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "   ${GREEN}System Status: READY${NC}"
    exit 0
elif [ $FAIL_COUNT -le 2 ]; then
    echo -e "   ${YELLOW}System Status: PARTIAL - Some issues need attention${NC}"
    exit 1
else
    echo -e "   ${RED}System Status: CRITICAL - Multiple failures${NC}"
    exit 2
fi
