#!/bin/bash
#
# MCP Server Verification Script
#
# Verifies that the MCP server is properly configured and functional.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_PATH="$REPO_ROOT/mcp/server.py"
export PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}"

echo "=== MCP Server Verification ==="

# Check Python
echo "1. Checking Python..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 not found"
    exit 1
fi
echo "✓ Python3 found: $(python3 --version)"

# Check dependencies
echo "2. Checking dependencies..."
python3 -c "import mcp.server" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ MCP module not found"
    exit 1
fi
echo "✓ MCP module imports successfully"

# Check server can be imported
echo "3. Checking server import..."
python3 -c "from mcp.server import MCPServer; s = MCPServer(); print('Server initialized')" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Server initialization failed"
    exit 1
fi
echo "✓ Server initializes successfully"

# Check tools list
echo "4. Checking tools list..."
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 "$SERVER_PATH" | jq -e '.result.tools | length' 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Tools list check failed"
    exit 1
fi

TOOL_COUNT=$(echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 "$SERVER_PATH" | jq -r '.result.tools | length')
echo "✓ Tools available: $TOOL_COUNT"

# Check expected tools exist
EXPECTED_TOOLS=("store_memory" "search_memory" "get_context" "get_stats" "git_status" "git_diff" "git_show" "ripgrep_search" "run_cmd" "memory_append" "memory_search" "decision_log_add" "decision_log_search" "ext_get_context" "ext_set_context" "ext_clear_context")
if [ -n "$CODEX_ENDPOINT" ]; then
    EXPECTED_TOOLS+=("codex_analyze" "codex_plan" "codex_diff")
fi
if [ -n "$VERDENT_ENDPOINT" ]; then
    EXPECTED_TOOLS+=("verdent_search" "verdent_get_trace" "verdent_recent")
fi

for tool in "${EXPECTED_TOOLS[@]}"; do
    TOOL_EXISTS=$(echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 "$SERVER_PATH" | jq -r ".result.tools[] | select(.name == \"$tool\") | length | . > 0")
    if [ "$TOOL_EXISTS" != "true" ]; then
        echo "❌ Tool '$tool' not found in tools list"
        exit 1
    fi
done
echo "✓ All expected tools present"

# Check Codex endpoint missing behavior (only when not configured)
if [ -z "$CODEX_ENDPOINT" ]; then
    echo "5. Checking Codex endpoint not configured behavior..."
    CODEX_RESP=$(echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"codex_analyze","arguments":{"input":"ping"}}}' | python3 "$SERVER_PATH")
    echo "$CODEX_RESP" | jq -e '.result.isError == true and (.result.content[0].text | contains("CODEX_ENDPOINT"))' >/dev/null
    if [ $? -ne 0 ]; then
        echo "❌ Codex tool did not return expected endpoint error"
        exit 1
    fi
    echo "✓ Codex endpoint not configured error handled"
fi

# Check Verdent endpoint missing behavior (only when not configured)
if [ -z "$VERDENT_ENDPOINT" ]; then
    echo "6. Checking Verdent endpoint not configured behavior..."
    VERDENT_RESP=$(echo '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"verdent_search","arguments":{"query":"ping"}}}' | python3 "$SERVER_PATH")
    echo "$VERDENT_RESP" | jq -e '.result.isError == true and (.result.content[0].text | contains("VERDENT_ENDPOINT"))' >/dev/null
    if [ $? -ne 0 ]; then
        echo "❌ Verdent tool did not return expected endpoint error"
        exit 1
    fi
    echo "✓ Verdent endpoint not configured error handled"
fi

# Check extension context write-token gating when MCP_WRITE_TOKEN is not set
if [ -z "$MCP_WRITE_TOKEN" ]; then
    echo "7. Checking extension context write protection..."
    EXT_SET_RESP=$(echo '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"ext_set_context","arguments":{"payload":{"k":"v"}}}}' | python3 "$SERVER_PATH")
    echo "$EXT_SET_RESP" | jq -e '.result.isError == true and (.result.content[0].text | contains("MCP_WRITE_TOKEN"))' >/dev/null
    if [ $? -ne 0 ]; then
        echo "❌ ext_set_context did not return expected write-token error"
        exit 1
    fi
    EXT_CLEAR_RESP=$(echo '{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"ext_clear_context","arguments":{}}}' | python3 "$SERVER_PATH")
    echo "$EXT_CLEAR_RESP" | jq -e '.result.isError == true and (.result.content[0].text | contains("MCP_WRITE_TOKEN"))' >/dev/null
    if [ $? -ne 0 ]; then
        echo "❌ ext_clear_context did not return expected write-token error"
        exit 1
    fi
    echo "✓ Extension context write protection enforced"
fi

echo ""
echo "=== Verification Complete ==="
echo "All checks passed! MCP server is ready."
