#!/bin/bash
#
# MCP Server Verification Script
#
# Verifies that the MCP server is properly configured and functional.
#

set -e

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
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 mcp/server.py | jq -e '.result.tools | length' 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Tools list check failed"
    exit 1
fi

TOOL_COUNT=$(echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 mcp/server.py | jq -r '.result.tools | length')
echo "✓ Tools available: $TOOL_COUNT"

# Check expected tools exist
EXPECTED_TOOLS=("store_memory" "search_memory" "get_context" "get_stats" "git_status" "git_diff" "git_show" "ripgrep_search" "run_cmd" "memory_append" "memory_search" "decision_log_add" "decision_log_search")

for tool in "${EXPECTED_TOOLS[@]}"; do
    TOOL_EXISTS=$(echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python3 mcp/server.py | jq -r ".result.tools[] | select(.name == \"$tool\") | length | . > 0")
    if [ "$TOOL_EXISTS" != "true" ]; then
        echo "❌ Tool '$tool' not found in tools list"
        exit 1
    fi
done
echo "✓ All expected tools present"

echo ""
echo "=== Verification Complete ==="
echo "All checks passed! MCP server is ready."
