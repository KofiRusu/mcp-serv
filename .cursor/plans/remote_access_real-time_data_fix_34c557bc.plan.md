---
name: Remote Access Real-time Data Fix
overview: Configure ChatOS for remote access so Mac/Windows clients can view real-time scraped data through a single HTTPS entrypoint via Caddy reverse proxy, ensuring same-origin API calls and fixing hardcoded localhost URLs throughout the frontend.
todos:
  - id: install-caddy
    content: Install Caddy reverse proxy server and create Caddyfile configuration
    status: completed
  - id: configure-caddy
    content: Configure Caddyfile with reverse proxy rules for UI (port 3000) and API (port 8000), including WebSocket support
    status: completed
    dependencies:
      - install-caddy
  - id: fix-api-urls
    content: Replace all hardcoded 'localhost:8000' API base URLs in frontend with relative '/api' paths
    status: completed
  - id: fix-websocket-urls
    content: Update WebSocket connection logic to use wss:// for HTTPS and auto-detect host from window.location
    status: completed
  - id: configure-firewall
    content: Secure firewall to allow only port 443 (HTTPS) and block direct access to 3000/8000
    status: completed
    dependencies:
      - configure-caddy
  - id: verify-data-pipeline
    content: Verify scrapers and backend share same data directory/volume, and RealtimeDataStore reads from scraper output
    status: completed
  - id: update-env-config
    content: Update/create .env.local.example to document same-origin API configuration
    status: completed
    dependencies:
      - fix-api-urls
  - id: validate-remote-access
    content: "Test remote access from Mac/client: verify HTTPS UI loads, API calls are same-origin, WebSocket connects, real-time data updates"
    status: completed
    dependencies:
      - configure-caddy
      - fix-api-urls
      - fix-websocket-urls
      - configure-firewall
---

# Remote Access Real-time Data Implementation Plan

## Current Architecture Analysis

**Components:**

- **Backend**: FastAPI on port 8000 (`ChatOS/app.py`)
- **Frontend**: Next.js `sandbox-ui` (primary UI, port 3000)
- **Scrapers**: Docker containers writing to `/home/kr/ChatOS-v2.0/sandbox-ui/data/`
- **Realtime Store**: `ChatOS/services/realtime_data_store.py` (in-memory, can read from filesystem)
- **Data Flow**: Scrapers → JSON files → `RealtimeDataStore` → FastAPI routes → WebSocket/REST → React UI

**Issues Found:**

1. Frontend hardcodes `localhost:8000` in 262+ locations
2. WebSocket uses `ws://localhost:8000` (should be `wss://` for HTTPS)
3. No reverse proxy (Caddy) configured
4. Ports 3000/8000 likely exposed to public
5. API base URLs use `NEXT_PUBLIC_API_URL` but default to `localhost:8000`

## Implementation Phases

### Phase 1: Install and Configure Caddy Reverse Proxy

**Files to create/modify:**

- `/etc/caddy/Caddyfile` (new)

**Configuration:**

```caddy
chatos.yourdomain.com {
    # UI -> Next.js
    reverse_proxy / localhost:3000

    # API -> FastAPI (everything under /api goes to backend)
    reverse_proxy /api/* localhost:8000

    # WebSocket upgrade support for realtime data
    reverse_proxy /ws/* localhost:8000 {
        header_up Connection "Upgrade"
        header_up Upgrade "websocket"
    }

    # Proxy headers for correct URL building
    header {
        X-Forwarded-Proto {scheme}
        X-Forwarded-Host {host}
    }
}
```

**Actions:**

1. Install Caddy: `sudo apt update && sudo apt install -y caddy`
2. Create `/etc/caddy/Caddyfile` with above config
3. Validate: `sudo caddy validate --config /etc/caddy/Caddyfile`
4. Enable/start: `sudo systemctl enable caddy && sudo systemctl restart caddy`

**Prerequisites:**

- Domain name configured (DNS A record pointing to server IP)
- Port 443 accessible (or use Let's Encrypt for automatic HTTPS)

---

### Phase 2: Fix Frontend API Base URLs

**Files to modify:**

1. `sandbox-ui/src/lib/api.ts` - Replace `localhost:8000` with relative `/api`
2. `sandbox-ui/src/lib/notes-db-api.ts` - Same
3. `sandbox-ui/src/hooks/use-api.ts` - Same
4. `sandbox-ui/src/components/terminal.tsx` - Same
5. `sandbox-ui/src/hooks/use-realtime-websocket.ts` - Fix WebSocket URL
6. `sandbox-ui/src/app/training/page.tsx` - Replace hardcoded URL
7. `sandbox-ui/src/app/trading/automations/page.tsx` - Replace hardcoded URLs
8. `sandbox-ui/src/app/editor/page.tsx` - Replace hardcoded URLs
9. `sandbox-ui/src/components/automation-builder/automation-preview.tsx` - Fix WebSocket URL
10. `sandbox-ui/src/components/automation-builder/ai-builder-chat.tsx` - Replace hardcoded URLs
11. `sandbox-ui/src/hooks/use-auto-trading.ts` - Replace hardcoded URL

**Pattern to implement:**

```typescript
// Before:
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// After:
const API_BASE = process.env.NEXT_PUBLIC_API_URL || '' // Empty = same origin

// WebSocket:
// Before:
const DEFAULT_WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws/realtime'

// After:
const getWebSocketUrl = () => {
  if (typeof window === 'undefined') return ''
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  return process.env.NEXT_PUBLIC_WS_URL || `${protocol}//${host}/ws/realtime`
}
```

**Environment variables:**

- Update `sandbox-ui/.env.local.example` (create if missing) to document:
  - `NEXT_PUBLIC_API_URL=""` (empty for same-origin)
  - `NEXT_PUBLIC_WS_URL=""` (empty for auto-detection)

---

### Phase 3: Verify Backend WebSocket Path Configuration

**Files to check:**

- `ChatOS/app.py` - Ensure WebSocket routes are registered
- `ChatOS/api/routes_realtime_data.py` - Verify `/api/v1/realtime/ws` endpoint

**Expected endpoint:** `/api/v1/realtime/ws` (matches frontend `use-realtime-websocket.ts`)

**Action:** Ensure backend WebSocket is accessible at `ws://localhost:8000/api/v1/realtime/ws` (Caddy will proxy `/ws/*` to backend)

