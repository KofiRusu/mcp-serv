"""
Tool Router for AGI Core

Automatically selects the best tool for a given query/task.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from .base import Tool, ToolRegistry, ToolResult


class ToolRouter:
    """
    Routes queries to the appropriate tool based on context.
    
    Uses pattern matching and keyword analysis to determine
    which tool is most appropriate for a given task.
    
    Usage:
        router = ToolRouter(registry)
        tool, args = router.select_tool("What is 2 + 2?")
        if tool:
            result = tool.execute(**args)
    """
    
    def __init__(self, registry: ToolRegistry):
        """
        Initialize the router.
        
        Args:
            registry: The tool registry to route to
        """
        self.registry = registry
        
        # Keyword patterns for tool selection
        self._patterns = {
            "calculator": [
                r'\b\d+\s*[\+\-\*\/\%\^]\s*\d+\b',  # Math expressions
                r'\bcalculate\b', r'\bcompute\b', r'\bmath\b',
                r'\bsum\b', r'\badd\b', r'\bsubtract\b', r'\bmultiply\b', r'\bdivide\b',
            ],
            "read_file": [
                r'\bread\s+(?:file|the\s+file)\b',
                r'\bshow\s+(?:me\s+)?(?:the\s+)?(?:file|contents)\b',
                r'\bopen\s+(?:file)?\b',
                r'\bcat\s+\S+',
                r'\bview\s+\S+',
            ],
            "write_file": [
                r'\bwrite\s+(?:to\s+)?(?:file|the\s+file)\b',
                r'\bsave\s+(?:to\s+)?(?:file)?\b',
                r'\bcreate\s+(?:a\s+)?file\b',
            ],
            "list_files": [
                r'\blist\s+(?:files|directory)\b',
                r'\bls\b', r'\bdir\b',
                r'\bshow\s+(?:me\s+)?(?:the\s+)?files\b',
            ],
            "search_text": [
                r'\bsearch\s+(?:for\s+)?(?:in\s+)?\b',
                r'\bfind\s+(?:text|string)\b',
                r'\bgrep\b',
            ],
            "http_get": [
                r'\bfetch\b', r'\bget\s+url\b',
                r'\bhttp\b', r'\bdownload\b',
                r'\bhttps?://\S+',
            ],
            "current_time": [
                r'\bwhat\s+time\b', r'\bcurrent\s+time\b',
                r'\bwhat\s+date\b', r'\btoday\b',
                r'\bnow\b',
            ],
            "shell": [
                r'\brun\s+command\b', r'\bexecute\s+command\b',
                r'\bshell\b', r'\bterminal\b', r'\bbash\b',
            ],
        }
    
    def select_tool(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Optional[Tool], Dict[str, Any]]:
        """
        Select the best tool for a query.
        
        Args:
            query: The user's query or task description
            context: Additional context for tool selection
            
        Returns:
            Tuple of (selected tool, extracted arguments) or (None, {})
        """
        query_lower = query.lower()
        
        # Score each tool based on pattern matches
        scores: Dict[str, int] = {}
        
        for tool_name, patterns in self._patterns.items():
            tool = self.registry.get(tool_name)
            if not tool:
                continue
            
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            
            if score > 0:
                scores[tool_name] = score
        
        if not scores:
            return None, {}
        
        # Select tool with highest score
        best_tool_name = max(scores, key=scores.get)
        best_tool = self.registry.get(best_tool_name)
        
        if best_tool:
            args = self._extract_arguments(best_tool, query, context)
            return best_tool, args
        
        return None, {}
    
    def _extract_arguments(
        self,
        tool: Tool,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Extract arguments from query for a specific tool.
        
        Args:
            tool: The tool to extract arguments for
            query: The user's query
            context: Additional context
            
        Returns:
            Dictionary of extracted arguments
        """
        args = {}
        
        # Tool-specific argument extraction
        if tool.name == "calculator":
            # Extract mathematical expression
            match = re.search(r'[\d\.\+\-\*\/\(\)\s\%\^]+', query)
            if match:
                expr = match.group().strip()
                # Clean up the expression
                expr = re.sub(r'\s+', '', expr)
                if expr:
                    args["expression"] = expr
        
        elif tool.name == "read_file":
            # Extract file path
            match = re.search(r'(?:file\s+)?([\/\w\.\-]+\.\w+)', query)
            if match:
                args["path"] = match.group(1)
        
        elif tool.name == "write_file":
            # Extract file path (content would come from context)
            match = re.search(r'(?:to\s+)?([\/\w\.\-]+\.\w+)', query)
            if match:
                args["path"] = match.group(1)
            if context and "content" in context:
                args["content"] = context["content"]
        
        elif tool.name == "list_files":
            # Extract directory path
            match = re.search(r'(?:in\s+)?([\/\w\.\-]+)', query)
            if match:
                args["path"] = match.group(1)
            else:
                args["path"] = "."
        
        elif tool.name == "search_text":
            # Extract search query and path
            match = re.search(r'(?:for\s+)?["\']?([^"\']+)["\']?\s+in\s+([\/\w\.\-]+)', query)
            if match:
                args["query"] = match.group(1).strip()
                args["path"] = match.group(2)
        
        elif tool.name == "http_get":
            # Extract URL
            match = re.search(r'(https?://\S+)', query)
            if match:
                args["url"] = match.group(1)
        
        elif tool.name == "shell":
            # Extract command (after "run" or "execute")
            match = re.search(r'(?:run|execute)\s+(.+)$', query, re.IGNORECASE)
            if match:
                args["command"] = match.group(1).strip()
        
        return args
    
    def suggest_tools(
        self,
        query: str,
        max_suggestions: int = 3,
    ) -> List[Tuple[Tool, float]]:
        """
        Suggest tools that might be relevant for a query.
        
        Args:
            query: The user's query
            max_suggestions: Maximum number of suggestions
            
        Returns:
            List of (tool, relevance_score) tuples
        """
        query_lower = query.lower()
        scored = []
        
        for tool_name, patterns in self._patterns.items():
            tool = self.registry.get(tool_name)
            if not tool:
                continue
            
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            
            # Also check tool description
            desc_lower = tool.description.lower()
            for word in query_lower.split():
                if len(word) > 3 and word in desc_lower:
                    score += 0.5
            
            if score > 0:
                scored.append((tool, score))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:max_suggestions]
    
    def execute_with_routing(
        self,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """
        Select and execute the appropriate tool for a query.
        
        Args:
            query: The user's query
            context: Additional context
            
        Returns:
            ToolResult from the executed tool
        """
        tool, args = self.select_tool(query, context)
        
        if not tool:
            return ToolResult(
                success=False,
                error="No suitable tool found for this query",
                metadata={"query": query},
            )
        
        if not args and tool.input_schema.get("required"):
            return ToolResult(
                success=False,
                error=f"Could not extract required arguments for {tool.name}",
                metadata={"tool": tool.name, "query": query},
            )
        
        return tool.execute(**args)

