#!/usr/bin/env python3
"""
Cursor MCP Server - Implements proper MCP protocol for Cursor IDE
This server uses stdio-based JSON-RPC communication with Cursor.
"""

import sys
import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.agent_integration import get_memory
from mcp.path_sandbox import PathSandbox
from mcp import engineer_tools
from mcp.repo_memory import RepoMemory

# Setup logging (logs to stderr so stdout stays clean for MCP protocol)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class MCPServer:
    """MCP Protocol server for Cursor IDE with security hardening"""

    # Write operations that require MCP_WRITE_TOKEN
    WRITE_OPERATIONS = {"store_memory", "memory_append", "decision_log_add"}

    def __init__(self):
        self.memory = get_memory()
        self.request_id = 0

        # Repo memory system
        context_dir = Path(__file__).parent.parent / "context"
        self.repo_memory = RepoMemory(
            memory_file=str(context_dir / "MEMORY.md"),
            decision_file=str(context_dir / "DECISIONS.md")
        )

        # Security: Write token from environment
        self.write_token = os.environ.get("MCP_WRITE_TOKEN")

        # Security: Dry-run mode
        self.dry_run = os.environ.get("MCP_DRY_RUN", "false").lower() == "true"

        # Security: Path sandbox (use current working directory as root)
        self.sandbox = PathSandbox(str(Path.cwd()))

        # Log security status
        if self.write_token:
            logger.info("MCP Server initialized with write protection enabled")
        else:
            logger.info("MCP Server initialized in READ-ONLY mode (no MCP_WRITE_TOKEN set)")

        if self.dry_run:
            logger.info("DRY-RUN mode enabled - write operations will be logged only")

        # Canonical tool registry (kept in sync with tools/list)
        self._tools_list = self._build_tools()
        self.tools = {tool["name"]: tool for tool in self._tools_list}
    
    def is_write_allowed(self, provided_token: Optional[str]) -> bool:
        """
        Check if write operation is allowed.

        Args:
            provided_token: The token provided by the client

        Returns:
            True if write is allowed, False otherwise
        """
        # Dry-run mode always denies writes
        if self.dry_run:
            return False

        # No token configured = no writes allowed (read-only default)
        if self.write_token is None:
            return False

        # No token provided = denied
        if provided_token is None:
            return False

        # Token must match exactly
        return self.write_token == provided_token

    def handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        logger.debug("Initialize request received")
        logger.info("✅ Client initialized successfully")
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "logging": {},
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "subscribe": True,
                    "listChanged": True
                }
            },
            "serverInfo": {
                "name": "cursor-mcp",
                "version": "1.0.0"
            }
        }
    
    def _build_tools(self) -> list:
        """Build canonical tools list used by tools/list and introspection"""
        return [
            {
                "name": "store_memory",
                "description": "Store a memory in the MCP system (requires write_token)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "domain": {"type": "string", "description": "Memory domain"},
                        "content": {"type": "string", "description": "Memory content"},
                        "title": {"type": "string", "description": "Memory title"},
                        "tags": {"type": "array", "items": {"type": "string"}},
                        "write_token": {"type": "string", "description": "Write authorization token (set MCP_WRITE_TOKEN env var)"}
                    },
                    "required": ["domain", "content"]
                }
            },
            {
                "name": "search_memory",
                "description": "Search memories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Max results"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_context",
                "description": "Get contextual memories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workspace": {"type": "string"},
                        "max_memories": {"type": "integer"}
                    }
                }
            },
            {
                "name": "get_stats",
                "description": "Get MCP system statistics",
                "inputSchema": {"type": "object", "properties": {}}
            },
            {
                "name": "git_status",
                "description": "Get git repository status",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cwd": {"type": "string", "description": "Working directory"}
                    },
                    "required": ["cwd"]
                }
            },
            {
                "name": "git_diff",
                "description": "Get git diff between commits or working tree",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cwd": {"type": "string", "description": "Working directory"},
                        "ref": {"type": "string", "description": "Git reference (default: HEAD)"}
                    },
                    "required": ["cwd"]
                }
            },
            {
                "name": "git_show",
                "description": "Show git commit details",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cwd": {"type": "string", "description": "Working directory"},
                        "ref": {"type": "string", "description": "Git reference (default: HEAD)"}
                    },
                    "required": ["cwd"]
                }
            },
            {
                "name": "ripgrep_search",
                "description": "Search files using ripgrep (with Python fallback)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search pattern"},
                        "path": {"type": "string", "description": "Directory to search (default: current)"},
                        "glob": {"type": "string", "description": "File pattern (default: *)"},
                        "context_lines": {"type": "integer", "description": "Context lines (default: 2)"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "run_cmd",
                "description": "Run an allowed command (strict allowlist)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "cmd": {"type": "array", "items": {"type": "string"}, "description": "Command as array (e.g., [\"git\", \"status\"])"},
                        "cwd": {"type": "string", "description": "Working directory"},
                        "timeout_sec": {"type": "integer", "description": "Timeout in seconds (default: 60)"}
                    },
                    "required": ["cmd", "cwd"]
                }
            },
            {
                "name": "memory_append",
                "description": "Append to project MEMORY.md (requires write_token)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string", "description": "Memory content"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
                        "write_token": {"type": "string", "description": "Write authorization token (set MCP_WRITE_TOKEN env var)"}
                    },
                    "required": ["content"]
                }
            },
            {
                "name": "memory_search",
                "description": "Search project MEMORY.md",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "decision_log_add",
                "description": "Add entry to decision log (requires write_token)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "decision": {"type": "string", "description": "The decision made"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "List of tags for categorization"},
                        "context": {"type": "string", "description": "Additional context about the decision"},
                        "write_token": {"type": "string", "description": "Write authorization token (set MCP_WRITE_TOKEN env var)"}
                    },
                    "required": ["decision"]
                }
            },
            {
                "name": "decision_log_search",
                "description": "Search decision log",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            }
        ]

    def handle_tools_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available tools"""
        return {
            "tools": self._tools_list
        }
    
    def handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool calls with security checks"""
        tool_name = params.get("name")
        tool_input = params.get("arguments", {})

        logger.debug(f"Tool call: {tool_name} with {tool_input}")

        # Security: Check write permission for write operations
        if tool_name in self.WRITE_OPERATIONS:
            provided_token = tool_input.get("write_token")

            # Check if write is allowed
            if not self.is_write_allowed(provided_token):
                # Build helpful error message
                if self.dry_run:
                    msg = "[DRY-RUN] Write operation not executed. Set MCP_DRY_RUN=false to enable writes."
                elif self.write_token is None:
                    msg = "Write operation denied: MCP_WRITE_TOKEN not set. Server is in READ-ONLY mode."
                elif provided_token is None:
                    msg = "Write operation denied: Missing write_token parameter."
                else:
                    msg = "Write operation denied: Invalid write_token."

                logger.warning(f"Write denied for {tool_name}: {msg}")
                return {
                    "content": [
                        {"type": "text", "text": msg}
                    ],
                    "isError": True
                }

            # Log successful write authorization
            logger.info(f"Write authorized for {tool_name}")

        try:
            if tool_name == "store_memory":
                # In dry-run mode, log but don't execute
                if self.dry_run:
                    domain = tool_input.get("domain", "Project Knowledge")
                    content = tool_input.get("content", "")
                    logger.info(f"[DRY-RUN] Would store memory: domain={domain}, content_length={len(content)}")
                    return {
                        "content": [
                            {"type": "text", "text": "[DRY-RUN] Memory would be stored (not executed)"}
                        ]
                    }

                memory_id = self.memory.store(
                    domain=tool_input.get("domain", "Project Knowledge"),
                    content=tool_input.get("content", ""),
                    title=tool_input.get("title"),
                    tags=tool_input.get("tags", [])
                )
                return {
                    "content": [
                        {"type": "text", "text": f"Memory stored: {memory_id}"}
                    ]
                }
            
            elif tool_name == "search_memory":
                results = self.memory.search(
                    query=tool_input.get("query", ""),
                    limit=tool_input.get("limit", 10)
                )
                text = json.dumps(results, indent=2)
                return {
                    "content": [
                        {"type": "text", "text": f"Search results:\n{text}"}
                    ]
                }
            
            elif tool_name == "get_context":
                results = self.memory.get_context(
                    workspace=tool_input.get("workspace"),
                    max_memories=tool_input.get("max_memories", 20)
                )
                text = json.dumps(results, indent=2)
                return {
                    "content": [
                        {"type": "text", "text": f"Context:\n{text}"}
                    ]
                }
            
            elif tool_name == "get_stats":
                stat = self.memory.stats()
                text = json.dumps(stat, indent=2)
                return {
                    "content": [
                        {"type": "text", "text": f"Statistics:\n{text}"}
                    ]
                }

            elif tool_name == "git_status":
                cwd = tool_input.get("cwd", str(Path.cwd()))
                result = engineer_tools.git_status(cwd)
                text = json.dumps(result, indent=2)
                return {
                    "content": [
                        {"type": "text", "text": f"Git status:\n{text}"}
                    ]
                }

            elif tool_name == "git_diff":
                cwd = tool_input.get("cwd", str(Path.cwd()))
                ref = tool_input.get("ref", "HEAD")
                result = engineer_tools.git_diff(cwd, ref)
                text = json.dumps(result, indent=2)
                return {
                    "content": [
                        {"type": "text", "text": f"Git diff:\n{text}"}
                    ]
                }

            elif tool_name == "git_show":
                cwd = tool_input.get("cwd", str(Path.cwd()))
                ref = tool_input.get("ref", "HEAD")
                result = engineer_tools.git_show(cwd, ref)
                text = json.dumps(result, indent=2)
                return {
                    "content": [
                        {"type": "text", "text": f"Git show:\n{text}"}
                    ]
                }

            elif tool_name == "ripgrep_search":
                query = tool_input.get("query", "")
                path = tool_input.get("path", ".")
                glob = tool_input.get("glob", "*")
                context_lines = tool_input.get("context_lines", 2)
                result = engineer_tools.ripgrep_search(query, path, glob, context_lines)
                text = json.dumps(result, indent=2)
                return {
                    "content": [
                        {"type": "text", "text": f"Ripgrep results:\n{text}"}
                    ]
                }

            elif tool_name == "run_cmd":
                cmd = tool_input.get("cmd", [])
                cwd = tool_input.get("cwd", str(Path.cwd()))
                timeout_sec = tool_input.get("timeout_sec", 60)
                result = engineer_tools.run_cmd(cmd, cwd, self.sandbox, timeout_sec)
                text = json.dumps(result, indent=2)

                # Check if command was rejected (returncode -1 indicates allowlist/sandbox rejection)
                if result.get("returncode") == -1:
                    return {
                        "content": [
                            {"type": "text", "text": f"Command result:\n{text}"}
                        ],
                        "isError": True
                    }

                return {
                    "content": [
                        {"type": "text", "text": f"Command result:\n{text}"}
                    ]
                }

            elif tool_name == "memory_append":
                provided_token = tool_input.get("write_token")

                # Check if write is allowed
                if not self.is_write_allowed(provided_token):
                    if self.dry_run:
                        msg = "[DRY-RUN] Memory append not executed. Set MCP_DRY_RUN=false to enable writes."
                    elif self.write_token is None:
                        msg = "Write operation denied: MCP_WRITE_TOKEN not set. Server is in READ-ONLY mode."
                    elif provided_token is None:
                        msg = "Write operation denied: Missing write_token parameter."
                    else:
                        msg = "Write operation denied: Invalid write_token."

                    logger.warning(f"Write denied for {tool_name}: {msg}")
                    return {
                        "content": [
                            {"type": "text", "text": msg}
                        ],
                        "isError": True
                    }

                # In dry-run mode, log but don't execute
                if self.dry_run:
                    content = tool_input.get("content", "")
                    tags = tool_input.get("tags", [])
                    logger.info(f"[DRY-RUN] Would append memory: content_length={len(content)}, tags={tags}")
                    return {
                        "content": [
                            {"type": "text", "text": "[DRY-RUN] Memory would be appended (not executed)"}
                        ]
                    }

                timestamp = self.repo_memory.append_memory(
                    content=tool_input.get("content", ""),
                    tags=tool_input.get("tags")
                )
                return {
                    "content": [
                        {"type": "text", "text": f"Memory appended: {timestamp}"}
                    ]
                }

            elif tool_name == "memory_search":
                query = tool_input.get("query", "")
                results = self.repo_memory.search_memory(query)
                text = "\n\n".join(results) if results else "No results found"
                return {
                    "content": [
                        {"type": "text", "text": f"Memory search results:\n{text}"}
                    ]
                }

            elif tool_name == "decision_log_add":
                provided_token = tool_input.get("write_token")

                # Check if write is allowed
                if not self.is_write_allowed(provided_token):
                    if self.dry_run:
                        msg = "[DRY-RUN] Decision log not executed. Set MCP_DRY_RUN=false to enable writes."
                    elif self.write_token is None:
                        msg = "Write operation denied: MCP_WRITE_TOKEN not set. Server is in READ-ONLY mode."
                    elif provided_token is None:
                        msg = "Write operation denied: Missing write_token parameter."
                    else:
                        msg = "Write operation denied: Invalid write_token."

                    logger.warning(f"Write denied for {tool_name}: {msg}")
                    return {
                        "content": [
                            {"type": "text", "text": msg}
                        ],
                        "isError": True
                    }

                # In dry-run mode, log but don't execute
                if self.dry_run:
                    decision = tool_input.get("decision", "")
                    tags = tool_input.get("tags", [])
                    context = tool_input.get("context", "")
                    logger.info(f"[DRY-RUN] Would add decision: {decision}, tags={tags}, context={context}")
                    return {
                        "content": [
                            {"type": "text", "text": "[DRY-RUN] Decision would be logged (not executed)"}
                        ]
                    }

                timestamp = self.repo_memory.add_decision(
                    decision=tool_input.get("decision", ""),
                    tags=tool_input.get("tags", []),
                    context=tool_input.get("context", "")
                )
                return {
                    "content": [
                        {"type": "text", "text": f"Decision logged: {timestamp}"}
                    ]
                }

            elif tool_name == "decision_log_search":
                query = tool_input.get("query", "")
                results = self.repo_memory.search_decisions(query)
                text = "\n\n".join(results) if results else "No results found"
                return {
                    "content": [
                        {"type": "text", "text": f"Decision log results:\n{text}"}
                    ]
                }

            else:
                return {
                    "content": [
                        {"type": "text", "text": f"Unknown tool: {tool_name}"}
                    ]
                }
        
        except Exception as e:
            logger.error(f"Tool error: {e}", exc_info=True)
            return {
                "content": [
                    {"type": "text", "text": f"Error: {str(e)}"}
                ],
                "isError": True
            }
    
    def handle_resources_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available resources"""
        stats = self.memory.stats()
        return {
            "resources": [
                {
                    "uri": "mcp://cursor-mcp/stats",
                    "name": "MCP Statistics",
                    "description": f"Current system stats: {stats['total']} memories",
                    "mimeType": "application/json"
                }
            ]
        }
    
    def handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a resource"""
        uri = params.get("uri", "")
        
        if uri == "mcp://cursor-mcp/stats":
            stats = self.memory.stats()
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(stats, indent=2)
                    }
                ]
            }
        
        return {"contents": []}
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming MCP request"""
        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")
        
        logger.debug(f"Request: {method} (id: {request_id})")
        
        # Handle notifications (no id means notification, no response needed)
        if request_id is None:
            if method == "notifications/initialized":
                logger.debug("Client initialized notification received")
                return None  # Don't send response for notifications
            elif method.startswith("notifications/"):
                logger.debug(f"Notification: {method}")
                return None
        
        try:
            if method == "initialize":
                result = self.handle_initialize(params)
            elif method == "tools/list":
                result = self.handle_tools_list(params)
            elif method == "tools/call":
                result = self.handle_call_tool(params)
            elif method == "resources/list":
                result = self.handle_resources_list(params)
            elif method == "resources/read":
                result = self.handle_resources_read(params)
            else:
                # Unknown method
                logger.warning(f"Unknown method: {method}")
                result = {"error": f"Unknown method: {method}"}
            
            # Only send response if there's an id (not a notification)
            if request_id is not None:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
                return response
            else:
                return None
        
        except Exception as e:
            logger.error(f"Error processing request: {e}", exc_info=True)
            # Only send error response if there's an id
            if request_id is not None:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": str(e)
                    }
                }
                return response
            else:
                return None


def main():
    """Main entry point"""
    logger.info("Starting Cursor MCP Server")
    
    try:
        server = MCPServer()
        logger.info("Server ready, listening on stdio")
        
        # Read and process requests from stdin
        while True:
            try:
                line = sys.stdin.readline()
                if not line:
                    logger.info("EOF received, shutting down")
                    break
                
                # Parse JSON request
                request = json.loads(line.strip())
                
                # Process request
                response = server.process_request(request)
                
                # Send response on stdout only if not None (notifications have no response)
                if response is not None:
                    print(json.dumps(response))
                    sys.stdout.flush()
            
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON: {e}")
                continue
            except KeyboardInterrupt:
                logger.info("Interrupted, shutting down")
                break
            except Exception as e:
                logger.error(f"Error: {e}", exc_info=True)
                continue
    
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
