"""
vscode_manager.py - Manages code-server process for VSCode Sandbox.

Provides lifecycle management for code-server instances, enabling
a full VSCode experience within ChatOS.
"""

import asyncio
import os
import shutil
import signal
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from chatos_backend.config import (
    CODE_SERVER_AUTH,
    CODE_SERVER_HOST,
    CODE_SERVER_PORT,
    SANDBOX_ALLOWED_COMMANDS,
    SANDBOX_COMMAND_TIMEOUT,
    SANDBOX_MAX_OUTPUT_SIZE,
    SANDBOX_PROJECT_ROOTS,
)


@dataclass
class VSCodeStatus:
    """Status of the code-server instance."""
    
    running: bool = False
    pid: Optional[int] = None
    port: int = CODE_SERVER_PORT
    host: str = CODE_SERVER_HOST
    workspace: Optional[str] = None
    url: Optional[str] = None
    started_at: Optional[datetime] = None
    error: Optional[str] = None


@dataclass
class CommandResult:
    """Result of a command execution."""
    
    success: bool
    command: str
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    truncated: bool = False


@dataclass
class ProjectInfo:
    """Information about a project root."""
    
    path: str
    name: str
    exists: bool
    is_git: bool = False
    file_count: int = 0


class VSCodeManager:
    """
    Manages the code-server process lifecycle.
    
    Provides methods to start, stop, and monitor code-server
    for the VSCode sandbox integration.
    """
    
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._workspace: Optional[str] = None
        self._started_at: Optional[datetime] = None
        self._port = CODE_SERVER_PORT
        self._host = CODE_SERVER_HOST
    
    @property
    def is_running(self) -> bool:
        """Check if code-server is currently running."""
        if self._process is None:
            return False
        return self._process.poll() is None
    
    def get_status(self) -> VSCodeStatus:
        """Get the current status of code-server."""
        if not self.is_running:
            return VSCodeStatus(running=False)
        
        return VSCodeStatus(
            running=True,
            pid=self._process.pid if self._process else None,
            port=self._port,
            host=self._host,
            workspace=self._workspace,
            url=f"http://{self._host}:{self._port}",
            started_at=self._started_at,
        )
    
    def _find_code_server(self) -> Optional[str]:
        """Find the code-server executable."""
        # Check common locations
        locations = [
            shutil.which("code-server"),
            "/usr/bin/code-server",
            "/usr/local/bin/code-server",
            str(Path.home() / ".local" / "bin" / "code-server"),
            str(Path.home() / ".nvm" / "versions" / "node" / "current" / "bin" / "code-server"),
        ]
        
        for loc in locations:
            if loc and Path(loc).exists():
                return loc
        
        return None
    
    def _validate_workspace(self, workspace: str) -> bool:
        """
        Validate that the workspace path is allowed.
        
        Args:
            workspace: Path to validate
            
        Returns:
            True if path is within allowed project roots
        """
        try:
            workspace_resolved = Path(workspace).expanduser().resolve()
            
            for root in SANDBOX_PROJECT_ROOTS:
                root_resolved = Path(root).resolve()
                try:
                    workspace_resolved.relative_to(root_resolved)
                    return True
                except ValueError:
                    continue
            
            return False
        except Exception:
            return False
    
    async def start_server(
        self,
        workspace: Optional[str] = None,
        port: Optional[int] = None,
    ) -> VSCodeStatus:
        """
        Start the code-server process.
        
        Args:
            workspace: Directory to open (must be within allowed roots)
            port: Port to run on (defaults to CODE_SERVER_PORT)
            
        Returns:
            VSCodeStatus with server information
        """
        # Check if already running
        if self.is_running:
            return VSCodeStatus(
                running=True,
                pid=self._process.pid if self._process else None,
                port=self._port,
                host=self._host,
                workspace=self._workspace,
                url=f"http://{self._host}:{self._port}",
                started_at=self._started_at,
                error="code-server is already running",
            )
        
        # Find code-server executable
        code_server_path = self._find_code_server()
        if not code_server_path:
            return VSCodeStatus(
                running=False,
                error="code-server not found. Install with: curl -fsSL https://code-server.dev/install.sh | sh",
            )
        
        # Validate workspace
        if workspace:
            if not self._validate_workspace(workspace):
                return VSCodeStatus(
                    running=False,
                    error=f"Workspace '{workspace}' is not within allowed project roots",
                )
            workspace_path = Path(workspace).expanduser().resolve()
            if not workspace_path.exists():
                workspace_path.mkdir(parents=True, exist_ok=True)
        else:
            # Default to first project root
            workspace_path = Path(SANDBOX_PROJECT_ROOTS[0])
            workspace_path.mkdir(parents=True, exist_ok=True)
        
        self._workspace = str(workspace_path)
        self._port = port or CODE_SERVER_PORT
        
        # Build command
        cmd = [
            code_server_path,
            "--bind-addr", f"{self._host}:{self._port}",
            "--auth", CODE_SERVER_AUTH,
            "--disable-telemetry",
            "--disable-update-check",
            str(workspace_path),
        ]
        
        try:
            # Start code-server process
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            self._started_at = datetime.now()
            
            # Wait a bit for startup
            await asyncio.sleep(2)
            
            # Check if still running
            if self._process.poll() is not None:
                stderr = self._process.stderr.read().decode() if self._process.stderr else ""
                return VSCodeStatus(
                    running=False,
                    error=f"code-server failed to start: {stderr}",
                )
            
            return VSCodeStatus(
                running=True,
                pid=self._process.pid,
                port=self._port,
                host=self._host,
                workspace=self._workspace,
                url=f"http://{self._host}:{self._port}",
                started_at=self._started_at,
            )
            
        except Exception as e:
            return VSCodeStatus(
                running=False,
                error=f"Failed to start code-server: {str(e)}",
            )
    
    async def stop_server(self) -> bool:
        """
        Stop the code-server process.
        
        Returns:
            True if successfully stopped
        """
        if not self.is_running:
            return True
        
        try:
            # Send SIGTERM to the process group
            if self._process:
                os.killpg(os.getpgid(self._process.pid), signal.SIGTERM)
                
                # Wait for graceful shutdown
                try:
                    self._process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if not responding
                    os.killpg(os.getpgid(self._process.pid), signal.SIGKILL)
                    self._process.wait()
            
            self._process = None
            self._workspace = None
            self._started_at = None
            return True
            
        except Exception as e:
            print(f"Error stopping code-server: {e}")
            self._process = None
            return False
    
    async def is_healthy(self) -> bool:
        """
        Check if code-server is healthy and responding.
        
        Returns:
            True if code-server is responding to requests
        """
        if not self.is_running:
            return False
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{self._host}:{self._port}/healthz",
                    timeout=aiohttp.ClientTimeout(total=2),
                ) as response:
                    return response.status == 200
        except Exception:
            # If aiohttp not available, just check process
            return self.is_running
    
    def list_project_roots(self) -> List[ProjectInfo]:
        """
        List all configured project roots with information.
        
        Returns:
            List of ProjectInfo for each root
        """
        projects = []
        
        for root in SANDBOX_PROJECT_ROOTS:
            path = Path(root).expanduser().resolve()
            
            # Count files (shallow)
            file_count = 0
            if path.exists():
                try:
                    file_count = sum(1 for _ in path.iterdir())
                except PermissionError:
                    pass
            
            projects.append(ProjectInfo(
                path=str(path),
                name=path.name,
                exists=path.exists(),
                is_git=(path / ".git").exists(),
                file_count=file_count,
            ))
        
        return projects
    
    def validate_command(self, command: str) -> bool:
        """
        Validate that a command is in the allowlist.
        
        Args:
            command: The command (first word) to validate
            
        Returns:
            True if command is allowed
        """
        # Extract the base command (first word)
        base_cmd = command.split()[0] if command.strip() else ""
        
        # Remove any path prefix
        base_cmd = os.path.basename(base_cmd)
        
        return base_cmd in SANDBOX_ALLOWED_COMMANDS
    
    async def run_command(
        self,
        command: str,
        args: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """
        Execute a command in the sandbox.
        
        Args:
            command: The command to execute
            args: Optional list of arguments
            cwd: Working directory (must be within project roots)
            timeout: Execution timeout in seconds
            
        Returns:
            CommandResult with output and status
        """
        import time
        
        start_time = time.time()
        
        # Validate command
        if not self.validate_command(command):
            return CommandResult(
                success=False,
                command=command,
                stderr=f"Command '{command.split()[0]}' is not in the allowlist",
                exit_code=-1,
            )
        
        # Validate working directory
        if cwd:
            if not self._validate_workspace(cwd):
                return CommandResult(
                    success=False,
                    command=command,
                    stderr=f"Working directory '{cwd}' is not within allowed project roots",
                    exit_code=-1,
                )
            work_dir = Path(cwd).expanduser().resolve()
        else:
            work_dir = Path(SANDBOX_PROJECT_ROOTS[0])
        
        # Build full command
        full_cmd = command
        if args:
            full_cmd = f"{command} {' '.join(args)}"
        
        timeout = timeout or SANDBOX_COMMAND_TIMEOUT
        
        try:
            process = await asyncio.create_subprocess_shell(
                full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(work_dir),
            )
            
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return CommandResult(
                    success=False,
                    command=full_cmd,
                    stderr=f"Command timed out after {timeout} seconds",
                    exit_code=-1,
                    execution_time=timeout,
                )
            
            # Decode output
            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")
            
            # Truncate if too large
            truncated = False
            if len(stdout) > SANDBOX_MAX_OUTPUT_SIZE:
                stdout = stdout[:SANDBOX_MAX_OUTPUT_SIZE] + "\n... (output truncated)"
                truncated = True
            if len(stderr) > SANDBOX_MAX_OUTPUT_SIZE:
                stderr = stderr[:SANDBOX_MAX_OUTPUT_SIZE] + "\n... (output truncated)"
                truncated = True
            
            return CommandResult(
                success=process.returncode == 0,
                command=full_cmd,
                stdout=stdout,
                stderr=stderr,
                exit_code=process.returncode or 0,
                execution_time=time.time() - start_time,
                truncated=truncated,
            )
            
        except Exception as e:
            return CommandResult(
                success=False,
                command=full_cmd,
                stderr=str(e),
                exit_code=-1,
                execution_time=time.time() - start_time,
            )


# Singleton instance
_vscode_manager: Optional[VSCodeManager] = None


def get_vscode_manager() -> VSCodeManager:
    """Get the singleton VSCodeManager instance."""
    global _vscode_manager
    if _vscode_manager is None:
        _vscode_manager = VSCodeManager()
    return _vscode_manager

