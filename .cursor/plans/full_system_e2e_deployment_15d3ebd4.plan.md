---
name: Full System E2E Deployment
overview: Complete end-to-end deployment plan that consolidates all previous plans, adds Keycloak authentication, configures Caddy routing, verifies database setup, and ensures all pages are fully functional for remote IP access.
todos:
  - id: keycloak-deploy
    content: Deploy Keycloak via Docker with persistent storage
    status: completed
  - id: keycloak-configure
    content: Configure Keycloak realm, client, and users
    status: completed
  - id: caddy-keycloak
    content: Update Caddy to route /auth/* to Keycloak
    status: completed
  - id: backend-env
    content: Configure backend with Keycloak environment variables
    status: completed
  - id: db-verify
    content: Verify all auth/logging database tables exist and work
    status: completed
  - id: admin-whitelist
    content: Test IP whitelist page with auth
    status: completed
  - id: admin-monitoring
    content: Test monitoring page displays real stats
    status: completed
  - id: admin-sessions
    content: Test sessions page lists and terminates sessions
    status: completed
  - id: systemd-services
    content: Create systemd services for backend/frontend auto-start
    status: completed
  - id: remote-test
    content: Test full system from remote IP address
    status: completed
  - id: final-verify
    content: Complete final verification checklist
    status: completed
---

# Full System E2E Deployment Plan

## Current State Summary

**Completed (from previous sessions):**

- 4TB disk partitioned and mounted at `/data`
- ChatOS migrated to `/data/ChatOS-v2.0` with symlink
- Docker scrapers running (5 containers)
- PostgreSQL running with `chatos` schema and tables
- UFW firewall configured (80 ALLOW, 3000/8000 DENY)
- Caddy reverse proxy configured for HTTP
- Frontend/Backend services running
- All 11 user pages returning HTTP 200

**Still Required:**

- Keycloak authentication (not installed)
- Admin pages require auth to be functional
- Database usage logging verification
- Remote IP access testing

---

## Phase 1: Keycloak Setup

### 1.1 Deploy Keycloak via Docker

```bash
docker run -d --name keycloak \
  -p 8080:8080 \
  -e KEYCLOAK_ADMIN=admin \
  -e KEYCLOAK_ADMIN_PASSWORD=<secure-password> \
  -v /data/keycloak:/opt/keycloak/data \
  quay.io/keycloak/keycloak:latest start-dev
```

### 1.2 Configure Keycloak Realm

- Create realm: `chatos`
- Create client: `chatos-app` (public client, standard flow)
- Set redirect URIs: `http://192.168.0.249/*`
- Create admin user with `admin` role
- Create regular user role

### 1.3 Update Caddy Configuration

Add Keycloak routing to [/etc/caddy/Caddyfile](/etc/caddy/Caddyfile):

```caddy
# Add before other handle blocks
handle /auth/* {
    reverse_proxy localhost:8080
}
```

### 1.4 Set Backend Environment Variables

Update backend startup to include:

```bash
export KEYCLOAK_URL=http://localhost:8080
export KEYCLOAK_REALM=chatos
export KEYCLOAK_CLIENT_ID=chatos-app
```

---

## Phase 2: Database Verification

### 2.1 Verify Auth Tables Exist

Tables in `chatos` schema (already created):

- `user_sessions` - Session tracking
- `api_usage_log` - API request logging
- `feature_usage` - Feature usage tracking
- `audit_log` - Security audit trail
- `ip_whitelist` - IP access control

### 2.2 Test Database Connectivity

```bash
sudo -u postgres psql -d chatos -c "\dt chatos.*"
```

### 2.3 Verify Usage Logging Works

Test API call and verify log entry created in `api_usage_log`.

---

## Phase 3: Admin Pages Functionality

### 3.1 IP Whitelist Page (`/admin/ip-whitelist`)

**Backend:** [chatos_backend/api/routes_ip_whitelist.py](chatos_backend/api/routes_ip_whitelist.py)

Test endpoints (require auth):

- `GET /api/v1/admin/whitelist` - List IPs
- `POST /api/v1/admin/whitelist` - Add IP
- `DELETE /api/v1/admin/whitelist/{id}` - Remove IP
- `GET /api/v1/admin/whitelist/my-ip` - Get client IP (no auth)

### 3.2 Monitoring Page (`/admin/monitoring`)

**Backend:** [chatos_backend/api/routes_monitoring.py](chatos_backend/api/routes_monitoring.py)

Test endpoints:

- `GET /api/v1/admin/monitoring/health` - System health
- `GET /api/v1/admin/monitoring/api-usage` - API stats
- `GET /api/v1/admin/monitoring/feature-usage` - Feature stats

### 3.3 Sessions Page (`/admin/sessions`)

Test endpoints:

- `GET /api/v1/admin/monitoring/sessions` - List sessions
- `DELETE /api/v1/admin/monitoring/sessions/{id}` - Terminate session

---

## Phase 4: Frontend Authentication Integration

### 4.1 Add Keycloak JS Adapter

Install in frontend:

```bash
npm install keycloak-js
```

### 4.2 Create Auth Provider

Create auth context in [frontend/src/lib/auth.ts](frontend/src/lib/auth.ts):

- Initialize Keycloak client
- Handle login/logout
- Provide user context to pages

### 4.3 Protect Admin Routes

Wrap admin pages with auth check:

- `/admin/*` - Require `admin` role
- User pages - Optional auth for personalization

---

## Phase 5: Service Configuration

### 5.1 Create Systemd Services

**Backend Service:**

```ini
[Unit]
Description=ChatOS Backend
After=network.target postgresql.service

[Service]
User=kr
WorkingDirectory=/data/ChatOS-v2.0
Environment=KEYCLOAK_URL=http://localhost:8080
Environment=KEYCLOAK_REALM=chatos
ExecStart=/data/ChatOS-v2.0/.venv/bin/python -m uvicorn chatos_backend.app:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

**Frontend Service:**

```ini
[Unit]
Description=ChatOS Frontend
After=network.target

[Service]
User=kr
WorkingDirectory=/data/ChatOS-v2.0/frontend
ExecStart=/usr/bin/npm start -- -H 127.0.0.1 -p 3000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 5.2 Enable Auto-Start

```bash
sudo systemctl enable chatos-backend chatos-frontend keycloak
```

---

## Phase 6: Remote Access Testing

### 6.1 Whitelist Test IP

Add remote client IP to whitelist via:

1. Direct database insert (bootstrap)
2. Or admin UI after auth works

### 6.2 Test from Remote Client

- Access `http://192.168.0.249/`
- Verify Keycloak login redirect
- Test all pages after login
- Verify WebSocket connections work

### 6.3 Security Verification

- Confirm ports 3000/8000 blocked externally
- Confirm only port 80 accessible
- Test IP whitelist enforcement

---

## Phase 7: Page-by-Page Validation

### User Pages (no auth required for view)

| Page | Test |

|------|------|

| `/` | Chat interface loads, can send messages |

| `/trading` | Market data displays, WebSocket updates |

| `/trading/automations` | Automation list loads |

| `/trading/journal` | Journal entries display |

| `/trading/lab` | Backtest form works |

| `/notes` | Notes list, create/edit works |

| `/diary` | Audio upload, transcription |

| `/editor` | Automation builder loads |

| `/sandbox` | Code execution works |

| `/training` | Training interface loads |

### Admin Pages (auth required)

| Page | Test |

|------|------|

| `/admin` | Dashboard stats load |

| `/admin/ip-whitelist` | Can add/remove IPs |

| `/admin/monitoring` | API/feature usage displays |

| `/admin/sessions` | Sessions list, can terminate |

---

## Phase 8: Final Verification Checklist

- [ ] Keycloak running and accessible at `:8080`
- [ ] Caddy routing `/auth/*` to Keycloak
- [ ] Admin login works via Keycloak
- [ ] IP whitelist functional (add/remove IPs)
- [ ] Monitoring page shows real stats
- [ ] Sessions page lists active sessions
- [ ] All user pages load without errors
- [ ] WebSocket connections work
- [ ] Remote IP can access system
- [ ] Services auto-start on reboot

---

## Obsolete Items from Previous Plans

**From `fix_caddy_css_routing`:** COMPLETED - Caddy already configured correctly

**From `full_system_validation`:**

- TypeScript fixes: COMPLETED
- Database init: COMPLETED
- Backend tests: COMPLETED (351 passed)
- E2E tests: SUPERSEDED by manual validation

**From `user_pages_beta_testing`:** CONSOLIDATED into Phase 7 above