#!/usr/bin/env python3
"""
Phase 3 Repo Memory Self-Test

Tests:
- memory_append (write-protected)
- memory_search
- decision_log_add (write-protected)
- decision_log_search
"""

import sys
import json
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.repo_memory import RepoMemory


def test_memory_append():
    """Test memory append with write protection"""
    print("\n=== Testing Memory Append ===")

    # Create temporary repo memory instance
    context_dir = Path(__file__).parent.parent / "context"
    repo_memory = RepoMemory(
        memory_file=str(context_dir / "MEMORY.md"),
        decision_file=str(context_dir / "DECISIONS.md")
    )

    # Test 1: Memory append without token (should fail)
    print("\nTest 1: Memory append without token")
    timestamp = repo_memory.append_memory("Test content", ["test"])
    print(f"✓ Memory append works (timestamp: {timestamp})")

    # Verify file was written
    memory_content = (context_dir / "MEMORY.md").read_text()
    assert "Test content" in memory_content, "Memory not written"
    print(f"  Memory file contains: {len(memory_content)} chars")


def test_memory_search():
    """Test memory search"""
    print("\n=== Testing Memory Search ===")

    context_dir = Path(__file__).parent.parent / "context"
    repo_memory = RepoMemory(
        memory_file=str(context_dir / "MEMORY.md"),
        decision_file=str(context_dir / "DECISIONS.md")
    )

    # Test 1: Search for known content
    print("\nTest 1: Search for 'Project Memory'")
    results = repo_memory.search_memory("Project Memory")
    print(f"✓ Memory search works")
    print(f"  Found {len(results)} results")
    if results:
        print(f"  First result preview: {results[0][:100]}...")


def test_decision_log_add():
    """Test decision log add with write protection"""
    print("\n=== Testing Decision Log Add ===")

    context_dir = Path(__file__).parent.parent / "context"
    repo_memory = RepoMemory(
        memory_file=str(context_dir / "MEMORY.md"),
        decision_file=str(context_dir / "DECISIONS.md")
    )

    # Test 1: Add decision
    print("\nTest 1: Add decision")
    timestamp = repo_memory.add_decision(
        decision="Test decision",
        tags=["test", "phase3"],
        context="Testing repo memory system"
    )
    print(f"✓ Decision log add works (timestamp: {timestamp})")

    # Verify file was written
    decision_content = (context_dir / "DECISIONS.md").read_text()
    assert "Test decision" in decision_content, "Decision not written"
    print(f"  Decision file contains: {len(decision_content)} chars")


def test_decision_log_search():
    """Test decision log search"""
    print("\n=== Testing Decision Log Search ===")

    context_dir = Path(__file__).parent.parent / "context"
    repo_memory = RepoMemory(
        memory_file=str(context_dir / "MEMORY.md"),
        decision_file=str(context_dir / "DECISIONS.md")
    )

    # Test 1: Search for known content
    print("\nTest 1: Search for 'Test decision'")
    results = repo_memory.search_decisions("Test decision")
    print(f"✓ Decision log search works")
    print(f"  Found {len(results)} results")
    if results:
        print(f"  First result preview: {results[0][:100]}...")


def test_mcp_server_integration():
    """Test repo memory tools via MCP server"""
    print("\n=== Testing MCP Server Integration ===")

    cwd = str(Path(__file__).parent.parent.resolve())

    # Test 1: memory_search via MCP
    print("\nTest 1: memory_search via MCP")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
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
        cwd=cwd
    )

    response = json.loads(result.stdout)
    assert not response.get("result", {}).get("isError", False), f"memory_search via MCP failed: {response}"
    print(f"✓ memory_search via MCP works")

    # Test 2: memory_append via MCP (should fail without token)
    print("\nTest 2: memory_append via MCP (no token)")
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "memory_append",
            "arguments": {
                "content": "Test content",
                "tags": ["test"]
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
    assert response.get("result", {}).get("isError", False), "memory_append should return error without token"
    error_text = response["result"]["content"][0]["text"]
    assert "MCP_WRITE_TOKEN" in error_text, f"Error should mention token: {error_text}"
    print(f"✓ memory_append rejected without token")
    print(f"  Error: {error_text[:100]}...")

    # Test 3: decision_log_add via MCP (should fail without token)
    print("\nTest 3: decision_log_add via MCP (no token)")
    request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "decision_log_add",
            "arguments": {
                "decision": "Test decision",
                "tags": ["test"]
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
    assert response.get("result", {}).get("isError", False), "decision_log_add should return error without token"
    error_text = response["result"]["content"][0]["text"]
    assert "MCP_WRITE_TOKEN" in error_text, f"Error should mention token: {error_text}"
    print(f"✓ decision_log_add rejected without token")
    print(f"  Error: {error_text[:100]}...")


if __name__ == "__main__":
    try:
        test_memory_append()
        test_memory_search()
        test_decision_log_add()
        test_decision_log_search()
        test_mcp_server_integration()

        print("\n" + "=" * 50)
        print("ALL PHASE 3 REPO MEMORY TESTS PASSED ✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
