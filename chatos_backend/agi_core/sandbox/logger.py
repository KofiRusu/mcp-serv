"""
Sandbox Logger for AGI Core

Logs and tracks all sandbox operations for analysis and training.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from enum import Enum


class SandboxOperation(Enum):
    """Types of sandbox operations."""
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    FILE_CREATE = "file_create"
    DIRECTORY_CREATE = "directory_create"
    CODE_EXECUTE = "code_execute"
    SEARCH = "search"
    IMPORT = "import"
    UPLOAD = "upload"


@dataclass
class SandboxLogEntry:
    """A single sandbox operation log entry."""
    operation: SandboxOperation
    path: str = ""
    success: bool = True
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    duration_ms: float = 0.0
    error: Optional[str] = None
    session_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation.value,
            "path": self.path,
            "success": self.success,
            "details": self.details,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "session_id": self.session_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SandboxLogEntry":
        return cls(
            operation=SandboxOperation(data["operation"]),
            path=data.get("path", ""),
            success=data.get("success", True),
            details=data.get("details", {}),
            timestamp=data.get("timestamp", time.time()),
            duration_ms=data.get("duration_ms", 0.0),
            error=data.get("error"),
            session_id=data.get("session_id", ""),
        )


@dataclass
class ExecutionLog:
    """Log entry for code execution."""
    code: str
    file_path: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    success: bool = True
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code[:500] if len(self.code) > 500 else self.code,
            "code_length": len(self.code),
            "file_path": self.file_path,
            "stdout": self.stdout[:1000] if len(self.stdout) > 1000 else self.stdout,
            "stderr": self.stderr[:500] if len(self.stderr) > 500 else self.stderr,
            "exit_code": self.exit_code,
            "execution_time": self.execution_time,
            "success": self.success,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }


class SandboxLogger:
    """
    Logger for sandbox operations.
    
    Tracks all file operations, code executions, and provides
    analytics for training and debugging.
    
    Usage:
        logger = SandboxLogger()
        logger.log_file_read("/path/to/file.py", success=True)
        logger.log_execution(code="print('hi')", stdout="hi", exit_code=0)
        stats = logger.get_stats()
    """
    
    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path.home() / "ChatOS-Memory" / "agi" / "sandbox_logs"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.log_file = self.storage_path / "operations.json"
        self.execution_log_file = self.storage_path / "executions.json"
        
        self._entries: List[SandboxLogEntry] = []
        self._executions: List[ExecutionLog] = []
        self._session_id = f"sandbox_{int(time.time())}"
        
        self._load()
    
    def _load(self) -> None:
        """Load existing logs from disk."""
        if self.log_file.exists():
            try:
                data = json.loads(self.log_file.read_text(encoding="utf-8"))
                self._entries = [SandboxLogEntry.from_dict(e) for e in data.get("entries", [])[-500:]]
            except Exception:
                pass
        
        if self.execution_log_file.exists():
            try:
                data = json.loads(self.execution_log_file.read_text(encoding="utf-8"))
                self._executions = [
                    ExecutionLog(**{k: v for k, v in e.items() if k != "code_length"})
                    for e in data.get("executions", [])[-200:]
                ]
            except Exception:
                pass
    
    def _save(self) -> None:
        """Save logs to disk."""
        # Save operation logs
        data = {
            "version": 1,
            "updated_at": time.time(),
            "entries": [e.to_dict() for e in self._entries[-500:]],
        }
        self.log_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        
        # Save execution logs
        exec_data = {
            "version": 1,
            "updated_at": time.time(),
            "executions": [e.to_dict() for e in self._executions[-200:]],
        }
        self.execution_log_file.write_text(json.dumps(exec_data, indent=2), encoding="utf-8")
    
    def set_session(self, session_id: str) -> None:
        """Set the current session ID."""
        self._session_id = session_id
    
    def log_operation(
        self,
        operation: SandboxOperation,
        path: str = "",
        success: bool = True,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: float = 0.0,
        error: Optional[str] = None,
    ) -> SandboxLogEntry:
        """Log a sandbox operation."""
        entry = SandboxLogEntry(
            operation=operation,
            path=path,
            success=success,
            details=details or {},
            duration_ms=duration_ms,
            error=error,
            session_id=self._session_id,
        )
        
        self._entries.append(entry)
        self._save()
        return entry
    
    def log_file_read(self, path: str, success: bool = True, size: int = 0, error: str = None) -> SandboxLogEntry:
        """Log a file read operation."""
        return self.log_operation(
            SandboxOperation.FILE_READ,
            path=path,
            success=success,
            details={"size": size},
            error=error,
        )
    
    def log_file_write(self, path: str, success: bool = True, size: int = 0, error: str = None) -> SandboxLogEntry:
        """Log a file write operation."""
        return self.log_operation(
            SandboxOperation.FILE_WRITE,
            path=path,
            success=success,
            details={"size": size},
            error=error,
        )
    
    def log_file_delete(self, path: str, success: bool = True, error: str = None) -> SandboxLogEntry:
        """Log a file delete operation."""
        return self.log_operation(
            SandboxOperation.FILE_DELETE,
            path=path,
            success=success,
            error=error,
        )
    
    def log_directory_create(self, path: str, success: bool = True, error: str = None) -> SandboxLogEntry:
        """Log a directory creation operation."""
        return self.log_operation(
            SandboxOperation.DIRECTORY_CREATE,
            path=path,
            success=success,
            error=error,
        )
    
    def log_search(self, pattern: str, path: str, results_count: int, success: bool = True) -> SandboxLogEntry:
        """Log a search operation."""
        return self.log_operation(
            SandboxOperation.SEARCH,
            path=path,
            success=success,
            details={"pattern": pattern, "results_count": results_count},
        )
    
    def log_import(self, source: str, target: str, success: bool = True, files_count: int = 0, error: str = None) -> SandboxLogEntry:
        """Log an import operation."""
        return self.log_operation(
            SandboxOperation.IMPORT,
            path=target,
            success=success,
            details={"source": source, "files_count": files_count},
            error=error,
        )
    
    def log_execution(
        self,
        code: str,
        file_path: Optional[str] = None,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 0,
        execution_time: float = 0.0,
    ) -> ExecutionLog:
        """Log a code execution."""
        success = exit_code == 0 and not stderr
        
        log = ExecutionLog(
            code=code,
            file_path=file_path,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            execution_time=execution_time,
            success=success,
            session_id=self._session_id,
        )
        
        self._executions.append(log)
        
        # Also log as operation
        self.log_operation(
            SandboxOperation.CODE_EXECUTE,
            path=file_path or "",
            success=success,
            details={
                "exit_code": exit_code,
                "execution_time": execution_time,
                "code_length": len(code),
                "has_error": bool(stderr),
            },
            error=stderr if stderr else None,
        )
        
        return log
    
    def get_recent_operations(self, limit: int = 50, operation: Optional[SandboxOperation] = None) -> List[Dict]:
        """Get recent operations."""
        entries = self._entries
        
        if operation:
            entries = [e for e in entries if e.operation == operation]
        
        return [e.to_dict() for e in entries[-limit:]]
    
    def get_recent_executions(self, limit: int = 20, successful_only: bool = False) -> List[Dict]:
        """Get recent code executions."""
        executions = self._executions
        
        if successful_only:
            executions = [e for e in executions if e.success]
        
        return [e.to_dict() for e in executions[-limit:]]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sandbox usage statistics."""
        total_ops = len(self._entries)
        total_execs = len(self._executions)
        
        # Count by operation type
        by_operation = {}
        for entry in self._entries:
            op_name = entry.operation.value
            by_operation[op_name] = by_operation.get(op_name, 0) + 1
        
        # Success rate
        successful = sum(1 for e in self._entries if e.success)
        success_rate = successful / total_ops if total_ops > 0 else 0
        
        # Execution success rate
        exec_successful = sum(1 for e in self._executions if e.success)
        exec_success_rate = exec_successful / total_execs if total_execs > 0 else 0
        
        # Most accessed files
        file_access = {}
        for entry in self._entries:
            if entry.path:
                file_access[entry.path] = file_access.get(entry.path, 0) + 1
        
        top_files = sorted(file_access.items(), key=lambda x: x[1], reverse=True)[:10]
        
        return {
            "total_operations": total_ops,
            "total_executions": total_execs,
            "by_operation": by_operation,
            "success_rate": success_rate,
            "execution_success_rate": exec_success_rate,
            "top_files": dict(top_files),
            "session_id": self._session_id,
        }
    
    def export_for_training(self, output_path: Optional[Path] = None, min_success: bool = True) -> int:
        """
        Export execution logs as training data.
        
        Args:
            output_path: Output file path
            min_success: Only include successful executions
            
        Returns:
            Number of examples exported
        """
        output_path = output_path or self.storage_path / f"sandbox_training_{int(time.time())}.jsonl"
        
        examples = []
        for execution in self._executions:
            if min_success and not execution.success:
                continue
            
            # Create instruction-response pairs
            if execution.code and execution.stdout:
                example = {
                    "instruction": f"Execute Python code: {execution.code[:200]}",
                    "input": execution.code,
                    "output": f"Exit code: {execution.exit_code}\nOutput: {execution.stdout}",
                    "metadata": {
                        "source": "sandbox_execution",
                        "success": execution.success,
                    }
                }
                examples.append(example)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for example in examples:
                f.write(json.dumps(example) + "\n")
        
        return len(examples)
    
    def clear_logs(self, older_than_days: int = 30) -> int:
        """Clear old logs."""
        cutoff = time.time() - (older_than_days * 86400)
        
        old_count = len(self._entries)
        self._entries = [e for e in self._entries if e.timestamp > cutoff]
        self._executions = [e for e in self._executions if e.timestamp > cutoff]
        
        removed = old_count - len(self._entries)
        self._save()
        return removed


# Singleton instance
_sandbox_logger: Optional[SandboxLogger] = None


def get_sandbox_logger() -> SandboxLogger:
    """Get the singleton sandbox logger instance."""
    global _sandbox_logger
    if _sandbox_logger is None:
        _sandbox_logger = SandboxLogger()
    return _sandbox_logger

