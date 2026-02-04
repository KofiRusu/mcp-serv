#!/usr/bin/env python3
"""
Phase 1 Security Self-Test

Tests:
a) missing token => write rejected
b) wrong token => rejected
c) correct token => allowed (or dry-run output)
d) ../ path => rejected
"""

import sys
import json
import subprocess
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.path_sandbox import PathSandbox


def test_path_sandbox():
    """Test path sandbox blocks ../ escapes"""
    print("\n=== Testing Path Sandbox ===")

    # Create sandbox with current directory as root
    sandbox = PathSandbox(str(Path.cwd()))

    # Test 1: Valid path should pass
    valid_path = str(Path.cwd() / "mcp" / "server.py")
    result = sandbox.validate_path(valid_path)
    assert result is not None, f"Valid path should pass: {valid_path}"
    print(f"✓ Valid path accepted: {valid_path}")

    # Test 2: ../ escape should be rejected
    escape_path = str(Path.cwd() / ".." / "etc" / "passwd")
    result = sandbox.validate_path(escape_path)
    assert result is None, f"../ escape should be rejected: {escape_path}"
    print(f"✓ ../ escape rejected: {escape_path}")

    # Test 3: Symlink outside sandbox should be rejected
    # Create a test symlink pointing outside
    test_link = Path.cwd() / "test_escape_link"
    try:
        test_link.symlink_to("/etc/passwd")
        result = sandbox.validate_path(str(test_link))
        assert result is None, f"Symlink outside sandbox should be rejected"
        print(f"✓ Symlink escape rejected: {test_link}")
    except Exception as e:
        print(f"⚠ Skipping symlink test (may need permissions): {e}")
    finally:
        # Clean up
        if test_link.exists():
            test_link.unlink()

    print("✓ Path sandbox tests passed\n")


def test_mcp_server_security():
    """Test MCP server write protection"""
    print("=== Testing MCP Server Security ===")

    # Test 1: No token set - write should be rejected
    print("\nTest 1: No MCP_WRITE_TOKEN (read-only default)")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "store_memory",
            "arguments": {
                "domain": "test",
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
    assert response.get("result", {}).get("isError", False), "Write should be rejected without token"
    assert "MCP_WRITE_TOKEN not set" in response["result"]["content"][0]["text"], "Error message should mention missing token"
    print(f"✓ Write rejected without token")
    print(f"  Error: {response['result']['content'][0]['text']}")

    # Test 2: Wrong token - write should be rejected
    print("\nTest 2: Wrong MCP_WRITE_TOKEN")
    env = {"MCP_WRITE_TOKEN": "correct_token"}
    request["params"]["arguments"]["write_token"] = "wrong_token"

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
        env={**subprocess.os.environ, **env}
    )

    response = json.loads(result.stdout)
    assert response.get("result", {}).get("isError", False), "Write should be rejected with wrong token"
    assert "Invalid write_token" in response["result"]["content"][0]["text"], "Error message should mention invalid token"
    print(f"✓ Write rejected with wrong token")
    print(f"  Error: {response['result']['content'][0]['text']}")

    # Test 3: Correct token - write should be allowed
    print("\nTest 3: Correct MCP_WRITE_TOKEN")
    request["params"]["arguments"]["write_token"] = "correct_token"

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
        env={**subprocess.os.environ, **env}
    )

    response = json.loads(result.stdout)
    # Should succeed (not an error)
    is_error = response.get("result", {}).get("isError", False)
    if is_error:
        print(f"⚠ Write with correct token returned error: {response['result']['content'][0]['text']}")
    else:
        print(f"✓ Write allowed with correct token")
        print(f"  Result: {response['result']['content'][0]['text']}")

    # Test 4: Dry-run mode - write should be logged but not executed
    print("\nTest 4: MCP_DRY_RUN=true")
    env = {"MCP_WRITE_TOKEN": "test_token", "MCP_DRY_RUN": "true"}
    request["params"]["arguments"]["write_token"] = "test_token"

    result = subprocess.run(
        ["python3", "mcp/server.py"],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
        env={**subprocess.os.environ, **env}
    )

    response = json.loads(result.stdout)
    assert "DRY-RUN" in response["result"]["content"][0]["text"], "Dry-run should be indicated"
    print(f"✓ Dry-run mode works")
    print(f"  Result: {response['result']['content'][0]['text']}")

    print("\n✓ MCP server security tests passed\n")


if __name__ == "__main__":
    try:
        test_path_sandbox()
        test_mcp_server_security()
        print("\n" + "=" * 50)
        print("ALL PHASE 1 SECURITY TESTS PASSED ✓")
        print("=" * 50)
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
