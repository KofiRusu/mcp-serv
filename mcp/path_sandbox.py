"""
Path Sandbox - Prevent path traversal attacks

Enforces that all file operations stay within a designated root directory.
Blocks ../ escapes and symlink attacks.
"""

import os
from pathlib import Path
from typing import Optional


class PathSandbox:
    """Path sandbox that prevents directory traversal attacks"""

    def __init__(self, allowed_root: str):
        """
        Initialize sandbox with allowed root directory.

        Args:
            allowed_root: The root directory that all paths must stay within
        """
        self.allowed_root = Path(allowed_root).resolve()
        self.allowed_root_str = str(self.allowed_root)

    def validate_path(self, path: str) -> Optional[Path]:
        """
        Validate that a path is within the allowed root.

        Args:
            path: The path to validate

        Returns:
            Resolved Path if valid, None if outside sandbox or invalid
        """
        try:
            # Resolve to absolute path (follows symlinks by default)
            resolved = Path(path).resolve()

            # Check if resolved path starts with allowed root
            resolved_str = str(resolved)
            if resolved_str == self.allowed_root_str:
                # Exact match to root is allowed
                return resolved
            if resolved_str.startswith(self.allowed_root_str + os.sep):
                # Path is within root (with path separator to avoid prefix matches)
                return resolved

            return None
        except (OSError, RuntimeError, ValueError):
            # Invalid path, permission error, etc.
            return None

    def sanitize_path(self, path: str) -> Optional[str]:
        """
        Return safe absolute path string or None if invalid.

        Args:
            path: The path to sanitize

        Returns:
            Safe absolute path string or None
        """
        validated = self.validate_path(path)
        return str(validated) if validated else None

    def get_error_message(self, path: str) -> str:
        """
        Get a user-friendly error message for a rejected path.

        Args:
            path: The rejected path

        Returns:
            Error message explaining why the path was rejected
        """
        return (
            f"Path '{path}' is outside the allowed sandbox. "
            f"All paths must be within: {self.allowed_root}"
        )
