"""
Automation Runner - Runs automations in dev mode as Python subprocesses.

Manages the lifecycle of running automations for testing.
"""

import asyncio
import subprocess
import sys
import os
import signal
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Callable
import tempfile

from .automation_store import (
    Automation, AutomationStatus,
    get_automation_store
)


class RunningProcess:
    """Tracks a running automation process."""
    def __init__(self, process: subprocess.Popen, automation_id: str, temp_file: Path):
        self.process = process
        self.automation_id = automation_id
        self.temp_file = temp_file
        self.started_at = datetime.utcnow()
        self.output_lines: list = []


class AutomationRunner:
    """Manages running automation processes."""
    
    def __init__(self):
        self._running: Dict[str, RunningProcess] = {}
        self._store = get_automation_store()
        self._output_callbacks: Dict[str, Callable] = {}
    
    async def start(self, automation_id: str) -> Dict:
        """Start an automation in dev mode."""
        # Check if already running
        if automation_id in self._running:
            return {"success": False, "error": "Automation already running"}
        
        # Get automation
        automation = self._store.get(automation_id)
        if not automation:
            return {"success": False, "error": "Automation not found"}
        
        if not automation.generated_code:
            return {"success": False, "error": "No generated code to run"}
        
        # Create temp file with the code
        temp_dir = Path(tempfile.gettempdir()) / "chatos_automations"
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / f"{automation_id}.py"
        temp_file.write_text(automation.generated_code)
        
        # Create output directory
        output_dir = Path.home() / "ChatOS-v2.0" / "sandbox-ui" / "data" / "automations" / automation_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Update code to use the correct output dir
        code_with_output = automation.generated_code.replace(
            '/app/data',
            str(output_dir)
        )
        temp_file.write_text(code_with_output)
        
        try:
            # Start process
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            
            process = subprocess.Popen(
                [sys.executable, str(temp_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env,
                text=True,
                bufsize=1
            )
            
            # Track it
            running = RunningProcess(process, automation_id, temp_file)
            self._running[automation_id] = running
            
            # Clear old logs and update status
            self._store.clear_logs(automation_id)
            self._store.set_status(automation_id, AutomationStatus.TESTING)
            self._store.add_log(automation_id, f"Started (PID: {process.pid})")
            
            # Start output reader task
            asyncio.create_task(self._read_output(automation_id))
            
            return {
                "success": True,
                "pid": process.pid,
                "output_dir": str(output_dir)
            }
            
        except Exception as e:
            self._store.set_status(automation_id, AutomationStatus.ERROR, str(e))
            self._store.add_log(automation_id, f"Failed to start: {e}")
            return {"success": False, "error": str(e)}
    
    async def _read_output(self, automation_id: str):
        """Read output from running process."""
        if automation_id not in self._running:
            return
        
        running = self._running[automation_id]
        try:
            while True:
                if running.process.poll() is not None:
                    # Process ended - read any remaining output
                    for line in running.process.stdout:
                        if line:
                            stripped = line.strip()
                            running.output_lines.append(stripped)
                            self._store.add_log(automation_id, stripped)
                    break
                
                line = running.process.stdout.readline()
                if line:
                    stripped = line.strip()
                    running.output_lines.append(stripped)
                    # Keep only last 1000 lines
                    running.output_lines = running.output_lines[-1000:]
                    
                    # Log ALL output to store (important for single-run automations)
                    self._store.add_log(automation_id, stripped)
                    
                    # Call callback if registered
                    if automation_id in self._output_callbacks:
                        await self._output_callbacks[automation_id](stripped)
                
                await asyncio.sleep(0.01)
            
            # Process ended - update status
            exit_code = running.process.returncode
            if exit_code == 0:
                self._store.set_status(automation_id, AutomationStatus.STOPPED)
                self._store.add_log(automation_id, "✓ Completed")
            else:
                self._store.set_status(automation_id, AutomationStatus.ERROR, f"Exit code: {exit_code}")
                self._store.add_log(automation_id, f"✗ Failed (exit code {exit_code})")
            
            # Cleanup
            if automation_id in self._running:
                del self._running[automation_id]
                
        except Exception as e:
            self._store.add_log(automation_id, f"Output reader error: {e}")
    
    async def stop(self, automation_id: str) -> Dict:
        """Stop a running automation."""
        if automation_id not in self._running:
            return {"success": False, "error": "Automation not running"}
        
        running = self._running[automation_id]
        
        try:
            # Try graceful termination first
            running.process.terminate()
            
            # Wait up to 5 seconds
            for _ in range(50):
                if running.process.poll() is not None:
                    break
                await asyncio.sleep(0.1)
            
            # Force kill if still running
            if running.process.poll() is None:
                running.process.kill()
                await asyncio.sleep(0.5)
            
            # Cleanup temp file
            if running.temp_file.exists():
                running.temp_file.unlink()
            
            # Update status
            self._store.set_status(automation_id, AutomationStatus.STOPPED)
            self._store.add_log(automation_id, "Stopped by user")
            
            # Remove from tracking
            del self._running[automation_id]
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_status(self, automation_id: str) -> Dict:
        """Get status of an automation."""
        if automation_id in self._running:
            running = self._running[automation_id]
            return {
                "running": True,
                "pid": running.process.pid,
                "started_at": running.started_at.isoformat(),
                "output_lines": running.output_lines[-50:]  # Last 50 lines
            }
        return {"running": False}
    
    def get_output(self, automation_id: str, lines: int = 100) -> list:
        """Get recent output lines."""
        if automation_id in self._running:
            return self._running[automation_id].output_lines[-lines:]
        return []
    
    def register_output_callback(self, automation_id: str, callback: Callable):
        """Register a callback for output lines."""
        self._output_callbacks[automation_id] = callback
    
    def unregister_output_callback(self, automation_id: str):
        """Unregister output callback."""
        if automation_id in self._output_callbacks:
            del self._output_callbacks[automation_id]
    
    async def stop_all(self):
        """Stop all running automations."""
        for automation_id in list(self._running.keys()):
            await self.stop(automation_id)


# Singleton
_runner: Optional[AutomationRunner] = None

def get_automation_runner() -> AutomationRunner:
    global _runner
    if _runner is None:
        _runner = AutomationRunner()
    return _runner

