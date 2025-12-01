# VSCode Web Sandbox - Architecture Design

## Overview

The VSCode Sandbox integrates [code-server](https://github.com/coder/code-server) into ChatOS, providing a full Visual Studio Code experience within the ChatOS interface. This enables developers to:

- Edit code with full VSCode features (IntelliSense, extensions, themes)
- Access local project folders via configurable project roots
- Execute commands through a secure allowlist
- Get AI-powered code assistance via ChatOS LLM integration

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ChatOS Frontend (Next.js)                     │
│  ┌─────────────────┐  ┌────────────────────────────────────────┐   │
│  │ Project Selector │  │         VSCode Sandbox (iframe)         │   │
│  │   Component      │  │                                        │   │
│  └────────┬────────┘  │   ┌──────────────────────────────────┐ │   │
│           │           │   │       code-server (port 8443)     │ │   │
│           ▼           │   │                                    │ │   │
│  ┌─────────────────┐  │   │  ┌────────┐ ┌────────┐ ┌────────┐│ │   │
│  │  Model Assist   │  │   │  │Explorer│ │ Editor │ │Terminal││ │   │
│  │     Panel       │  │   │  └────────┘ └────────┘ └────────┘│ │   │
│  └────────┬────────┘  │   └──────────────────────────────────┘ │   │
│           │           └────────────────────────────────────────┘   │
└───────────┼─────────────────────────────────────────────────────────┘
            │                              ▲
            ▼                              │
┌───────────────────────────────────────────────────────────────────────┐
│                      ChatOS Backend (FastAPI)                         │
│                                                                       │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐   │
│  │  routes_vscode  │  │  vscode_manager │  │   Existing APIs     │   │
│  │                 │  │                 │  │                     │   │
│  │ /projects       │  │ start_server()  │  │ /api/chat           │   │
│  │ /vscode/start   │──│ stop_server()   │  │ /api/sandbox/*      │   │
│  │ /vscode/stop    │  │ get_status()    │  │ /api/terminal/ws    │   │
│  │ /vscode/status  │  │                 │  │                     │   │
│  │ /run            │  └────────┬────────┘  └─────────────────────┘   │
│  │ /model-assist   │           │                                     │
│  └─────────────────┘           ▼                                     │
│                       ┌─────────────────┐                            │
│                       │  code-server    │                            │
│                       │    process      │                            │
│                       └────────┬────────┘                            │
│                                │                                     │
└────────────────────────────────┼─────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        Local Filesystem                              │
│                                                                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │
│  │ ~/ChatOS-Sandbox│  │ ~/projects/app1 │  │ ~/projects/app2     │  │
│  │   (default)     │  │  (configured)   │  │   (configured)      │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### Backend Components

#### 1. VSCode Manager (`controllers/vscode_manager.py`)

Manages the code-server process lifecycle:

- **Process Management**: Start, stop, and monitor code-server
- **Session Tracking**: Track active workspace sessions
- **Health Checks**: Verify code-server availability
- **Configuration**: Apply port, auth, and workspace settings

```python
class VSCodeManager:
    def start_server(workspace: str, port: int) -> bool
    def stop_server() -> bool
    def get_status() -> VSCodeStatus
    def is_healthy() -> bool
```

#### 2. VSCode Routes (`api/routes_vscode.py`)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/sandbox/projects` | GET | List allowed project roots |
| `/api/sandbox/vscode/start` | POST | Start code-server for workspace |
| `/api/sandbox/vscode/stop` | POST | Stop code-server instance |
| `/api/sandbox/vscode/status` | GET | Get code-server status |
| `/api/sandbox/run` | POST | Execute allowlisted command |
| `/api/sandbox/model-assist` | POST | LLM code assistance |

### Frontend Components

#### 1. Project Selector (`project-selector.tsx`)

- Dropdown listing configured project roots
- Displays workspace status (running/stopped)
- Launch button to open in VSCode

#### 2. VSCode Sandbox Wrapper (`vscode-sandbox.tsx`)

- Embeds code-server in an iframe
- Handles loading/error states
- Manages iframe communication
- Responsive sizing

#### 3. Sandbox Page (`app/sandbox/page.tsx`)

- Full-screen layout with VSCode embedded
- Header with project selection and ChatOS branding
- Optional AI assist panel

## Security Model

### Path Restrictions

All filesystem access is restricted to configured project roots:

```python
SANDBOX_PROJECT_ROOTS = [
    "~/ChatOS-Sandbox",      # Default sandbox
    "~/projects/my-app",     # Custom project
]
```

Path validation ensures:
- No `..` traversal outside allowed roots
- Symbolic links resolved and validated
- File operations only within boundaries

### Command Allowlist

Command execution restricted to approved commands:

```python
SANDBOX_ALLOWED_COMMANDS = [
    "python", "python3", "pip", "pytest",
    "node", "npm", "pnpm", "yarn",
    "bash", "sh", "cat", "ls", "pwd", "echo", "grep", "find"
]
```

### code-server Security

- Runs on localhost only (127.0.0.1)
- No authentication required (local access)
- Workspace restricted to selected project root

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SANDBOX_PROJECT_ROOTS` | `~/ChatOS-Sandbox` | Colon-separated list of allowed directories |
| `CODE_SERVER_PORT` | `8443` | Port for code-server |
| `CODE_SERVER_HOST` | `127.0.0.1` | Host binding for code-server |
| `CODE_SERVER_AUTH` | `none` | Authentication mode |

### Example Configuration

```bash
# .env or shell export
export SANDBOX_PROJECT_ROOTS="$HOME/ChatOS-Sandbox:$HOME/projects/webapp:$HOME/projects/api"
export CODE_SERVER_PORT=8443
```

## Data Flow

### Opening a Project

```
1. User selects project from dropdown
2. Frontend calls POST /api/sandbox/vscode/start
3. Backend starts code-server with workspace path
4. Backend returns URL (localhost:8443)
5. Frontend loads iframe with code-server URL
6. User interacts with full VSCode environment
```

### Model Assist Flow

```
1. User selects code in VSCode
2. Copies to Model Assist panel
3. Sends request with instruction + code
4. Backend calls ChatOS LLM
5. Returns suggestions/patches
6. User applies changes manually
```

### Command Execution

```
1. User invokes command (via API or terminal)
2. Backend validates against allowlist
3. Executes in project directory
4. Streams output back to client
5. Returns exit code and result
```

## Integration with Existing ChatOS

### Preserved Functionality

- Existing `/api/sandbox/*` endpoints unchanged
- Chat UI and LLM integration unaffected
- Training pipelines and data intact
- Terminal WebSocket API available

### New Entry Points

- `/sandbox` route for VSCode experience
- Model assist integrates with existing LLM client
- Project roots extend sandbox concept

## Limitations

1. **Single Instance**: Only one code-server instance at a time
2. **Local Only**: code-server binds to localhost
3. **Manual AI**: Model assist requires copy/paste (no inline AI)
4. **Extension Sync**: Extensions managed within code-server

## Future Enhancements

- [ ] Multiple simultaneous workspaces
- [ ] VSCode extension for ChatOS integration
- [ ] Inline AI suggestions in editor
- [ ] Git integration panel
- [ ] Collaborative editing support

