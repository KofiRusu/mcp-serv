# Maintenance Guide

## Adding New Tools Safely
- Add the tool to the canonical tools list in `mcp/server.py`.
- Implement handler logic with read-only defaults and clear errors.
- If write-capable, include the tool in `WRITE_OPERATIONS` and require `MCP_WRITE_TOKEN`.
- Enforce payload sanitization and size limits for any new inputs.

## Updating Verifiers and Tests
- Update `scripts/verify_mcp.sh` expected tool list and any new error checks.
- Update `tests/test_mcp_smoke.py` to cover tool presence and basic behavior.
- Keep optional integrations gated by env vars to avoid CI failures.
