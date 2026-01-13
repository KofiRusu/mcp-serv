# ChatOS Remote Access Setup Guide

This document describes the changes made to enable remote access to ChatOS, allowing Mac/Windows clients to view real-time scraped data through a single HTTPS entrypoint.

## Summary of Changes

### ✅ Completed

1. **Frontend API URL Fixes**
   - Replaced all hardcoded `localhost:8000` URLs with relative paths or environment variables
   - Updated 11 files in `sandbox-ui/src/`:
     - `lib/api.ts`
     - `lib/notes-db-api.ts`
     - `hooks/use-api.ts`
     - `hooks/use-realtime-websocket.ts`
     - `components/terminal.tsx`
     - `app/training/page.tsx`
     - `app/trading/automations/page.tsx`
     - `app/editor/page.tsx`
     - `components/automation-builder/automation-preview.tsx`
     - `components/automation-builder/ai-builder-chat.tsx`
     - `hooks/use-auto-trading.ts`

2. **WebSocket URL Auto-Detection**
   - Updated WebSocket connections to auto-detect protocol (ws/wss) and host from `window.location`
   - Fixed WebSocket path to match backend endpoint: `/api/v1/realtime/ws`
   - All WebSocket connections now work with HTTPS via reverse proxy

3. **Caddy Reverse Proxy Configuration**
   - Created `Caddyfile` template with:
     - UI routing to port 3000
     - API routing to port 8000
     - WebSocket support for realtime data, terminal, and automation streams
     - Proper proxy headers for authentication

4. **Data Pipeline Verification**
   - Verified scraper output directories match backend configuration
   - Documented REALTIME_DATA_DIR environment variable requirement

5. **Setup Script**
   - Created `scripts/setup-remote-access.sh` for easy deployment

## Architecture

```
Internet Browser
  ↓
https://chatos.yourdomain.com
  ↓
Caddy (TLS/443)
  ├─ / → Next.js UI (localhost:3000)
  ├─ /api/* → FastAPI (localhost:8000)
  └─ /api/v1/realtime/ws → WebSocket (localhost:8000)
```

**Key Principle**: All requests go through same-origin HTTPS, eliminating CORS and mixed content issues.

## Setup Instructions

### Prerequisites

- Domain name with DNS A record pointing to server IP
- Port 443 accessible from internet
- Caddy installed (`sudo apt install -y caddy`)
- Backend running on port 8000
- Frontend running on port 3000

### Step-by-Step Setup

1. **Install Caddy** (if not already installed)
   ```bash
   sudo apt update && sudo apt install -y caddy
   ```

2. **Configure Caddyfile**
   ```bash
   # Copy template to system location
   sudo cp Caddyfile /etc/caddy/Caddyfile
   
   # Edit domain name
   sudo nano /etc/caddy/Caddyfile
   # Replace 'chatos.yourdomain.com' with your actual domain
   ```

3. **Validate and Start Caddy**
   ```bash
   # Validate configuration
   sudo caddy validate --config /etc/caddy/Caddyfile
   
   # Start and enable Caddy
   sudo systemctl restart caddy
   sudo systemctl enable caddy
   ```

4. **Configure Firewall**
   ```bash
   # Allow HTTPS
   sudo ufw allow 443/tcp
   
   # Block direct access to UI and API ports
   sudo ufw deny 3000/tcp
   sudo ufw deny 8000/tcp
   
   # Verify
   sudo ufw status
   ```

5. **Configure Backend Environment**
   
   Set `REALTIME_DATA_DIR` to match scraper output:
   ```bash
   export REALTIME_DATA_DIR="/home/kr/ChatOS-v2.0/sandbox-ui/data/realtime"
   ```
   
   Or add to your backend startup script/systemd service.

6. **Rebuild Frontend**
   ```bash
   cd sandbox-ui
   npm run build
   npm start  # or use PM2/systemd
   ```

7. **Start Backend**
   ```bash
   cd /home/kr/ChatOS-v2.0
   python -m uvicorn ChatOS.app:app --host 0.0.0.0 --port 8000
   ```

8. **Start Scrapers** (if not already running)
   ```bash
   cd scrapers
   docker-compose -f docker-compose.scrapers.yml up -d
   ```

### Automated Setup

Use the provided setup script:
```bash
cd /home/kr/ChatOS-v2.0
sudo bash scripts/setup-remote-access.sh
```

## Validation

### Server-Side Checks

1. **Check Caddy status**
   ```bash
   sudo systemctl status caddy
   ```

2. **Test API directly**
   ```bash
   curl http://localhost:8000/api/health
   ```

3. **Test API through Caddy**
   ```bash
   curl -k https://chatos.yourdomain.com/api/health
   ```

4. **Test realtime data endpoint**
   ```bash
   curl -k https://chatos.yourdomain.com/api/v1/realtime/dashboard
   ```

5. **Check listeners**
   ```bash
   ss -tulpn | grep -E ':(443|3000|8000)'
   ```
   - Port 443 should be listening on public interface
   - Ports 3000/8000 can be localhost only (firewalled)

