# VSCode Sandbox Setup Guide

This guide explains how to set up and use the VSCode Sandbox feature in ChatOS.

## Prerequisites

### 1. Install code-server

The VSCode Sandbox requires [code-server](https://github.com/coder/code-server) to be installed on your system.

**Option A: Using the install script (Recommended)**

```bash
curl -fsSL https://code-server.dev/install.sh | sh
```

**Option B: Using npm**

```bash
npm install -g code-server
```

**Option C: Using Homebrew (macOS)**

```bash
brew install code-server
```

**Option D: Manual download**

Download from [GitHub Releases](https://github.com/coder/code-server/releases) and add to your PATH.

### 2. Verify Installation

```bash
code-server --version
```

You should see version output like `4.x.x`.

## Configuration

### Environment Variables

Configure the sandbox behavior using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `SANDBOX_PROJECT_ROOTS` | `~/ChatOS-Sandbox` | Colon-separated list of allowed project directories |
| `CODE_SERVER_PORT` | `8443` | Port for code-server |
| `CODE_SERVER_HOST` | `127.0.0.1` | Host binding (localhost only for security) |
| `CODE_SERVER_AUTH` | `none` | Authentication mode (`none` for local use) |
| `SANDBOX_COMMAND_TIMEOUT` | `60` | Command execution timeout in seconds |
| `SANDBOX_MAX_OUTPUT_SIZE` | `1048576` | Maximum output size in bytes (1MB) |

### Setting Up Project Roots

You can configure multiple project directories that can be opened in the sandbox:

```bash
# Single directory (default)
export SANDBOX_PROJECT_ROOTS="$HOME/ChatOS-Sandbox"

# Multiple directories
export SANDBOX_PROJECT_ROOTS="$HOME/ChatOS-Sandbox:$HOME/projects/webapp:$HOME/projects/api"
```

Add this to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) for persistence.

### Example .env File

Create a `.env` file in the ChatOS root directory:

```env
# VSCode Sandbox Configuration
SANDBOX_PROJECT_ROOTS=/home/user/ChatOS-Sandbox:/home/user/my-projects
CODE_SERVER_PORT=8443
CODE_SERVER_HOST=127.0.0.1
CODE_SERVER_AUTH=none
SANDBOX_COMMAND_TIMEOUT=60
```

## Running the Sandbox

### 1. Start the Backend

```bash
cd ChatOS-0.1
uvicorn ChatOS.app:app --reload --port 8000
```

### 2. Start the Frontend

```bash
cd ChatOS-0.1/sandbox-ui
npm run dev
```

### 3. Access the Sandbox

Open your browser to:

- **Main Editor**: http://localhost:3000
- **VSCode Sandbox**: http://localhost:3000/sandbox

## Using the Sandbox

### Opening a Project

1. Navigate to http://localhost:3000/sandbox
2. Select a project from the dropdown (these are your configured project roots)
3. Click "Start" to launch code-server
4. Wait for VSCode to load in the iframe

### Running Commands

Use the `/api/sandbox/run` endpoint to execute commands:

```bash
curl -X POST http://localhost:8000/api/sandbox/run \
  -H "Content-Type: application/json" \
  -d '{"command": "python --version"}'
```

Allowed commands include:
- Python: `python`, `python3`, `pip`, `pytest`, `mypy`, `black`, `ruff`
- Node.js: `node`, `npm`, `npx`, `pnpm`, `yarn`, `bun`
- Git: `git`
- Shell: `bash`, `sh`, `cat`, `ls`, `pwd`, `echo`, `grep`, `find`, etc.

### AI Code Assistance

Use the AI Assist panel to get help with your code:

1. Click the "AI Assist" button to open the panel
2. Copy code from VSCode
3. Ask for explanations, refactoring, or test generation
4. Apply suggestions back to your code

Or use the API directly:

```bash
curl -X POST http://localhost:8000/api/sandbox/model-assist \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "explain this code",
    "code": "def hello(): print(\"world\")",
    "language": "python"
  }'
```

## Troubleshooting

### code-server not found

**Error**: `code-server not found`

**Solution**: Install code-server using one of the methods above and ensure it's in your PATH.

### Workspace not allowed

**Error**: `Workspace 'xxx' is not within allowed project roots`

**Solution**: Add the directory to `SANDBOX_PROJECT_ROOTS`:

```bash
export SANDBOX_PROJECT_ROOTS="$SANDBOX_PROJECT_ROOTS:/path/to/your/project"
```

### code-server fails to start

**Error**: `code-server failed to start`

**Solutions**:
1. Check if port 8443 is already in use: `lsof -i :8443`
2. Try a different port: `export CODE_SERVER_PORT=8444`
3. Check code-server logs for details

### iframe doesn't load / VSCode opens in new tab

**This is expected behavior.** code-server sets `X-Frame-Options` headers that prevent embedding in iframes from different origins. For security reasons, we show a launch panel instead and open VSCode in a new tab.

**Why this happens**:
- The ChatOS frontend runs on port 3000
- code-server runs on port 8443
- These are considered different "origins" by browsers
- code-server's security headers prevent cross-origin iframe embedding

**This is actually safer** because:
1. VSCode gets its own browser context with full permissions
2. No iframe sandbox restrictions limit functionality
3. Extensions and terminal work without issues
4. Copy/paste and file operations work normally

### Command not in allowlist

**Error**: `Command 'xxx' is not in the allowlist`

**Solution**: The command must be in `SANDBOX_ALLOWED_COMMANDS` in `config.py`. You can extend this list by modifying the configuration (requires restart).

## Security Considerations

1. **Local Only**: code-server binds to localhost by default. Don't expose it to the network.

2. **Path Restrictions**: All file operations are restricted to configured project roots.

3. **Command Allowlist**: Only pre-approved commands can be executed.

4. **No Authentication**: In local mode, authentication is disabled. Enable it for shared environments:
   ```bash
   export CODE_SERVER_AUTH=password
   ```

## API Reference

### Projects

- `GET /api/sandbox/projects` - List configured project roots
- `GET /api/sandbox/allowed-commands` - List allowed commands

### VSCode Management

- `GET /api/sandbox/vscode/status` - Get code-server status
- `POST /api/sandbox/vscode/start` - Start code-server
- `POST /api/sandbox/vscode/stop` - Stop code-server
- `GET /api/sandbox/vscode/health` - Health check

### Command Execution

- `POST /api/sandbox/run` - Execute a command

### AI Assistance

- `POST /api/sandbox/model-assist` - Get AI help with code
- `POST /api/sandbox/model-assist/explain` - Quick code explanation
- `POST /api/sandbox/model-assist/refactor` - Get refactoring suggestions
- `POST /api/sandbox/model-assist/tests` - Generate unit tests

## Next Steps

- Explore the VSCode extensions available in code-server
- Configure your preferred theme and settings
- Set up additional project roots for your workflows
- Use the AI Assist feature for code help

