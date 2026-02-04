"""
Engineer Tools - Git, ripgrep, and safe command execution

Provides read-only engineer tools for the MCP server.
"""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from .path_sandbox import PathSandbox


# Strict allowlist of allowed commands
ALLOWED_COMMANDS = {
    "pytest",
    "pnpm",
    "npm",
    "node",
    "python",
    "python3",
    "ruff",
    "mypy",
    "alembic",
    "git",
    "rg",
}


def git_status(cwd: str) -> Dict[str, Any]:
    """
    Get git repository status.

    Args:
        cwd: Working directory (must be within sandbox)

    Returns:
        Dict with status output and return code
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "status": result.stdout.strip(),
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "git status timed out",
            "returncode": -1
        }
    except Exception as e:
        return {
            "error": str(e),
            "returncode": -1
        }


def git_diff(cwd: str, ref: str = "HEAD") -> Dict[str, Any]:
    """
    Get git diff between commits or working tree.

    Args:
        cwd: Working directory (must be within sandbox)
        ref: Git reference to diff against (default: HEAD)

    Returns:
        Dict with diff output and return code
    """
    try:
        result = subprocess.run(
            ["git", "diff", ref],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "diff": result.stdout,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "git diff timed out",
            "returncode": -1
        }
    except Exception as e:
        return {
            "error": str(e),
            "returncode": -1
        }


def git_show(cwd: str, ref: str = "HEAD") -> Dict[str, Any]:
    """
    Show commit details.

    Args:
        cwd: Working directory (must be within sandbox)
        ref: Git reference to show (default: HEAD)

    Returns:
        Dict with show output and return code
    """
    try:
        result = subprocess.run(
            ["git", "show", "--stat", ref],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "show": result.stdout,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "error": "git show timed out",
            "returncode": -1
        }
    except Exception as e:
        return {
            "error": str(e),
            "returncode": -1
        }


def ripgrep_search(
    query: str,
    path: str = ".",
    glob: str = "*",
    context_lines: int = 2
) -> Dict[str, Any]:
    """
    Search using ripgrep (rg) with Python fallback.

    Args:
        query: Search pattern
        path: Directory to search (default: current)
        glob: File pattern (default: *)
        context_lines: Number of context lines (default: 2)

    Returns:
        Dict with search results and return code
    """
    # Check if ripgrep is available
    rg_available = shutil.which("rg") is not None

    if rg_available:
        try:
            cmd = [
                "rg",
                query,
                "-g", glob,
                "-C", str(context_lines),
                "--json"
            ]
            result = subprocess.run(
                cmd,
                cwd=path,
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "results": result.stdout,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "error": "ripgrep search timed out",
                "returncode": -1
            }
        except Exception as e:
            return {
                "error": str(e),
                "returncode": -1
            }
    else:
        # Python fallback using pathlib and basic string search
        try:
            search_path = Path(path)
            results = []

            # Recursively find matching files
            for file_path in search_path.rglob(glob):
                if file_path.is_file():
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        lines = content.split("\n")

                        # Find matching lines
                        for i, line in enumerate(lines):
                            if query.lower() in line.lower():
                                # Get context lines
                                start = max(0, i - context_lines)
                                end = min(len(lines), i + context_lines + 1)

                                context = "\n".join(
                                    f"{j + 1}:{lines[j]}" for j in range(start, end)
                                )

                                results.append({
                                    "file": str(file_path),
                                    "line": i + 1,
                                    "context": context
                                })
                    except Exception:
                        # Skip files that can't be read
                        continue

            return {
                "results": str(results),
                "returncode": 0,
                "fallback": "python"
            }
        except Exception as e:
            return {
                "error": str(e),
                "returncode": -1
            }


def run_cmd(
    cmd: List[str],
    cwd: str,
    sandbox: PathSandbox,
    timeout_sec: int = 60
) -> Dict[str, Any]:
    """
    Run an allowed command with sandboxing and timeout.

    Args:
        cmd: Command as list of strings (e.g., ["git", "status"])
        cwd: Working directory (must be within sandbox)
        sandbox: PathSandbox instance for validation
        timeout_sec: Timeout in seconds (default: 60)

    Returns:
        Dict with stdout, stderr, and return code
    """
    # Security: Check command is allowed
    if not cmd:
        return {
            "error": "Empty command",
            "returncode": -1
        }

    command_name = cmd[0]
    if command_name not in ALLOWED_COMMANDS:
        return {
            "error": (
                f"Command '{command_name}' not in allowlist. "
                f"Allowed commands: {', '.join(sorted(ALLOWED_COMMANDS))}"
            ),
            "returncode": -1
        }

    # Security: Validate cwd is within sandbox
    if not sandbox.validate_path(cwd):
        return {
            "error": f"Path '{cwd}' outside sandbox: {sandbox.allowed_root}",
            "returncode": -1
        }

    # Execute command safely (no shell=True)
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            # Security: Never use shell=True
            shell=False
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {
            "error": f"Command timed out after {timeout_sec} seconds",
            "returncode": -1
        }
    except Exception as e:
        return {
            "error": str(e),
            "returncode": -1
        }
