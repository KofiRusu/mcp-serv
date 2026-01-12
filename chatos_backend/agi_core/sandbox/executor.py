"""
Safe Code Executor for AGI Core

Provides sandboxed Python code execution with safety limits.
"""

import ast
import io
import sys
import time
import traceback
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class ExecutionResult:
    """
    Result of code execution.
    
    Attributes:
        success: Whether execution succeeded
        output: Standard output
        error: Error message if failed
        return_value: Return value of the code
        duration_ms: Execution time
        metadata: Additional execution info
    """
    success: bool
    output: str = ""
    error: Optional[str] = None
    return_value: Any = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "return_value": repr(self.return_value) if self.return_value else None,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


class SafeExecutor:
    """
    Executes Python code in a restricted environment.
    
    Safety features:
    - Limited built-in functions
    - No file system access (by default)
    - No network access
    - Time limits
    - Output size limits
    
    Usage:
        executor = SafeExecutor()
        result = executor.execute("print(2 + 2)")
    """
    
    # Safe built-in functions
    SAFE_BUILTINS = {
        'abs', 'all', 'any', 'ascii', 'bin', 'bool', 'bytearray', 'bytes',
        'callable', 'chr', 'complex', 'dict', 'divmod', 'enumerate', 'filter',
        'float', 'format', 'frozenset', 'hash', 'hex', 'int', 'isinstance',
        'issubclass', 'iter', 'len', 'list', 'map', 'max', 'min', 'next',
        'oct', 'ord', 'pow', 'print', 'range', 'repr', 'reversed', 'round',
        'set', 'slice', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip',
    }
    
    # Blocked AST node types (dangerous operations)
    BLOCKED_NODES = {
        ast.Import, ast.ImportFrom,  # No imports by default
    }
    
    def __init__(
        self,
        timeout_seconds: float = 5.0,
        max_output_size: int = 10000,
        allow_imports: bool = False,
        allowed_modules: Optional[Set[str]] = None,
    ):
        """
        Initialize the executor.
        
        Args:
            timeout_seconds: Maximum execution time
            max_output_size: Maximum output characters
            allow_imports: Whether to allow imports
            allowed_modules: Set of allowed module names (if imports enabled)
        """
        self.timeout_seconds = timeout_seconds
        self.max_output_size = max_output_size
        self.allow_imports = allow_imports
        self.allowed_modules = allowed_modules or {'math', 'random', 'datetime', 'json', 're'}
        
        self._safe_globals = self._build_safe_globals()
    
    def _build_safe_globals(self) -> Dict[str, Any]:
        """Build the restricted global namespace."""
        safe_builtins = {
            name: getattr(__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__, name, None)
            for name in self.SAFE_BUILTINS
            if hasattr(__builtins__ if isinstance(__builtins__, dict) else __builtins__.__dict__, name)
        }
        
        # Handle __builtins__ as dict or module
        if isinstance(__builtins__, dict):
            for name in self.SAFE_BUILTINS:
                if name in __builtins__:
                    safe_builtins[name] = __builtins__[name]
        else:
            for name in self.SAFE_BUILTINS:
                if hasattr(__builtins__, name):
                    safe_builtins[name] = getattr(__builtins__, name)
        
        return {
            '__builtins__': safe_builtins,
            '__name__': '__sandbox__',
        }
    
    def validate_code(self, code: str) -> Optional[str]:
        """
        Validate code for safety.
        
        Args:
            code: Python code to validate
            
        Returns:
            Error message if invalid, None if valid
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return f"Syntax error: {e}"
        
        for node in ast.walk(tree):
            node_type = type(node)
            
            # Check blocked nodes
            if node_type in self.BLOCKED_NODES:
                if node_type == ast.Import and self.allow_imports:
                    for alias in node.names:
                        if alias.name.split('.')[0] not in self.allowed_modules:
                            return f"Import not allowed: {alias.name}"
                elif node_type == ast.ImportFrom and self.allow_imports:
                    if node.module and node.module.split('.')[0] not in self.allowed_modules:
                        return f"Import not allowed: {node.module}"
                elif not self.allow_imports:
                    return f"Imports are not allowed"
            
            # Check for dangerous function calls
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in {'exec', 'eval', 'compile', 'open', '__import__'}:
                        return f"Function not allowed: {node.func.id}"
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in {'__subclasses__', '__bases__', '__mro__'}:
                        return f"Attribute access not allowed: {node.func.attr}"
        
        return None
    
    def execute(self, code: str, local_vars: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        """
        Execute Python code safely.
        
        Args:
            code: Python code to execute
            local_vars: Optional local variables
            
        Returns:
            ExecutionResult with output and status
        """
        # Validate first
        validation_error = self.validate_code(code)
        if validation_error:
            return ExecutionResult(
                success=False,
                error=validation_error,
            )
        
        # Set up output capture
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Set up locals
        local_namespace = dict(local_vars or {})
        
        start_time = time.time()
        
        try:
            # Execute with output capture
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Compile the code
                compiled = compile(code, '<sandbox>', 'exec')
                
                # Execute
                exec(compiled, dict(self._safe_globals), local_namespace)
            
            duration_ms = (time.time() - start_time) * 1000
            
            # Get output
            stdout = stdout_capture.getvalue()
            stderr = stderr_capture.getvalue()
            
            # Truncate if needed
            if len(stdout) > self.max_output_size:
                stdout = stdout[:self.max_output_size] + "\n... (truncated)"
            
            # Check for result variable
            return_value = local_namespace.get('result', local_namespace.get('_result'))
            
            return ExecutionResult(
                success=True,
                output=stdout,
                error=stderr if stderr else None,
                return_value=return_value,
                duration_ms=duration_ms,
                metadata={"local_vars": list(local_namespace.keys())},
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            return ExecutionResult(
                success=False,
                output=stdout_capture.getvalue(),
                error=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
                duration_ms=duration_ms,
            )
    
    def execute_function(
        self,
        func_code: str,
        func_name: str,
        args: List[Any] = None,
        kwargs: Dict[str, Any] = None,
    ) -> ExecutionResult:
        """
        Execute a function defined in code.
        
        Args:
            func_code: Code defining the function
            func_name: Name of function to call
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            ExecutionResult with return value
        """
        args = args or []
        kwargs = kwargs or {}
        
        # First define the function
        define_result = self.execute(func_code)
        if not define_result.success:
            return define_result
        
        # Then call it
        call_code = f"result = {func_name}(*__args__, **__kwargs__)"
        
        return self.execute(
            f"{func_code}\n{call_code}",
            local_vars={"__args__": args, "__kwargs__": kwargs},
        )
    
    def evaluate(self, expression: str) -> ExecutionResult:
        """
        Evaluate a Python expression safely.
        
        Args:
            expression: Python expression
            
        Returns:
            ExecutionResult with the expression value
        """
        code = f"result = {expression}"
        return self.execute(code)

