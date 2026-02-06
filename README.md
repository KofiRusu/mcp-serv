# Senior Engineer MCP Server

Production-hardened MCP server for Cursor/Continue IDEs with git, ripgrep, repo memory, and verification harness.

## Features

- **Security Hardening**: Read-only by default, token-guarded writes, path sandboxing, dry-run mode
- **Engineer Tools**: git_status, git_diff, git_show, ripgrep_search, run_cmd (with strict allowlist)
- **Repo Memory**: Append-only MEMORY.md, decision log with timestamps/tags
- **Verification**: Shell script and pytest smoke tests

## Architecture Overview

- Single-process MCP server using stdio JSON-RPC for IDE clients.
- Entry point is `mcp/server.py` with initialize/tools/resources handlers.
- Tool registry is centralized and used by verifiers and tests.
- Memory storage uses SQLite via `mcp/memory_store.py`.
- Repo memory is append-only markdown in `context/`.
- Engineer tools are allowlisted and path-sandboxed.
- Codex/Verdent integrations are optional and env-gated.
- Extension context is in-memory and write-token gated.
- Tests cover protocol, tools, and security gates.
- Verification script mirrors expected tool list and behavior.

## Security Model (Summary)

The server defaults to read-only with no writes allowed. Write-capable tools require a valid `MCP_WRITE_TOKEN` and are checked before any handler runs. Optional integrations are disabled unless their endpoints are configured.

## Quick Start

```bash
export MCP_WRITE_TOKEN="your_secure_token_here"
export MCP_DRY_RUN="false"
python -m compileall .
./scripts/verify_mcp.sh
python3 tests/test_mcp_smoke.py
```

## Detailed Setup

### 1. Configure Environment Variables

Set the `MCP_WRITE_TOKEN` environment variable to enable write operations:

```bash
export MCP_WRITE_TOKEN="your_secure_token_here"
```

For dry-run mode (log writes without executing):

```bash
export MCP_DRY_RUN="true"
```

### 2. Update Client Configurations

**For Cursor** ([`mcp_config_macos.json`](mcp_config_macos.json:1)):

```json
{
  "mcpServers": {
    "cursor-mcp": {
      "command": "python3",
      "args": ["/ABS/PATH/TO/cursor-mcp/mcp/server.py"],
      "cwd": "/ABS/PATH/TO/cursor-mcp",
      "env": {
        "PYTHONPATH": "/ABS/PATH/TO/cursor-mcp",
        "MCP_WORKSPACE_ROOT": "",
        "MCP_HOME": "/ABS/PATH/TO/cursor-mcp",
        "MCP_WRITE_TOKEN": "YOUR_SECURE_TOKEN_HERE",
        "MCP_DRY_RUN": "false"
      }
    }
  }
}
```

**For Continue** ([`.continue/mcpServers/cursor-mcp.yaml`](.continue/mcpServers/cursor-mcp.yaml:1)):

```yaml
name: cursor-mcp
description: Senior Engineer MCP Server with git, ripgrep, repo memory
command: python3
args:
  - /ABS/PATH/TO/cursor-mcp/mcp/server.py
cwd: /ABS/PATH/TO/cursor-mcp
env:
  PYTHONPATH: /ABS/PATH/TO/cursor-mcp
  MCP_WORKSPACE_ROOT: ${workspaceFolder}
  MCP_HOME: /ABS/PATH/TO/cursor-mcp
  MCP_WRITE_TOKEN: YOUR_SECURE_TOKEN_HERE
  MCP_DRY_RUN: "false"
```

### 3. Available Tools

| Tool | Description | Write Protected |
|------|------------------|----------|
| `store_memory` | Store memory in SQLite DB | ✓ Yes |
| `search_memory` | Search SQLite memories | No |
| `get_context` | Get contextual memories | No |
| `get_stats` | Get system statistics | No |
| `git_status` | Get git repository status | No |
| `git_diff` | Get git diff | No |
| `git_show` | Show commit details | No |
| `ripgrep_search` | Search files with ripgrep | No |
| `run_cmd` | Run allowed commands | No |
| `memory_append` | Append to MEMORY.md | ✓ Yes |
| `memory_search` | Search MEMORY.md | No |
| `decision_log_add` | Add to decision log | ✓ Yes |
| `decision_log_search` | Search decision log | No |
| `verdent_search` | Search Verdent traces | No |
| `verdent_get_trace` | Get Verdent trace by ID | No |
| `verdent_recent` | Get recent Verdent traces | No |
| `ext_set_context` | Set IDE/extension context (in-memory) | ✓ Yes |
| `ext_get_context` | Get IDE/extension context | No |
| `ext_clear_context` | Clear IDE/extension context | ✓ Yes |

