"""
sandbox.py - Coding sandbox with file operations.

Provides a safe environment for code editing, file management,
and code execution. Similar to Cursor's coding capabilities.
"""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ChatOS.config import (
    SANDBOX_ALLOWED_EXTENSIONS,
    SANDBOX_DIR,
    SANDBOX_MAX_FILE_SIZE,
)


@dataclass
class FileInfo:
    """Information about a file in the sandbox."""
    
    name: str
    path: str
    extension: str
    size: int
    modified: datetime
    is_directory: bool = False
    children: List["FileInfo"] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "path": self.path,
            "extension": self.extension,
            "size": self.size,
            "modified": self.modified.isoformat(),
            "is_directory": self.is_directory,
            "children": [c.to_dict() for c in self.children] if self.children else [],
        }


@dataclass
class CodeEdit:
    """Represents a code edit operation."""
    
    file_path: str
    old_content: Optional[str] = None
    new_content: str = ""
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    operation: str = "replace"  # replace, insert, delete
    
    
@dataclass
class ExecutionResult:
    """Result of code execution."""
    
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0


class SandboxManager:
    """
    Manages the coding sandbox environment.
    
    Provides file operations, code editing, and safe execution
    in an isolated environment.
    """
    
    def __init__(self, sandbox_dir: Optional[Path] = None):
        self.sandbox_dir = sandbox_dir or SANDBOX_DIR
        self._ensure_sandbox_exists()
        self._edit_history: List[CodeEdit] = []
    
    def _ensure_sandbox_exists(self) -> None:
        """Create sandbox directory if it doesn't exist."""
        self.sandbox_dir.mkdir(parents=True, exist_ok=True)
    
    def _validate_path(self, path: str) -> Path:
        """
        Validate and resolve a path within the sandbox.
        
        Args:
            path: The path to validate
            
        Returns:
            Resolved Path object
            
        Raises:
            ValueError: If path is outside sandbox
        """
        # Handle both absolute and relative paths
        if os.path.isabs(path):
            resolved = Path(path).resolve()
        else:
            resolved = (self.sandbox_dir / path).resolve()
        
        # Ensure path is within sandbox
        try:
            resolved.relative_to(self.sandbox_dir.resolve())
        except ValueError:
            raise ValueError(f"Path {path} is outside the sandbox")
        
        return resolved
    
    def _is_allowed_extension(self, path: Path) -> bool:
        """Check if file extension is allowed."""
        return path.suffix.lower() in SANDBOX_ALLOWED_EXTENSIONS
    
    # =========================================================================
    # File Operations
    # =========================================================================
    
    def list_files(self, path: str = "") -> List[FileInfo]:
        """
        List files in a directory.
        
        Args:
            path: Relative path within sandbox (empty for root)
            
        Returns:
            List of FileInfo objects
        """
        dir_path = self._validate_path(path) if path else self.sandbox_dir
        
        if not dir_path.is_dir():
            return []
        
        files = []
        for item in sorted(dir_path.iterdir()):
            stat = item.stat()
            info = FileInfo(
                name=item.name,
                path=str(item.relative_to(self.sandbox_dir)),
                extension=item.suffix,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                is_directory=item.is_dir(),
            )
            files.append(info)
        
        return files
    
    def get_file_tree(self, max_depth: int = 3) -> FileInfo:
        """
        Get the complete file tree of the sandbox.
        
        Args:
            max_depth: Maximum depth to traverse
            
        Returns:
            FileInfo with nested children
        """
        def build_tree(path: Path, depth: int) -> FileInfo:
            stat = path.stat()
            info = FileInfo(
                name=path.name,
                path=str(path.relative_to(self.sandbox_dir)) if path != self.sandbox_dir else "",
                extension=path.suffix,
                size=stat.st_size,
                modified=datetime.fromtimestamp(stat.st_mtime),
                is_directory=path.is_dir(),
            )
            
            if path.is_dir() and depth < max_depth:
                for child in sorted(path.iterdir()):
                    if not child.name.startswith('.'):
                        info.children.append(build_tree(child, depth + 1))
            
            return info
        
        return build_tree(self.sandbox_dir, 0)
    
    def read_file(self, path: str) -> str:
        """
        Read file contents.
        
        Args:
            path: Path to file
            
        Returns:
            File contents as string
        """
        file_path = self._validate_path(path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if file_path.stat().st_size > SANDBOX_MAX_FILE_SIZE:
            raise ValueError(f"File too large: {path}")
        
        return file_path.read_text(encoding='utf-8')
    
    def write_file(self, path: str, content: str) -> bool:
        """
        Write content to a file.
        
        Args:
            path: Path to file
            content: Content to write
            
        Returns:
            True if successful
        """
        file_path = self._validate_path(path)
        
        if not self._is_allowed_extension(file_path):
            raise ValueError(f"File type not allowed: {file_path.suffix}")
        
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Store old content for history
        old_content = None
        if file_path.exists():
            old_content = file_path.read_text(encoding='utf-8')
        
        # Write new content
        file_path.write_text(content, encoding='utf-8')
        
        # Record edit
        self._edit_history.append(CodeEdit(
            file_path=path,
            old_content=old_content,
            new_content=content,
            operation="replace",
        ))
        
        return True
    
    def create_file(self, path: str, content: str = "") -> bool:
        """Create a new file."""
        file_path = self._validate_path(path)
        
        if file_path.exists():
            raise FileExistsError(f"File already exists: {path}")
        
        return self.write_file(path, content)
    
    def delete_file(self, path: str) -> bool:
        """Delete a file or directory."""
        file_path = self._validate_path(path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        
        return True
    
    def rename_file(self, old_path: str, new_path: str) -> bool:
        """Rename or move a file."""
        old = self._validate_path(old_path)
        new = self._validate_path(new_path)
        
        if not old.exists():
            raise FileNotFoundError(f"File not found: {old_path}")
        
        old.rename(new)
        return True
    
    def create_directory(self, path: str) -> bool:
        """Create a new directory."""
        dir_path = self._validate_path(path)
        dir_path.mkdir(parents=True, exist_ok=True)
        return True
    
    # =========================================================================
    # Code Editing
    # =========================================================================
    
    def apply_edit(self, edit: CodeEdit) -> str:
        """
        Apply a code edit to a file.
        
        Args:
            edit: The edit to apply
            
        Returns:
            The new file content
        """
        file_path = self._validate_path(edit.file_path)
        
        if edit.operation == "replace" and edit.line_start is None:
            # Full file replacement
            return self.write_file(edit.file_path, edit.new_content)
        
        # Read existing content
        if file_path.exists():
            lines = file_path.read_text(encoding='utf-8').splitlines(keepends=True)
        else:
            lines = []
        
        if edit.operation == "insert":
            # Insert at line
            line_num = edit.line_start or len(lines)
            new_lines = edit.new_content.splitlines(keepends=True)
            lines = lines[:line_num] + new_lines + lines[line_num:]
            
        elif edit.operation == "delete":
            # Delete lines
            start = (edit.line_start or 1) - 1
            end = edit.line_end or start + 1
            lines = lines[:start] + lines[end:]
            
        elif edit.operation == "replace":
            # Replace line range
            start = (edit.line_start or 1) - 1
            end = edit.line_end or start + 1
            new_lines = edit.new_content.splitlines(keepends=True)
            lines = lines[:start] + new_lines + lines[end:]
        
        new_content = ''.join(lines)
        self.write_file(edit.file_path, new_content)
        return new_content
    
    def search_in_files(
        self,
        pattern: str,
        path: str = "",
        file_pattern: str = "*"
    ) -> List[Dict[str, Any]]:
        """
        Search for a pattern in files.
        
        Args:
            pattern: Search pattern
            path: Directory to search
            file_pattern: Glob pattern for files
            
        Returns:
            List of matches with file, line, and content
        """
        import fnmatch
        
        search_dir = self._validate_path(path) if path else self.sandbox_dir
        matches = []
        
        for file_path in search_dir.rglob(file_pattern):
            if not file_path.is_file():
                continue
            if not self._is_allowed_extension(file_path):
                continue
            
            try:
                content = file_path.read_text(encoding='utf-8')
                for i, line in enumerate(content.splitlines(), 1):
                    if pattern.lower() in line.lower():
                        matches.append({
                            "file": str(file_path.relative_to(self.sandbox_dir)),
                            "line": i,
                            "content": line.strip(),
                        })
            except Exception:
                continue
        
        return matches
    
    # =========================================================================
    # Code Execution
    # =========================================================================
    
    def execute_python(
        self,
        code: Optional[str] = None,
        file_path: Optional[str] = None,
        timeout: int = 30
    ) -> ExecutionResult:
        """
        Execute Python code safely.
        
        Args:
            code: Code to execute (if no file_path)
            file_path: Path to Python file
            timeout: Execution timeout in seconds
            
        Returns:
            ExecutionResult with output
        """
        import time
        
        start_time = time.time()
        
        if file_path:
            path = self._validate_path(file_path)
            if not path.exists():
                return ExecutionResult(
                    success=False,
                    stderr=f"File not found: {file_path}",
                    exit_code=1,
                )
            cmd = ["python", str(path)]
        elif code:
            # Write code to temp file
            with tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.py',
                delete=False
            ) as f:
                f.write(code)
                temp_path = f.name
            cmd = ["python", temp_path]
        else:
            return ExecutionResult(
                success=False,
                stderr="No code or file provided",
                exit_code=1,
            )
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self.sandbox_dir),
            )
            
            return ExecutionResult(
                success=result.returncode == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                execution_time=time.time() - start_time,
            )
            
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                success=False,
                stderr=f"Execution timed out after {timeout}s",
                exit_code=-1,
                execution_time=timeout,
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stderr=str(e),
                exit_code=-1,
                execution_time=time.time() - start_time,
            )
        finally:
            # Clean up temp file if used
            if code and 'temp_path' in locals():
                os.unlink(temp_path)
    
    def get_undo_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent edit history for undo."""
        history = []
        for edit in self._edit_history[-limit:]:
            history.append({
                "file": edit.file_path,
                "operation": edit.operation,
                "has_undo": edit.old_content is not None,
            })
        return list(reversed(history))
    
    def undo_last_edit(self) -> Optional[str]:
        """Undo the last edit if possible."""
        if not self._edit_history:
            return None
        
        last_edit = self._edit_history.pop()
        if last_edit.old_content is not None:
            self.write_file(last_edit.file_path, last_edit.old_content)
            return last_edit.file_path
        
        return None


# Singleton instance
_sandbox: Optional[SandboxManager] = None


def get_sandbox() -> SandboxManager:
    """Get the singleton sandbox manager instance."""
    global _sandbox
    if _sandbox is None:
        _sandbox = SandboxManager()
    return _sandbox

