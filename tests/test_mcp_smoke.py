#!/usr/bin/env python3
"""
MCP Server Smoke Test

Basic smoke tests for MCP server functionality.
"""

import sys
import json
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_server_imports():
    """Test server module imports"""
    print("\n=== Testing Server Imports ===")
    try:
        from mcp import server
        print("✓ mcp.server imports successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        raise


def test_initialize():
    """Test initialize request"""
    print("\n=== Testing Initialize ===")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {}
    }

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )

    response = json.loads(result.stdout)
    assert "result" in response, f"No result in response: {response}"
    result = response["result"]
    assert result["protocolVersion"] == "2024-11-05", f"Wrong protocol version: {result}"
    assert "serverInfo" in result, f"No serverInfo in result: {result}"
    print(f"✓ Initialize works")
    print(f"  Server: {result['serverInfo']['name']}")


def test_tools_list():
    """Test tools list request"""
    print("\n=== Testing Tools List ===")
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list",
        "params": {}
    }

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )

    response = json.loads(result.stdout)
    assert "result" in response, f"No result in response: {response}"
    tools = response["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    # Check for expected tools
    expected_tools = {
        "store_memory", "search_memory", "get_context", "get_stats",
        "git_status", "git_diff", "git_show", "ripgrep_search", "run_cmd",
        "memory_append", "memory_search", "decision_log_add", "decision_log_search"
    }

    for tool in expected_tools:
        assert tool in tool_names, f"Missing tool: {tool}"

    print(f"✓ Tools list works")
    print(f"  Available tools: {len(tool_names)}")


def test_read_only_tools():
    """Test read-only tools work without token"""
    print("\n=== Testing Read-Only Tools ===")

    # Test search_memory (read-only)
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "search_memory",
            "arguments": {
                "query": "test"
            }
        }
    }

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )

    response = json.loads(result.stdout)
    assert not response.get("result", {}).get("isError", False), "search_memory should work"
    print(f"✓ search_memory works")


def test_write_protection():
    """Test write operations are rejected without token"""
    print("\n=== Testing Write Protection ===")

    # Test memory_append without token (should fail)
    request = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/call",
        "params": {
            "name": "memory_append",
            "arguments": {
                "content": "test content"
            }
        }
    }

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )

    response = json.loads(result.stdout)
    assert response.get("result", {}).get("isError", True), "memory_append should fail without token"
    error_text = response["result"]["content"][0]["text"]
    assert "MCP_WRITE_TOKEN" in error_text, f"Error should mention token: {error_text}"
    print(f"✓ Write protection works")
    print(f"  Error: {error_text[:80]}...")


def test_git_tools():
    """Test git tools"""
    print("\n=== Testing Git Tools ===")

    # Test git_status
    request = {
        "jsonrpc": "2.0",
        "id": 5,
        "method": "tools/call",
        "params": {
            "name": "git_status",
            "arguments": {
                "cwd": str(Path(__file__).parent.parent)
            }
        }
    }

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )

    response = json.loads(result.stdout)
    assert not response.get("result", {}).get("isError", False), "git_status should work"
    print(f"✓ git_status works")


def test_run_cmd_allowlist():
    """Test run_cmd allowlist enforcement"""
    print("\n=== Testing run_cmd Allowlist ===")

    # Test forbidden command (should fail)
    request = {
        "jsonrpc": "2.0",
        "id": 6,
        "method": "tools/call",
        "params": {
            "name": "run_cmd",
            "arguments": {
                "cmd": ["rm", "-rf", "/"],
                "cwd": str(Path(__file__).parent.parent)
            }
        }
    }

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )

    response = json.loads(result.stdout)
    assert response.get("result", {}).get("isError", True), "run_cmd should reject forbidden commands"
    error_text = response["result"]["content"][0]["text"]
    assert "not in allowlist" in error_text, f"Error should mention allowlist: {error_text}"
    print(f"✓ Forbidden command rejected")
    print(f"  Error: {error_text[:80]}...")

    # Test allowed command (should work)
    request = {
        "jsonrpc": "2.0",
        "id": 7,
        "method": "tools/call",
        "params": {
            "name": "run_cmd",
            "arguments": {
                "cmd": ["python3", "--version"],
                "cwd": str(Path(__file__).parent.parent)
            }
        }
    }

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )

    response = json.loads(result.stdout)
    assert not response.get("result", {}).get("isError", False), "run_cmd should allow python3"
    print(f"✓ Allowed command works")


def test_repo_memory_tools():
    """Test repo memory tools"""
    print("\n=== Testing Repo Memory Tools ===")

    # Test memory_search
    request = {
        "jsonrpc": "2.0",
        "id": 8,
        "method": "tools/call",
        "params": {
            "name": "memory_search",
            "arguments": {
                "query": "Project Memory"
            }
        }
    }

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent)
    )

    response = json.loads(result.stdout)
    assert not response.get("result", {}).get("isError", False), "memory_search should work"
    content = response["result"]["content"][0]["text"]
    assert "Project Memory" in content, f"Search should find 'Project Memory': {content[:100]}..."
    print(f"✓ memory_search works")


if __name__ == "__main__":
    try:
        test_server_imports()
        test_initialize()
        test_tools_list()
        test_read_only_tools()
        test_write_protection()
        test_git_tools()
        test_run_cmd_allowlist()
        test_repo_memory_tools()

        print("\n" + "=" * 50)
        print("ALL MCP SMOKE TESTS PASSED ✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
