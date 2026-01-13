# ChatOS v2.0 Admin Server - Full Deployment & Validation Plan

**Created**: January 13, 2026  
**Purpose**: Comprehensive validation to ensure all systems are properly configured and ready for production deployment

---

## System Overview

| Component | Location | Status |
|-----------|----------|--------|
| **Frontend** | `/home/kr/ChatOS-v2.0/frontend` | Next.js 16 - TypeScript clean |
| **Backend** | `/home/kr/ChatOS-v2.0/chatos_backend` | FastAPI on port 8000 |
| **Reverse Proxy** | Caddy on port 80 | Running via systemd |
| **Database** | SQLite at `data/chatos.db` | Needs verification |
| **Scrapers** | Docker containers | NOT running |
| **Real Disk Path** | `/media/kr/918386b7-.../home/kr/ChatOS-v2.0/` | 4TB disk |
| **Symlink** | `/home/kr/ChatOS-v2.0` → disk path | Active |

---

## Phase 1: Infrastructure Validation ✅ VERIFY

### 1.1 Network & Services Status

```bash
# Check all running services
systemctl status caddy
lsof -i :80 -i :3000 -i :8000

# Test internal connectivity
curl -s http://localhost:8000/api/health
curl -s http://localhost:3000 | head -20
curl -s http://localhost:80 | head -20

# Test external access (from the server itself)
curl -s http://192.168.0.249/ | head -20
```

### 1.2 Firewall Configuration

```bash
# Check current firewall status
sudo ufw status verbose

# If not configured, run:
sudo bash /home/kr/ChatOS-v2.0/scripts/configure-firewall.sh

# Expected rules:
# - Port 22 (SSH): ALLOW
# - Port 80 (HTTP): ALLOW (or 443 for HTTPS)
# - Port 3000: DENY (internal only)
# - Port 8000: DENY (internal only)
```

### 1.3 Caddy Reverse Proxy

