# RELEASE NOTES — v0.1.2-mcp

## Core Features
- MCP stdio JSON-RPC server for Cursor/Continue clients.
- Read-only default with token-gated write operations.
- Engineer tools: git, ripgrep, and allowlisted command execution.
- Repo memory append/search for MEMORY.md and decision log.

## Integrations
- Codex tools: analyze, plan, diff (optional, env-gated).
- Verdent tools: search, get_trace, recent (optional, env-gated).
- Extension context: in-memory IDE/editor context (token-gated writes).

## Verification Status
- `python -m compileall .`
- `./scripts/verify_mcp.sh`
- `python3 tests/test_mcp_smoke.py`