**Note:** Caddyfile routes `/ws/*` to port 8000, so `wss://chatos.yourdomain.com/ws/realtime` will become `ws://localhost:8000/ws/realtime` on backend. Adjust Caddyfile if backend expects `/api/v1/realtime/ws`.

---

### Phase 4: Secure Firewall Configuration

**Actions:**

1. Block public access to ports 3000, 8000:
   ```bash
   sudo ufw allow 443/tcp
   sudo ufw deny 3000/tcp
   sudo ufw deny 8000/tcp
   sudo ufw status
   ```

2. Ensure localhost access remains (for Caddy):

   - Services should bind to `127.0.0.1:8000` or `0.0.0.0:8000` (Caddy can access both)

---

### Phase 5: Verify Scraper-Backend Data Pipeline

**Current state:**

- Scrapers write to: `/home/kr/ChatOS-v2.0/sandbox-ui/data/{market-history,news,sentiment,aggr,coinglass}/`
- `RealtimeDataStore` can read from filesystem (via `REALTIME_DATA_DIR` env var) but defaults to in-memory

**Files to check/modify:**

- `ChatOS/services/realtime_data_store.py` - Verify data directory configuration
- `scrapers/docker-compose.scrapers.yml` - Verify volume mounts point to correct paths

**Actions:**

1. Ensure `RealtimeDataStore` reads from scraper output directories
2. Set environment variable in backend: `REALTIME_DATA_DIR=/home/kr/ChatOS-v2.0/sandbox-ui/data/realtime` (or point to news/sentiment dirs)
3. Verify scraper containers mount correct host paths

**Alternative:** Configure scrapers to POST to backend ingestion endpoints (`/api/v1/realtime/ingest/news`, `/api/v1/realtime/ingest/sentiment`) instead of just writing files. This ensures real-time updates via WebSocket.

---

### Phase 6: Keycloak Configuration (if applicable)

**If using Keycloak for auth:**

1. Update Keycloak client settings:

   - Valid Redirect URIs: `https://chatos.yourdomain.com/*`
   - Web Origins: `https://chatos.yourdomain.com`

2. Update Keycloak issuer URL to public domain (not localhost)
3. Add Keycloak proxy route to Caddyfile:
   ```caddy
   reverse_proxy /auth/* localhost:8080
   ```


---

### Phase 7: Update Docker Compose for Production

**Files to modify:**

- `docker-compose.yml` - Ensure backend binds to `0.0.0.0:8000` (for Caddy access)

**Check:**

- Backend container exposes port 8000 to host
- Next.js runs on port 3000 (or configure via env var)

---

### Phase 8: Validation & Testing

**Linux server validation:**

1. Check listeners: `ss -tulpn | grep -E ':(443|3000|8000)'`
2. Test API directly: `curl -s http://localhost:8000/api/v1/realtime/dashboard`
3. Test through Caddy: `curl -sk https://chatos.yourdomain.com/api/v1/realtime/dashboard`
4. Verify WebSocket: `wscat -c wss://chatos.yourdomain.com/ws/realtime` (or use browser DevTools)

**Mac/remote client validation:**

1. Open `https://chatos.yourdomain.com`
2. DevTools → Network → Verify all API calls go to `https://chatos.yourdomain.com/api/...`
3. Verify WebSocket connects to `wss://chatos.yourdomain.com/ws/realtime`
4. Confirm real-time data updates appear

**Prerequisites checklist:**

- [ ] Domain DNS A record points to server IP
- [ ] Port 443 open in firewall
- [ ] Caddy installed and running
- [ ] Backend running on port 8000
- [ ] Next.js UI running on port 3000
- [ ] Scrapers running and producing data
- [ ] Frontend rebuilt with new API URLs

---

## Files Summary

**New files:**

- `/etc/caddy/Caddyfile`
- `sandbox-ui/.env.local.example` (optional, for documentation)

**Modified files (estimated ~15 files):**

- Frontend API client files (11 files with hardcoded URLs)
- Docker compose files (if needed)
- Environment configuration files

**Commands to run:**

1. `sudo apt install -y caddy`
2. Create/edit Caddyfile
3. `sudo caddy validate --config /etc/caddy/Caddyfile`
4. `sudo systemctl restart caddy`
5. `sudo ufw allow 443/tcp && sudo ufw deny 3000/tcp && sudo ufw deny 8000/tcp`
6. Rebuild frontend: `cd sandbox-ui && npm run build`
7. Restart services as needed

---

## Rollback Plan

1. Remove/rename `/etc/caddy/Caddyfile`
2. `sudo systemctl stop caddy`
3. Revert frontend changes (git checkout)
4. Rebuild frontend
5. Re-open firewall ports if needed