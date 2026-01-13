---
name: Fix Backend Service Restart Issue
overview: Diagnose and fix the ChatOS backend service that is continuously restarting, ensuring it runs stably.
todos:
  - id: diagnose-logs
    content: Check systemd logs to identify the specific error causing restarts
    status: completed
  - id: check-port
    content: Verify port 8000 is not in use by another process
    status: completed
  - id: test-manual
    content: Test manual backend startup to see actual error message
    status: completed
  - id: apply-fix
    content: Apply fix based on identified root cause (dependency/port/config)
    status: completed
  - id: verify-stable
    content: Verify backend stays running without restart loops
    status: completed
---

# Fix Backend Service Restart Issue

## Problem

The `chatos-backend` systemd service is in `activating (auto-restart)` state, indicating it's crashing on startup and systemd is attempting to restart it every 5 seconds.

## Diagnosis Steps

### 1. Check Service Logs

```bash
sudo journalctl -u chatos-backend -n 100 --no-pager
```

Look for:

- Python import errors (ModuleNotFoundError, ImportError)
- Port conflicts (Address already in use)
- Database connection failures
- Missing environment variables
- Permission errors

### 2. Check for Port Conflicts

```bash
sudo lsof -i:8000
sudo ss -tlnp | grep 8000
```

If port 8000 is in use by another process, either:

- Kill the conflicting process
- Or change backend port in systemd service

### 3. Test Manual Startup

```bash
cd /data/ChatOS-v2.0
source .venv/bin/activate
export KEYCLOAK_URL=http://localhost:8080
export KEYCLOAK_REALM=chatos
export KEYCLOAK_CLIENT_ID=chatos-app
export DATABASE_URL=postgresql://chatos:chatos@localhost:5432/chatos
python -m uvicorn chatos_backend.app:app --host 127.0.0.1 --port 8000
```

This will show the actual error message.

## Common Causes & Fixes

### Cause 1: Missing Python Dependencies

**Symptoms:** `ModuleNotFoundError` in logs

**Fix:**

```bash
cd /data/ChatOS-v2.0
.venv/bin/pip install -r chatos_backend/requirements.txt
```

### Cause 2: Port Already in Use

**Symptoms:** `Address already in use` or `EADDRINUSE`

**Fix:**

```bash
# Find and kill process using port 8000
sudo lsof -ti:8000 | xargs sudo kill -9
# Or change port in systemd service to 8001
```

### Cause 3: Database Connection Failure

**Symptoms:** `OperationalError` or `connection refused`

**Fix:**

```bash
# Verify PostgreSQL is running
sudo systemctl status postgresql
# Test connection
psql -U chatos -d chatos -h localhost
```

### Cause 4: Missing Environment Variables

**Symptoms:** `KeyError` or `NoneType` errors related to config

**Fix:**

Verify all environment variables are set in `/etc/systemd/system/chatos-backend.service`:

- KEYCLOAK_URL
- KEYCLOAK_REALM
- KEYCLOAK_CLIENT_ID
- DATABASE_URL
- REALTIME_DATA_DIR

### Cause 5: Import Errors from Recent Changes

**Symptoms:** `ImportError` or `AttributeError` during module import

**Fix:**

Check if recent changes to `chatos_backend/app.py` or route files introduced import errors. Verify all imports resolve correctly.

## Implementation Plan

### Step 1: Diagnose the Issue

1. Check systemd logs: `sudo journalctl -u chatos-backend -n 100`
2. Identify the specific error message
3. Note the last successful line before error

### Step 2: Apply Appropriate Fix

Based on the error found:

- If missing dependency: Install it
- If port conflict: Kill conflicting process or change port
- If database: Verify PostgreSQL and connection string
- If import error: Fix the import or missing module
- If permission: Fix file/directory permissions

### Step 3: Test Manual Startup

1. Stop systemd service: `sudo systemctl stop chatos-backend`
2. Start manually with full error output
3. Verify it starts successfully
4. Test API endpoint: `curl http://127.0.0.1:8000/api/health`

### Step 4: Fix Systemd Service

If manual startup works but systemd doesn't:

1. Verify ExecStart path is correct: `/data/ChatOS-v2.0/.venv/bin/python`
2. Verify WorkingDirectory exists: `/data/ChatOS-v2.0`
3. Verify User has permissions: `kr` user can access all paths
4. Check for missing environment variables
5. Consider adding `StandardOutput=journal` and `StandardError=journal` for better logging

### Step 5: Restart and Verify

1. Reload systemd: `sudo systemctl daemon-reload`
2. Start service: `sudo systemctl start chatos-backend`
3. Check status: `sudo systemctl status chatos-backend`
4. Monitor logs: `sudo journalctl -u chatos-backend -f`
5. Verify it stays running (not restarting)
6. Test API: `curl http://127.0.0.1:8000/api/health`

## Files to Check/Modify

- `/etc/systemd/system/chatos-backend.service` - Service configuration
- `/data/ChatOS-v2.0/chatos_backend/app.py` - Main application file
- `/data/ChatOS-v2.0/chatos_backend/requirements.txt` - Python dependencies
- `/data/ChatOS-v2.0/.venv/` - Virtual environment
- Systemd logs: `journalctl -u chatos-backend`

## Success Criteria

- Backend service status shows `active (running)` (not `activating`)
- No restart loops in `systemctl status`
- API responds: `curl http://127.0.0.1:8000/api/health` returns 200
- Service stays running for at least 5 minutes without restarting
- All pages accessible via browser at http://192.168.0.249/

## Notes

The backend was working earlier when started manually. The issue likely relates to:

- Systemd environment differences vs manual startup
- Missing dependencies in venv
- Port conflict from previous manual start
- Import errors from recent code changes

Once the root cause is identified from logs, the fix should be straightforward.