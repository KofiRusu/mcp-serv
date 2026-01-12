"""
Built-in Tools for AGI Core

Provides a set of commonly useful tools out of the box.
"""

import ast
import json
import operator
import os
import re
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Tool, ToolResult


# Safe operators for calculator
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def safe_eval_expr(expr: str) -> float:
    """
    Safely evaluate a mathematical expression.
    
    Only supports basic arithmetic operations.
    """
    def _eval(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Invalid constant: {node.value}")
        elif isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            op = SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = _eval(node.operand)
            op = SAFE_OPERATORS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(operand)
        elif isinstance(node, ast.Expression):
            return _eval(node.body)
        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")
    
    try:
        tree = ast.parse(expr, mode='eval')
        return _eval(tree)
    except (SyntaxError, ValueError) as e:
        raise ValueError(f"Invalid expression: {e}")


def calculator_tool(expression: str) -> float:
    """
    Perform safe mathematical calculations.
    
    Args:
        expression: Mathematical expression (e.g., "2 + 2", "10 * 5 / 2")
        
    Returns:
        The result of the calculation
    """
    return safe_eval_expr(expression)


def read_file_tool(path: str, max_lines: int = 500) -> str:
    """
    Read the contents of a file.
    
    Args:
        path: Path to the file
        max_lines: Maximum number of lines to read
        
    Returns:
        File contents as string
    """
    file_path = Path(path).expanduser()
    
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    if not file_path.is_file():
        raise ValueError(f"Not a file: {path}")
    
    # Read file with line limit
    lines = []
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                lines.append(f"... (truncated at {max_lines} lines)")
                break
            lines.append(line.rstrip())
    
    return "\n".join(lines)


def write_file_tool(path: str, content: str, create_dirs: bool = True) -> str:
    """
    Write content to a file.
    
    Args:
        path: Path to the file
        content: Content to write
        create_dirs: Whether to create parent directories
        
    Returns:
        Success message
    """
    file_path = Path(path).expanduser()
    
    # Safety check - don't write outside home directory
    home = Path.home()
    try:
        file_path.resolve().relative_to(home)
    except ValueError:
        raise ValueError(f"Cannot write outside home directory: {path}")
    
    if create_dirs:
        file_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_path.write_text(content, encoding='utf-8')
    
    return f"Successfully wrote {len(content)} characters to {path}"


def list_files_tool(path: str, pattern: str = "*") -> List[str]:
    """
    List files in a directory.
    
    Args:
        path: Directory path
        pattern: Glob pattern to filter files
        
    Returns:
        List of file paths
    """
    dir_path = Path(path).expanduser()
    
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    
    if not dir_path.is_dir():
        raise ValueError(f"Not a directory: {path}")
    
    files = []
    for file in dir_path.glob(pattern):
        files.append(str(file.relative_to(dir_path)))
    
    return sorted(files)


def search_text_tool(
    path: str,
    query: str,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search for text in files.
    
    Args:
        path: Directory or file path to search
        query: Text to search for
        max_results: Maximum number of results
        
    Returns:
        List of matches with file, line number, and content
    """
    search_path = Path(path).expanduser()
    results = []
    
    if search_path.is_file():
        files_to_search = [search_path]
    elif search_path.is_dir():
        files_to_search = list(search_path.rglob("*"))
    else:
        raise FileNotFoundError(f"Path not found: {path}")
    
    for file_path in files_to_search:
        if not file_path.is_file():
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line_num, line in enumerate(f, 1):
                    if query.lower() in line.lower():
                        results.append({
                            "file": str(file_path),
                            "line": line_num,
                            "content": line.strip()[:200],
                        })
                        
                        if len(results) >= max_results:
                            return results
        except Exception:
            continue
    
    return results


def http_get_tool(url: str, timeout: int = 10) -> str:
    """
    Make an HTTP GET request.
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        Response body as string
    """
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        raise ValueError("URL must start with http:// or https://")
    
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'ChatOS-AGI/1.0'}
    )
    
    with urllib.request.urlopen(req, timeout=timeout) as response:
        content = response.read().decode('utf-8', errors='ignore')
        
        # Truncate if too long
        if len(content) > 50000:
            content = content[:50000] + "\n... (truncated)"
        
        return content


def get_current_time_tool() -> str:
    """
    Get the current date and time.
    
    Returns:
        Current timestamp
    """
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def json_parse_tool(text: str) -> Any:
    """
    Parse a JSON string.
    
    Args:
        text: JSON string to parse
        
    Returns:
        Parsed JSON object
    """
    return json.loads(text)


def json_format_tool(data: Any, indent: int = 2) -> str:
    """
    Format data as JSON string.
    
    Args:
        data: Data to format
        indent: Indentation level
        
    Returns:
        Formatted JSON string
    """
    return json.dumps(data, indent=indent, ensure_ascii=False)


def shell_command_tool(command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Execute a shell command (with safety restrictions).
    
    Args:
        command: Command to execute
        timeout: Timeout in seconds
        
    Returns:
        Dict with stdout, stderr, and return code
    """
    import subprocess
    
    # Blocked dangerous commands
    dangerous_patterns = [
        r'\brm\s+-rf\b', r'\bsudo\b', r'\bchmod\b', r'\bchown\b',
        r'\bmkfs\b', r'\bdd\b', r'>\s*/dev/', r'\|.*sh\b',
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, command, re.IGNORECASE):
            raise ValueError(f"Blocked potentially dangerous command: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(Path.home()),
        )
        
        return {
            "stdout": result.stdout[:10000],
            "stderr": result.stderr[:1000],
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        raise TimeoutError(f"Command timed out after {timeout}s")


def get_builtin_tools() -> List[Tool]:
    """
    Get all built-in tools.
    
    Returns:
        List of Tool instances
    """
    return [
        Tool(
            name="calculator",
            description="Perform mathematical calculations. Supports +, -, *, /, //, %, **",
            function=calculator_tool,
            input_schema={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate",
                    }
                },
                "required": ["expression"],
            },
        ),
        Tool(
            name="read_file",
            description="Read the contents of a file",
            function=read_file_tool,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file",
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Maximum lines to read (default 500)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="write_file",
            description="Write content to a file",
            function=write_file_tool,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write",
                    },
                },
                "required": ["path", "content"],
            },
            requires_confirmation=True,
            is_dangerous=True,
        ),
        Tool(
            name="list_files",
            description="List files in a directory",
            function=list_files_tool,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path",
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (default '*')",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="search_text",
            description="Search for text in files",
            function=search_text_tool,
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory or file to search",
                    },
                    "query": {
                        "type": "string",
                        "description": "Text to search for",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results (default 10)",
                    },
                },
                "required": ["path", "query"],
            },
        ),
        Tool(
            name="http_get",
            description="Make an HTTP GET request to fetch a URL",
            function=http_get_tool,
            input_schema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default 10)",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="current_time",
            description="Get the current date and time",
            function=get_current_time_tool,
            input_schema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="json_parse",
            description="Parse a JSON string into an object",
            function=json_parse_tool,
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "JSON string to parse",
                    },
                },
                "required": ["text"],
            },
        ),
        Tool(
            name="json_format",
            description="Format data as a JSON string",
            function=json_format_tool,
            input_schema={
                "type": "object",
                "properties": {
                    "data": {
                        "description": "Data to format",
                    },
                    "indent": {
                        "type": "integer",
                        "description": "Indentation level (default 2)",
                    },
                },
                "required": ["data"],
            },
        ),
        Tool(
            name="shell",
            description="Execute a shell command (with safety restrictions)",
            function=shell_command_tool,
            input_schema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default 30)",
                    },
                },
                "required": ["command"],
            },
            requires_confirmation=True,
            is_dangerous=True,
        ),
    ]