### 4. Verification

Run the verification script:

```bash
./scripts/verify_mcp.sh
```

Run the smoke tests:

```bash
python3 tests/test_mcp_smoke.py
```

### 5. File Structure

```
.cursor/                      # Cursor plans
.continue/                    # Continue MCP server configs
data/                         # Data directory
docs/                         # Documentation
mcp/                          # MCP server modules
    ├── __init__.py
    ├── agent_integration.py
    ├── classifier.py
    ├── memory_store.py
    ├── models.py
    ├── path_sandbox.py
    ├── repo_memory.py
    ├── server.py
    └── engineer_tools.py
plans/                        # Implementation plans
scripts/                       # Verification scripts
tests/                         # Test suites
    ├── test_phase1_security.py
    ├── test_phase2_engineer_tools.py
    ├── test_phase3_repo_memory.py
    └── test_mcp_smoke.py
context/                       # Repo memory files
    ├── DECISIONS.md
    └── MEMORY.md
```

### 6. Security Model

- **Read-Only Default**: Server starts in read-only mode unless `MCP_WRITE_TOKEN` is set
- **Write Protection**: All write operations (`store_memory`, `memory_append`, `decision_log_add`) require valid `MCP_WRITE_TOKEN`
- **Dry-Run Mode**: When `MCP_DRY_RUN=true`, writes are logged but not executed
- **Path Sandbox**: All file operations are validated to stay within repo root

### 7. Environment Variables

| Variable | Description | Default |
|---------|--------|----------|
| `MCP_WRITE_TOKEN` | Write authorization token (required for write ops) | `null` (no writes allowed) |
| `MCP_DRY_RUN` | Enable dry-run mode (log only, no execution) | `false` | (execute writes) |
| `VERDENT_ENDPOINT` | Verdent API endpoint (enables Verdent tools) | `null` (tools disabled) |
| `VERDENT_API_KEY` | Verdent API key (optional bearer token) | `null` |
| `CODEX_ENDPOINT` | Codex API endpoint (enables Codex tools) | `null` (tools disabled) |
| `CODEX_API_KEY` | Codex API key (optional bearer token) | `null` |

### 8. Usage Examples

#### Write to Memory

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "memory_append",
    "arguments": {
      "content": "Important project decision: Use MCP_WRITE_TOKEN env var for writes",
      "tags": ["architecture", "security"],
      "write_token": "YOUR_SECURE_TOKEN_HERE"
    }
  }
}
```

#### Search Memory

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "memory_search",
    "arguments": {
      "query": "architecture"
    }
  }
}
```

#### Git Status

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "git_status",
    "arguments": {
      "cwd": "/ABS/PATH/TO/WORKSPACE"
    }
  }
}
```

#### Run Command (Allowed)

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "method": "tools/call",
  "params": {
    "name": "run_cmd",
    "arguments": {
      "cmd": ["python3", "--version"],
      "cwd": "/ABS/PATH/TO/WORKSPACE"
    }
  }
}
```

#### Extension Context (IDE/Editor)

Use IDE extensions to set short-lived, in-memory context (no file writes). Recommended flow:
- Call `ext_set_context` on selection change or diagnostics update.
- Call `ext_get_context` before asking the agent to act.
- Call `ext_clear_context` when context becomes stale (file closed, selection cleared).

```json
{
  "jsonrpc": "2.0",
  "id": 5,
  "method": "tools/call",
  "params": {
    "name": "ext_set_context",
    "arguments": {
      "payload": {
        "file": "src/app.py",
        "selection": "def handle_request(...):",
        "diagnostics": []
      },
      "write_token": "YOUR_SECURE_TOKEN_HERE"
    }
  }
}
```

### 9. Troubleshooting

**Problem**: Tools not appearing in Cursor/Continue UI

**Solution**: Ensure config files are in the correct location:
- Cursor: `~/.cursor/mcpServers/cursor-mcp.yaml` or user settings
- Continue: `~/.continue/mcpServers/cursor-mcp.yaml` or user settings

**Problem**: Write operations failing

**Solution**: Set `MCP_WRITE_TOKEN` environment variable in the config

**Problem**: Git operations failing

**Solution**: Ensure you're in a git repository when using git tools

### 10. Development Status

- **Phase 1**: ✅ Security Hardening (COMPLETE)
- **Phase 2**: ✅ Engineer Tools (COMPLETE)
- **Phase 3**: ✅ Repo Memory System (COMPLETE)
- **Phase 4**: ✅ Verification Harness (COMPLETE)
- **Phase 5**: ✅ Client Configuration (COMPLETE)
- **Phase 6**: ✅ Documentation (COMPLETE)

All phases completed successfully!