### Client-Side Checks (from Mac/remote)

1. **Open UI**
   - Navigate to: `https://chatos.yourdomain.com`
   - Should load without errors

2. **Check Network Tab** (Browser DevTools)
   - All API calls should be to: `https://chatos.yourdomain.com/api/...`
   - No `localhost` or different-origin requests

3. **Check WebSocket Connection**
   - Open DevTools → Network → WS filter
   - Should connect to: `wss://chatos.yourdomain.com/api/v1/realtime/ws`
   - Status should be "101 Switching Protocols"

4. **Verify Real-time Data**
   - Watch a data panel update
   - Reload page - data should appear (not stuck/cached)

## Environment Variables

### Frontend (`sandbox-ui/.env.local`)

```bash
# Empty = same-origin (recommended for production)
NEXT_PUBLIC_API_URL=
NEXT_PUBLIC_WS_URL=
```

### Backend

```bash
# Point to scraper data directory
REALTIME_DATA_DIR=/home/kr/ChatOS-v2.0/sandbox-ui/data/realtime
```

## Troubleshooting

### Issue: "Connection refused" or "Connection reset"

**Cause**: Backend/UI not running or ports not accessible to Caddy

**Fix**:
- Verify services are running: `ps aux | grep -E '(uvicorn|next)'`
- Check services are bound to `0.0.0.0` or `127.0.0.1` (not just external IP)
- Verify ports: `ss -tulpn | grep -E ':(3000|8000)'`

### Issue: WebSocket connection fails

**Cause**: Caddy not configured for WebSocket upgrade

**Fix**:
- Check Caddyfile has WebSocket routes with `header_up Upgrade "websocket"`
- Verify backend endpoint path matches: `/api/v1/realtime/ws`
- Check browser console for WebSocket errors

### Issue: "Mixed content" or CORS errors

**Cause**: Frontend still calling `http://localhost:8000` directly

**Fix**:
- Rebuild frontend: `cd sandbox-ui && npm run build`
- Check environment variables are set correctly
- Verify browser cache is cleared

### Issue: No real-time data updates

**Cause**: Backend not reading from scraper data directory

**Fix**:
- Set `REALTIME_DATA_DIR` environment variable
- Verify scrapers are writing to correct directories
- Check backend logs for data loading errors
- Alternative: Configure scrapers to POST to `/api/v1/realtime/ingest/*` endpoints

### Issue: Caddy won't start

**Cause**: Invalid Caddyfile or port conflict

**Fix**:
- Validate: `sudo caddy validate --config /etc/caddy/Caddyfile`
- Check logs: `sudo journalctl -u caddy -n 50`
- Ensure port 443 is not in use: `ss -tulpn | grep :443`

## Security Considerations

1. **HTTPS Only**: All traffic goes through HTTPS (Caddy auto-configures Let's Encrypt)
2. **Port Isolation**: UI and API ports are not directly accessible from internet
3. **Authentication**: If using Keycloak, ensure redirect URIs match public domain
4. **Rate Limiting**: Consider adding rate limiting to Caddy configuration
5. **Basic Auth**: Optional basic auth can be enabled in Caddyfile for beta testing

## Rollback

If you need to revert changes:

1. Stop Caddy: `sudo systemctl stop caddy`
2. Remove Caddyfile: `sudo rm /etc/caddy/Caddyfile`
3. Revert frontend changes: `cd sandbox-ui && git checkout .`
4. Rebuild frontend: `npm run build`
5. Re-open firewall ports if needed

## Files Modified

- `sandbox-ui/src/lib/api.ts`
- `sandbox-ui/src/lib/notes-db-api.ts`
- `sandbox-ui/src/hooks/use-api.ts`
- `sandbox-ui/src/hooks/use-realtime-websocket.ts`
- `sandbox-ui/src/components/terminal.tsx`
- `sandbox-ui/src/app/training/page.tsx`
- `sandbox-ui/src/app/trading/automations/page.tsx`
- `sandbox-ui/src/app/editor/page.tsx`
- `sandbox-ui/src/components/automation-builder/automation-preview.tsx`
- `sandbox-ui/src/components/automation-builder/ai-builder-chat.tsx`
- `sandbox-ui/src/hooks/use-auto-trading.ts`

## Files Created

- `Caddyfile` - Reverse proxy configuration template
- `scripts/setup-remote-access.sh` - Automated setup script
- `REMOTE_ACCESS_SETUP.md` - This documentation

## Next Steps

1. ✅ Configure domain name in Caddyfile
2. ✅ Set up DNS A record
3. ✅ Install and configure Caddy
4. ✅ Configure firewall
5. ✅ Rebuild and restart services
6. ⏳ Test from remote client
7. ⏳ Configure Keycloak (if using authentication)

## Support

For issues or questions:
- Check Caddy logs: `sudo journalctl -u caddy -f`
- Check backend logs: Look for FastAPI/uvicorn logs
- Check browser console for client-side errors
- Verify network connectivity and DNS resolution