```bash
# Verify Caddy config
cat /etc/caddy/Caddyfile

# Test Caddy reload
sudo caddy validate --config /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

**Required Routes:**
- `/api/*` → `localhost:8000`
- `/api/v1/realtime/ws` → WebSocket upgrade to 8000
- `/_next/*` → `localhost:3000`
- `/*` (default) → `localhost:3000`

---

## Phase 2: Database Initialization

### 2.1 Check Existing Database

```bash
cd /home/kr/ChatOS-v2.0

# Check if database exists
ls -la data/*.db

# Verify tables (if sqlite3 is available)
sqlite3 data/chatos.db ".tables"
sqlite3 data/chatos.db ".schema"
```

### 2.2 Initialize Database Schema

```bash
cd /home/kr/ChatOS-v2.0
source .venv/bin/activate

# Run schema initialization
python -c "from chatos_backend.database import init_db; init_db()"

# Or using the CLI
python -m chatos_backend.database.init_schema
```

### 2.3 Verify Tables Exist

Expected tables:
- `users`, `sessions` (auth)
- `notes`, `transcripts`, `action_items` (notes)
- `trades`, `journal_entries` (trading)
- `conversations`, `messages` (chat)
- `backtests`, `strategies` (trading lab)
- `ip_whitelist`, `audit_log` (admin)

---

## Phase 3: Docker & Scrapers Setup

### 3.1 Verify Docker Installation

```bash
# Check Docker daemon
sudo systemctl status docker
docker info | grep "Docker Root Dir"

# Expected: /media/kr/.../Desktop/docker-data
```

### 3.2 Start Docker Scrapers

```bash
cd /home/kr/ChatOS-v2.0

# Check scraper compose file
cat scrapers/docker-compose.scrapers.yml

# Start scrapers
cd scrapers && docker-compose -f docker-compose.scrapers.yml up -d

# Verify containers running
docker ps
```

**Expected Scrapers:**
| Container | Purpose | Interval |
|-----------|---------|----------|
| market-scraper | OHLCV, orderbooks | 30s |
| news-scraper | Crypto news | 5min |
| sentiment-scraper | Fear & Greed | 10min |
| aggr-agent | CVD, whale detection | 1s |
| coinglass-agent | OI, funding, liquidations | 60s |

### 3.3 Verify Data Flow

```bash
# Check data directories are being populated
ls -la /home/kr/ChatOS-v2.0/frontend/data/
ls -la /home/kr/ChatOS-v2.0/frontend/data/market-history/
ls -la /home/kr/ChatOS-v2.0/frontend/data/sentiment/
```

---

## Phase 4: Backend Tests

### 4.1 Install Test Dependencies

```bash
cd /home/kr/ChatOS-v2.0
source .venv/bin/activate

pip install pytest pytest-asyncio httpx --break-system-packages
```

### 4.2 Run API Tests

```bash
# Run core API tests
pytest tests/test_api.py -v

# Run all backend tests (exclude E2E)
pytest tests/ -v --ignore=tests/test_e2e.py

# Run with coverage
pytest tests/ --cov=chatos_backend --cov-report=html
```

### 4.3 Expected Test Results

| Test File | Purpose | Expected |
|-----------|---------|----------|
| test_api.py | Core API routes | PASS |
| test_notes_db.py | Note storage | PASS |
| test_transcripts.py | Audio pipeline | PASS |
| test_rag.py | RAG retrieval | PASS |
| test_memory.py | Memory system | PASS |
| test_ollama.py | LLM integration | PASS |

---

## Phase 5: Frontend Validation

### 5.1 Build Verification (COMPLETED)

```bash
cd /home/kr/ChatOS-v2.0/frontend

# TypeScript build - should pass clean
npm run build

# Expected: Build successful, no TypeScript errors
```

### 5.2 Page Load Tests

Test each page loads without JS errors:

| Page | URL | Expected |
|------|-----|----------|
| Chat | `/` | Welcome message, model selector |
| Trading | `/trading` | Chart, price feeds |
| Automations | `/editor` | Block editor |
| Notes | `/notes` | Note list |
| Diary | `/diary` | Audio upload, transcripts |
| Sandbox | `/sandbox` | Code editor |
| Admin | `/admin` | System status |
| IP Whitelist | `/admin/ip-whitelist` | IP management |
| Monitoring | `/admin/monitoring` | Health metrics |
| Sessions | `/admin/sessions` | Active sessions |
| Trading Journal | `/trading/journal` | Trade log |
| Trading Lab | `/trading/lab` | Backtest form |
| Training | `/training` | Model training UI |

### 5.3 Browser Console Check

```javascript
// In browser DevTools (F12 → Console)
// Should show NO red errors

// Check API connectivity
fetch('/api/health').then(r => r.json()).then(console.log)
// Expected: {status: "healthy", version: "2.0.0", ...}
```

---

## Phase 6: E2E Tests

### 6.1 Install Playwright

```bash
cd /home/kr/ChatOS-v2.0
source .venv/bin/activate

pip install playwright --break-system-packages
playwright install chromium
```

### 6.2 Update E2E Test File

The test file needs updating for current page structure.

**Key Changes Needed:**
1. Base URL: `localhost:80` (via Caddy) or `localhost:3000` (direct)
2. Add tests for all 14 pages
3. Remove tests for non-existent pages

### 6.3 Run E2E Tests

```bash
pytest tests/test_e2e.py -v
```

---

## Phase 7: API Endpoint Validation

### 7.1 Health Endpoints

```bash
# Backend health
curl -s http://localhost/api/health | jq

# Council status
curl -s http://localhost/api/council | jq
```

### 7.2 Admin Endpoints

```bash
# Monitoring
curl -s http://localhost/api/v1/admin/monitoring/health | jq
curl -s http://localhost/api/v1/admin/monitoring/sessions | jq

# IP Whitelist
curl -s http://localhost/api/v1/admin/whitelist | jq
```

### 7.3 Data Endpoints

```bash
# Scraped data status
curl -s "http://localhost/api/scraped-data?type=status" | jq
curl -s "http://localhost/api/scraped-data?type=sentiment" | jq

# Market data
curl -s http://localhost/api/v1/realtime/dashboard | jq
```

### 7.4 Notes/Diary Endpoints

```bash
# Notes
curl -s http://localhost/api/notes | jq
curl -s http://localhost/api/notes/db | jq

# Transcripts
curl -s http://localhost/api/transcripts | jq
```

### 7.5 Trading Endpoints

```bash
# Market data
curl -s http://localhost/api/market | jq
curl -s "http://localhost/api/market-data/summary" | jq

# Paper trading
curl -s http://localhost/api/paper-trading | jq

# Backtest
curl -s http://localhost/api/backtest/history | jq
```

---

## Phase 8: WebSocket Validation

### 8.1 Test WebSocket Connection

```bash
# Install websocat if needed
# apt install websocat

# Test realtime WebSocket
websocat ws://localhost/api/v1/realtime/ws

# Or use Python
python -c "
import asyncio
import websockets

async def test():
    async with websockets.connect('ws://localhost/api/v1/realtime/ws') as ws:
        print('Connected!')
        data = await ws.recv()
        print(f'Received: {data}')

asyncio.run(test())
"
```

### 8.2 Frontend WebSocket Integration

In browser console:
```javascript
// Test WebSocket from frontend
const ws = new WebSocket('ws://localhost/api/v1/realtime/ws');
ws.onopen = () => console.log('WS Connected');
ws.onmessage = (e) => console.log('WS Data:', e.data);
ws.onerror = (e) => console.error('WS Error:', e);
```

---

## Phase 9: Security Checklist

### 9.1 Access Control

- [ ] Frontend bound to 127.0.0.1:3000 (localhost only)
- [ ] Backend bound to 127.0.0.1:8000 (localhost only)
- [ ] Caddy is only public-facing service (port 80)
- [ ] UFW blocks direct access to 3000, 8000
- [ ] SSH (22) remains accessible

### 9.2 Admin Functions

- [ ] `/admin/ip-whitelist` - Can add/remove IPs
- [ ] `/admin/sessions` - Can view/terminate sessions
- [ ] `/admin/monitoring` - Shows system health

### 9.3 Environment Variables

```bash
# Check .env files exist and are not in git
cat .gitignore | grep -i env

# Verify sensitive values are set
grep -i "secret\|key\|password" config/.env.production
```

---

## Phase 10: Startup Scripts Validation

### 10.1 Development Mode

```bash
# Test start-dev.sh
cd /home/kr/ChatOS-v2.0
bash scripts/start-dev.sh

# Verify:
# - Backend starts on 8000
# - Frontend starts on 3000
# - Hot reload enabled
```

### 10.2 Production Mode

```bash
# Test start-prod.sh
cd /home/kr/ChatOS-v2.0
bash scripts/start-prod.sh

# Verify:
# - Backend starts with 4 workers
# - Frontend is pre-built
# - Caddy routes correctly
```

### 10.3 Stop All

```bash
# Test stop-all.sh
bash scripts/stop-all.sh

# Verify all processes stopped
lsof -i :3000 -i :8000
```

---

## Quick Validation Commands

Run all these to verify system is ready:

```bash
#!/bin/bash
# Quick system check script

echo "=== ChatOS v2.0 System Check ==="
echo ""

echo "1. Caddy Status:"
systemctl is-active caddy && echo "   ✓ Running" || echo "   ✗ Not running"

echo ""
echo "2. Backend Health:"
curl -s http://localhost:8000/api/health | grep -q healthy && echo "   ✓ Healthy" || echo "   ✗ Not responding"

echo ""
echo "3. Frontend Status:"
curl -s http://localhost:3000 | grep -q ChatOS && echo "   ✓ Running" || echo "   ✗ Not responding"

echo ""
echo "4. Public Access:"
curl -s http://192.168.0.249/ | grep -q ChatOS && echo "   ✓ Accessible" || echo "   ✗ Not accessible"

echo ""
echo "5. Docker Scrapers:"
docker ps --format "{{.Names}}" 2>/dev/null | grep -q scraper && echo "   ✓ Running" || echo "   ✗ Not running"

echo ""
echo "6. Database:"
[ -f /home/kr/ChatOS-v2.0/data/chatos.db ] && echo "   ✓ Exists" || echo "   ✗ Missing"

echo ""
echo "=== Check Complete ==="
```

---

## Post-Deployment Monitoring

### Log Locations

| Log | Path |
|-----|------|
| Backend | `/home/kr/ChatOS-v2.0/logs/*.log` |
| Frontend | `npm run dev` output / Next.js logs |
| Caddy | `journalctl -u caddy -f` |
| Docker | `docker logs -f <container>` |

### Health Monitoring Commands

```bash
# Watch backend logs
tail -f /home/kr/ChatOS-v2.0/logs/*.log

# Watch Caddy logs
journalctl -u caddy -f

# Watch all Docker scraper logs
docker logs -f chatos-market-scraper
```

---

## Success Criteria

| Requirement | Status |
|-------------|--------|
| TypeScript builds clean | ✅ DONE |
| Backend API responds | ✅ VERIFIED |
| Frontend loads | ✅ VERIFIED |
| Caddy routes correctly | ✅ VERIFIED |
| Database initialized | ⏳ VERIFY |
| Docker scrapers running | ❌ START |
| Backend tests pass | ⏳ RUN |
| E2E tests pass | ⏳ UPDATE & RUN |
| All 14 pages load | ⏳ VERIFY |
| WebSockets work | ⏳ TEST |
| Security configured | ⏳ VERIFY |
| Startup scripts work | ⏳ TEST |

---

## Execution Order

1. **Immediate**: Start Docker scrapers
2. **Immediate**: Verify database schema
3. **Short-term**: Run backend tests
4. **Short-term**: Test all API endpoints
5. **Short-term**: Verify all pages load
6. **Medium-term**: Update and run E2E tests
7. **Medium-term**: Configure firewall if not done
8. **Final**: Document any remaining issues

---

*Last Updated: January 13, 2026*
