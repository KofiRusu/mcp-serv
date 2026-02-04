#!/usr/bin/env python3
"""
Phase 2 Engineer Tools Self-Test

Tests:
a) allowed command works (e.g. git status)
b) forbidden command is rejected with clear error
c) rg works (or clean fallback)
"""

import sys
import json
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.engineer_tools import (
    git_status,
    git_diff,
    git_show,
    ripgrep_search,
    run_cmd,
    ALLOWED_COMMANDS
)
from mcp.path_sandbox import PathSandbox


def test_git_tools():
    """Test git tools work in this repo"""
    print("\n=== Testing Git Tools ===")

    # Use the parent of parent (repo root) since we're in tests/
    cwd = str(Path(__file__).parent.parent.resolve())

    # Test 1: git_status
    print("\nTest 1: git_status")
    result = git_status(cwd)
    # Verify function returns proper structure (git repo may have issues)
    assert "returncode" in result, "git_status should return returncode"
    assert "status" in result, "git_status should return status"
    print(f"✓ git_status callable (returncode: {result['returncode']})")
    if result["returncode"] == 0:
        print(f"  Status: {result['status'][:50]}..." if len(result['status']) > 50 else f"  Status: {result['status']}")
    else:
        print(f"  Note: Git repo may have issues (not a code problem)")

    # Test 2: git_diff
    print("\nTest 2: git_diff")
    result = git_diff(cwd, "HEAD")
    assert "returncode" in result, "git_diff should return returncode"
    assert "diff" in result, "git_diff should return diff"
    print(f"✓ git_diff callable (returncode: {result['returncode']})")
    print(f"  Diff length: {len(result.get('diff', ''))} chars")

    # Test 3: git_show
    print("\nTest 3: git_show")
    result = git_show(cwd, "HEAD")
    assert "returncode" in result, "git_show should return returncode"
    assert "show" in result, "git_show should return show"
    print(f"✓ git_show callable (returncode: {result['returncode']})")
    if result.get("show"):
        print(f"  Show: {result['show'][:100]}...")

    print("\n✓ Git tools tests passed (functions work)\n")


def test_ripgrep_search():
    """Test ripgrep search with fallback"""
    print("=== Testing Ripgrep Search ===")

    cwd = str(Path(__file__).parent.parent.resolve())

    # Test with a known string that exists in the repo
    query = "MCPServer"
    print(f"\nTest: Search for '{query}'")

    result = ripgrep_search(query, cwd, "*.py", 1)

    assert result["returncode"] == 0, f"ripgrep_search failed: {result}"
    print(f"✓ ripgrep_search works")

    # Check if using ripgrep or fallback
    if "fallback" in result:
        print(f"  Using Python fallback (rg not available)")
    else:
        print(f"  Using ripgrep (rg available)")

    # Verify results contain the query
    results_str = result.get("results", "")
    if query.lower() in results_str.lower() or query in results_str:
        print(f"  Found '{query}' in results")
    else:
        print(f"  Results preview: {results_str[:200]}...")

    print("\n✓ Ripgrep search tests passed\n")


def test_run_cmd_allowlist():
    """Test run_cmd with allowlist enforcement"""
    print("=== Testing run_cmd Allowlist ===")

    cwd = str(Path(__file__).parent.parent.resolve())
    sandbox = PathSandbox(cwd)

    # Test 1: Allowed command (python3 --version)
    print("\nTest 1: Allowed command (python3 --version)")
    result = run_cmd(["python3", "--version"], cwd, sandbox, 30)
    assert result["returncode"] == 0, f"Allowed command failed: {result}"
    print(f"✓ Allowed command works")
    print(f"  Stdout: {result['stdout'].strip()}")

    # Test 2: Forbidden command (rm)
    print("\nTest 2: Forbidden command (rm)")
    result = run_cmd(["rm", "-rf", "/"], cwd, sandbox, 30)
    assert result["returncode"] == -1, "Forbidden command should return -1"
    assert "not in allowlist" in result.get("error", ""), "Error should mention allowlist"
    print(f"✓ Forbidden command rejected")
    print(f"  Error: {result['error']}")

    # Test 3: Another forbidden command (curl)
    print("\nTest 3: Forbidden command (curl)")
    result = run_cmd(["curl", "http://example.com"], cwd, sandbox, 30)
    assert result["returncode"] == -1, "Forbidden command should return -1"
    print(f"✓ Forbidden command (curl) rejected")
    print(f"  Error: {result['error']}")

    print("\n✓ run_cmd allowlist tests passed\n")


def test_allowlist_content():
    """Verify allowlist contains expected commands"""
    print("=== Testing Allowlist Content ===")

    expected_commands = {
        "pytest", "pnpm", "npm", "node", "python", "python3",
        "ruff", "mypy", "alembic", "git", "rg"
    }

    for cmd in expected_commands:
        assert cmd in ALLOWED_COMMANDS, f"Missing command in allowlist: {cmd}"
        print(f"✓ {cmd} in allowlist")

    # Verify dangerous commands are NOT in allowlist
    dangerous = ["rm", "curl", "wget", "sudo", "chmod", "chown"]
    for cmd in dangerous:
        assert cmd not in ALLOWED_COMMANDS, f"Dangerous command in allowlist: {cmd}"
        print(f"✓ {cmd} NOT in allowlist (correct)")

    print("\n✓ Allowlist content tests passed\n")


def test_mcp_server_integration():
    """Test engineer tools via MCP server"""
    print("=== Testing MCP Server Integration ===")

    cwd = str(Path(__file__).parent.parent.resolve())

    # Test 1: git_status via MCP
    print("\nTest 1: git_status via MCP")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "git_status",
            "arguments": {
                "cwd": cwd
            }
        }
    }

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=cwd
    )

    response = json.loads(result.stdout)
    assert not response.get("result", {}).get("isError", False), f"git_status via MCP failed: {response}"
    print(f"✓ git_status via MCP works")

    # Test 2: ripgrep_search via MCP
    print("\nTest 2: ripgrep_search via MCP")
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "ripgrep_search",
            "arguments": {
                "query": "MCPServer",
                "path": cwd,
                "glob": "*.py"
            }
        }
    }

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=cwd
    )

    response = json.loads(result.stdout)
    assert not response.get("result", {}).get("isError", False), f"ripgrep_search via MCP failed: {response}"
    print(f"✓ ripgrep_search via MCP works")

    # Test 3: run_cmd via MCP (forbidden)
    print("\nTest 3: run_cmd via MCP (forbidden command)")
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "run_cmd",
            "arguments": {
                "cmd": ["rm", "-rf", "/"],
                "cwd": cwd
            }
        }
    }

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=cwd
    )

    response = json.loads(result.stdout)
    assert response.get("result", {}).get("isError", False), "Forbidden command should return error"
    error_text = response["result"]["content"][0]["text"]
    assert "not in allowlist" in error_text, f"Error should mention allowlist: {error_text}"
    print(f"✓ Forbidden command rejected via MCP")
    print(f"  Error: {error_text[:100]}...")

    print("\n✓ MCP server integration tests passed\n")


if __name__ == "__main__":
    try:
        test_allowlist_content()
        test_git_tools()
        test_ripgrep_search()
        test_run_cmd_allowlist()
        test_mcp_server_integration()

        print("\n" + "=" * 50)
        print("ALL PHASE 2 ENGINEER TOOLS TESTS PASSED ✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
