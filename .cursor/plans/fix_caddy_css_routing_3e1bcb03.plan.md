---
name: Fix Caddy CSS Routing
overview: Fix the Caddyfile configuration so that all frontend assets (CSS, JS, fonts) are properly proxied to the Next.js server, not just the root path.
todos:
  - id: fix-caddyfile
    content: Update /etc/caddy/Caddyfile with proper handle blocks for routing
    status: pending
  - id: reload-caddy
    content: Reload Caddy service to apply changes
    status: pending
  - id: verify-assets
    content: Verify CSS/JS assets load correctly through Caddy
    status: pending
---

# Fix Caddy Reverse Proxy Configuration

## Problem

The current Caddyfile uses `reverse_proxy / localhost:3000` which only matches the **exact** path `/`.

This means `/_next/static/chunks/*.css` and other asset paths return empty responses.

## Solution

Update the Caddyfile to use proper route ordering with `handle` blocks:

1. Handle `/api/*` routes first (send to backend on port 8000)
2. Handle everything else as a fallback (send to frontend on port 3000)

## Changes Required

Update [/etc/caddy/Caddyfile](/etc/caddy/Caddyfile):

```caddy
:80 {
    # API routes -> FastAPI backend
    handle /api/* {
        reverse_proxy localhost:8000
    }
    
    # WebSocket routes
    handle /api/v1/realtime/ws {
        reverse_proxy localhost:8000 {
            header_up Connection "Upgrade"
            header_up Upgrade "websocket"
        }
    }
    
    # Everything else -> Next.js frontend (including /_next/*)
    handle {
        reverse_proxy localhost:3000
    }
}
```

## After Fix

- `http://192.168.0.249/` → loads HTML ✓
- `http://192.168.0.249/_next/static/chunks/*.css` → loads CSS ✓
- `http://192.168.0.249/_next/static/chunks/*.js` → loads JS ✓
- `http://192.168.0.249/api/*` → backend API ✓