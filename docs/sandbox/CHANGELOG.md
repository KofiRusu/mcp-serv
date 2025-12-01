# VSCode Sandbox Changelog

## [1.0.0] - 2025-12-01

### Added

#### Backend (FastAPI)

**New Files:**
- `ChatOS/controllers/vscode_manager.py` - code-server process manager
  - `VSCodeManager` class for lifecycle management
  - `VSCodeStatus` dataclass for status tracking
  - `CommandResult` dataclass for command execution results
  - `ProjectInfo` dataclass for project metadata
  - Start/stop code-server with workspace configuration
  - Health checking via HTTP
  - Command execution with allowlist validation
  - Path security validation

- `ChatOS/api/routes_vscode.py` - VSCode sandbox API endpoints
  - `GET /api/sandbox/projects` - List configured project roots
  - `GET /api/sandbox/vscode/status` - Get code-server status
  - `POST /api/sandbox/vscode/start` - Start code-server
  - `POST /api/sandbox/vscode/stop` - Stop code-server
  - `GET /api/sandbox/vscode/health` - Health check
  - `POST /api/sandbox/run` - Execute allowlisted command
  - `GET /api/sandbox/allowed-commands` - List allowed commands
  - `POST /api/sandbox/model-assist` - AI code assistance
  - `POST /api/sandbox/model-assist/explain` - Quick explanation
  - `POST /api/sandbox/model-assist/refactor` - Refactoring suggestions
  - `POST /api/sandbox/model-assist/tests` - Test generation

**Modified Files:**
- `ChatOS/config.py` - Added VSCode sandbox configuration
  - `SANDBOX_PROJECT_ROOTS` - Allowed directories (env configurable)
  - `CODE_SERVER_PORT` - code-server port (default 8443)
  - `CODE_SERVER_HOST` - code-server host (default 127.0.0.1)
  - `CODE_SERVER_AUTH` - Authentication mode
  - `SANDBOX_ALLOWED_COMMANDS` - Command allowlist
  - `SANDBOX_COMMAND_TIMEOUT` - Execution timeout
  - `SANDBOX_MAX_OUTPUT_SIZE` - Output size limit

- `ChatOS/app.py` - Registered vscode router

#### Frontend (Next.js)

**New Files:**
- `sandbox-ui/src/app/sandbox/page.tsx` - VSCode Sandbox page
  - Full-screen VSCode layout
  - Project selector integration
  - AI Assist panel toggle
  - Navigation to main editor

- `sandbox-ui/src/components/vscode-sandbox.tsx` - VSCode iframe wrapper
  - code-server iframe embedding
  - Loading/error states
  - Fullscreen toggle
  - Open in new tab
  - Workspace indicator

- `sandbox-ui/src/components/project-selector.tsx` - Project selector
  - Dropdown for project roots
  - Git repository indicator
  - Start/stop controls
  - Status badge
  - Refresh functionality

**Modified Files:**
- `sandbox-ui/src/lib/api.ts` - Added VSCode API functions
  - `getProjects()` - Fetch project roots
  - `getVSCodeStatus()` - Get server status
  - `startVSCode()` - Start code-server
  - `stopVSCode()` - Stop code-server
  - `checkVSCodeHealth()` - Health check
  - `runCommand()` - Execute commands
  - `getAllowedCommands()` - List allowed commands
  - `modelAssist()` - AI code assistance
  - `explainCode()` - Quick explanation
  - `refactorCode()` - Refactoring help
  - `generateTests()` - Test generation

#### Documentation

**New Files:**
- `docs/sandbox/VS_CODE_SANDBOX_DESIGN.md` - Architecture overview
- `docs/sandbox/SETUP.md` - Setup and configuration guide
- `docs/sandbox/CHANGELOG.md` - This changelog

### Security

- Path validation restricts access to configured project roots only
- Command execution limited to explicit allowlist
- No `..` path traversal permitted
- code-server binds to localhost by default
- Output size limits prevent resource exhaustion
- Execution timeouts prevent runaway processes

### Dependencies

**Required:**
- code-server (4.x recommended) - Install via: `curl -fsSL https://code-server.dev/install.sh | sh`

**Optional:**
- aiohttp - For async health checks (falls back to process check if unavailable)

### Configuration

Set these environment variables to customize behavior:

```bash
# Project directories (colon-separated)
SANDBOX_PROJECT_ROOTS="$HOME/ChatOS-Sandbox:$HOME/projects"

# code-server settings
CODE_SERVER_PORT=8443
CODE_SERVER_HOST=127.0.0.1
CODE_SERVER_AUTH=none

# Execution limits
SANDBOX_COMMAND_TIMEOUT=60
SANDBOX_MAX_OUTPUT_SIZE=1048576
```

### Known Limitations

1. Single code-server instance at a time
2. No inline AI suggestions in VSCode (use AI Assist panel)
3. Extensions managed within code-server separately
4. Local access only (no remote/shared support without additional configuration)

### Migration Notes

This is a new feature module. No migration required for existing ChatOS installations.

To enable:
1. Install code-server
2. Configure project roots (optional)
3. Restart ChatOS backend
4. Access via `/sandbox` route

---

## File Summary

### New Files (9)

| File | Type | Description |
|------|------|-------------|
| `ChatOS/controllers/vscode_manager.py` | Python | code-server process manager |
| `ChatOS/api/routes_vscode.py` | Python | VSCode sandbox API routes |
| `sandbox-ui/src/app/sandbox/page.tsx` | TypeScript/React | Sandbox page component |
| `sandbox-ui/src/components/vscode-sandbox.tsx` | TypeScript/React | VSCode iframe wrapper |
| `sandbox-ui/src/components/project-selector.tsx` | TypeScript/React | Project selection UI |
| `docs/sandbox/VS_CODE_SANDBOX_DESIGN.md` | Markdown | Architecture documentation |
| `docs/sandbox/SETUP.md` | Markdown | Setup guide |
| `docs/sandbox/CHANGELOG.md` | Markdown | This changelog |

### Modified Files (3)

| File | Changes |
|------|---------|
| `ChatOS/config.py` | Added VSCode sandbox configuration variables |
| `ChatOS/app.py` | Registered vscode_router |
| `sandbox-ui/src/lib/api.ts` | Added VSCode API client functions |

