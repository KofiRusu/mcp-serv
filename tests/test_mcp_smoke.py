#!/usr/bin/env python3
"""
MCP Server Smoke Test

Basic smoke tests for MCP server functionality.
"""

import os
import sys
import json
import subprocess
from pathlib import Path
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
REPO_ROOT = Path(__file__).parent.parent.resolve()
SERVER_PATH = REPO_ROOT / "mcp" / "server.py"


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
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
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
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )

    response = json.loads(result.stdout)
    assert "result" in response, f"No result in response: {response}"
    tools = response["result"]["tools"]
    tool_names = [t["name"] for t in tools]

    # Check for expected tools
    expected_tools = {
        "store_memory", "search_memory", "get_context", "get_stats",
        "git_status", "git_diff", "git_show", "ripgrep_search", "run_cmd",
        "memory_append", "memory_search", "decision_log_add", "decision_log_search",
        "ext_get_context", "ext_set_context", "ext_clear_context"
    }
    if os.getenv("CODEX_ENDPOINT"):
        expected_tools.update({"codex_analyze", "codex_plan", "codex_diff"})
    if os.getenv("VERDENT_ENDPOINT"):
        expected_tools.update({"verdent_search", "verdent_get_trace", "verdent_recent"})

    for tool in expected_tools:
        assert tool in tool_names, f"Missing tool: {tool}"

    print(f"✓ Tools list works")
    print(f"  Available tools: {len(tool_names)}")


def test_tools_list_from_other_cwd():
    """Test tools list when server launched from a different cwd"""
    print("\n=== Testing Tools List From Other CWD ===")
    request = {
        "jsonrpc": "2.0",
        "id": 20,
        "method": "tools/list",
        "params": {}
    }

    temp_dir = tempfile.gettempdir()
    result = subprocess.run(
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=temp_dir
    )

    response = json.loads(result.stdout)
    assert "result" in response, f"No result in response: {response}"
    tools = response["result"]["tools"]
    assert len(tools) > 0, "Expected tools list from non-repo cwd"
    print(f"✓ Tools list works from cwd={temp_dir}")


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
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
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
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )

    response = json.loads(result.stdout)
    assert response.get("result", {}).get("isError", True), "memory_append should fail without token"
    error_text = response["result"]["content"][0]["text"]
    assert "MCP_WRITE_TOKEN" in error_text, f"Error should mention token: {error_text}"
    print(f"✓ Write protection works")
    print(f"  Error: {error_text[:80]}...")


def test_codex_endpoint_not_configured():
    """Test Codex tools return a clear error when endpoint is missing"""
    if os.getenv("CODEX_ENDPOINT"):
        print("\n=== Skipping Codex Missing Endpoint Test (configured) ===")
        return

    print("\n=== Testing Codex Missing Endpoint ===")
    request = {
        "jsonrpc": "2.0",
        "id": 9,
        "method": "tools/call",
        "params": {
            "name": "codex_analyze",
            "arguments": {
                "input": "ping"
            }
        }
    }

    result = subprocess.run(
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )

    response = json.loads(result.stdout)
    assert response.get("result", {}).get("isError", False), "codex_analyze should error when endpoint missing"
    error_text = response["result"]["content"][0]["text"]
    assert "CODEX_ENDPOINT" in error_text, f"Error should mention CODEX_ENDPOINT: {error_text}"
    print("✓ Codex missing endpoint error handled")


def test_verdent_endpoint_not_configured():
    """Test Verdent tools return a clear error when endpoint is missing"""
    if os.getenv("VERDENT_ENDPOINT"):
        print("\n=== Skipping Verdent Missing Endpoint Test (configured) ===")
        return

    print("\n=== Testing Verdent Missing Endpoint ===")
    request = {
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {
            "name": "verdent_search",
            "arguments": {
                "query": "ping"
            }
        }
    }

    result = subprocess.run(
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )

    response = json.loads(result.stdout)
    assert response.get("result", {}).get("isError", False), "verdent_search should error when endpoint missing"
    error_text = response["result"]["content"][0]["text"]
    assert "VERDENT_ENDPOINT" in error_text, f"Error should mention VERDENT_ENDPOINT: {error_text}"
    print("✓ Verdent missing endpoint error handled")


def test_extension_context_tools():
    """Test extension context lifecycle and write protection"""
    print("\n=== Testing Extension Context Tools ===")

    # ext_get_context should start as none set
    request = {
        "jsonrpc": "2.0",
        "id": 11,
        "method": "tools/call",
        "params": {
            "name": "ext_get_context",
            "arguments": {}
        }
    }
    result = subprocess.run(
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )
    response = json.loads(result.stdout)
    content = response["result"]["content"][0]["text"]
    assert "none set" in content, f"Expected none set: {content}"

    # ext_set_context without token should fail
    request = {
        "jsonrpc": "2.0",
        "id": 12,
        "method": "tools/call",
        "params": {
            "name": "ext_set_context",
            "arguments": {"payload": {"foo": "bar"}}
        }
    }
    result = subprocess.run(
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
    )
    response = json.loads(result.stdout)
    assert response.get("result", {}).get("isError", False), "ext_set_context should fail without token"
    error_text = response["result"]["content"][0]["text"]
    assert "MCP_WRITE_TOKEN" in error_text, f"Error should mention token: {error_text}"

    # With token set, set context, get it, clear it, and confirm cleared
    token = "test-token"
    env = dict(os.environ)
    env["MCP_WRITE_TOKEN"] = token
    payload = {"doc": "README.md", "selection": "line 1"}
    requests = [
        {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {
                "name": "ext_set_context",
                "arguments": {"payload": payload, "write_token": token}
            }
        },
        {
            "jsonrpc": "2.0",
            "id": 14,
            "method": "tools/call",
            "params": {"name": "ext_get_context", "arguments": {}}
        },
        {
            "jsonrpc": "2.0",
            "id": 15,
            "method": "tools/call",
            "params": {"name": "ext_clear_context", "arguments": {"write_token": token}}
        },
        {
            "jsonrpc": "2.0",
            "id": 16,
            "method": "tools/call",
            "params": {"name": "ext_get_context", "arguments": {}}
        },
    ]
    input_data = "\n".join(json.dumps(r) for r in requests)
    result = subprocess.run(
        ["python3", str(SERVER_PATH)],
        input=input_data,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    responses = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
    assert len(responses) == 4, f"Expected 4 responses, got {len(responses)}"

    set_resp = responses[0]["result"]
    assert not set_resp.get("isError", False), "ext_set_context should succeed with token"

    get_resp = responses[1]["result"]
    get_text = get_resp["content"][0]["text"]
    assert "README.md" in get_text, f"Expected payload in get_context: {get_text}"

    clear_resp = responses[2]["result"]
    assert not clear_resp.get("isError", False), "ext_clear_context should succeed with token"

    get_resp2 = responses[3]["result"]
    get_text2 = get_resp2["content"][0]["text"]
    assert "none set" in get_text2, f"Expected none set after clear: {get_text2}"

    print("✓ Extension context lifecycle works")


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
                "cwd": str(REPO_ROOT)
            }
        }
    }

    result = subprocess.run(
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
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
                "cwd": str(REPO_ROOT)
            }
        }
    }

    result = subprocess.run(
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
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
                "cwd": str(REPO_ROOT)
            }
        }
    }

    result = subprocess.run(
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
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
        ["python3", str(SERVER_PATH)],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT)
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
        test_tools_list_from_other_cwd()
        test_read_only_tools()
        test_write_protection()
        test_codex_endpoint_not_configured()
        test_verdent_endpoint_not_configured()
        test_extension_context_tools()
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
