"""
commands.py - Command processor for special modes.

Parses user messages for /commands and routes to appropriate handlers.
Supported commands:
- /research - Deep research with web context
- /deepthinking - Chain-of-thought reflection
- /swarm - Multi-agent coding collaboration
- /code - Code-focused responses
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ChatOS.config import COMMAND_MODES


@dataclass
class ParsedCommand:
    """Represents a parsed command from user input."""
    
    command: Optional[str] = None
    query: str = ""
    args: Dict[str, str] = field(default_factory=dict)
    is_command: bool = False
    
    @property
    def mode_info(self) -> Optional[Dict[str, str]]:
        """Get mode information for the command."""
        if self.command and self.command in COMMAND_MODES:
            return COMMAND_MODES[self.command]
        return None


class CommandProcessor:
    """
    Processes user messages for /commands.
    
    Parses messages starting with / to extract commands and arguments.
    Routes to appropriate mode handlers.
    """
    
    # Regex patterns for command parsing
    COMMAND_PATTERN = re.compile(r'^/(\w+)\s*(.*)', re.DOTALL)
    ARG_PATTERN = re.compile(r'--(\w+)(?:=([^\s]+)|\s+([^\s-][^\s]*))?')
    
    def __init__(self):
        self.available_commands = list(COMMAND_MODES.keys())
    
    def parse(self, message: str) -> ParsedCommand:
        """
        Parse a message for commands.
        
        Args:
            message: The user's message
            
        Returns:
            ParsedCommand with extracted command and query
        """
        message = message.strip()
        
        # Check if message starts with /
        if not message.startswith('/'):
            return ParsedCommand(query=message, is_command=False)
        
        # Match command pattern
        match = self.COMMAND_PATTERN.match(message)
        if not match:
            return ParsedCommand(query=message, is_command=False)
        
        command = match.group(1).lower()
        rest = match.group(2).strip()
        
        # Check if it's a valid command
        if command not in self.available_commands:
            # Not a recognized command, treat as normal message
            return ParsedCommand(query=message, is_command=False)
        
        # Extract any arguments (--arg=value or --arg value)
        args = {}
        for arg_match in self.ARG_PATTERN.finditer(rest):
            arg_name = arg_match.group(1)
            arg_value = arg_match.group(2) or arg_match.group(3) or "true"
            args[arg_name] = arg_value
        
        # Remove arguments from query
        query = self.ARG_PATTERN.sub('', rest).strip()
        
        return ParsedCommand(
            command=command,
            query=query,
            args=args,
            is_command=True,
        )
    
    def get_help(self) -> str:
        """Get help text for all available commands."""
        lines = ["**Available Commands:**\n"]
        
        for cmd, info in COMMAND_MODES.items():
            lines.append(f"  `/{cmd}` - {info['icon']} {info['description']}")
        
        lines.append("\n**Examples:**")
        lines.append("  `/research What are the best practices for FastAPI?`")
        lines.append("  `/deepthinking Solve this optimization problem...`")
        lines.append("  `/swarm Build a REST API for user management`")
        lines.append("  `/code Write a binary search function`")
        
        return "\n".join(lines)
    
    def validate_command(self, parsed: ParsedCommand) -> Tuple[bool, Optional[str]]:
        """
        Validate a parsed command.
        
        Args:
            parsed: The parsed command
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not parsed.is_command:
            return True, None
        
        if not parsed.query:
            return False, f"Please provide a query after /{parsed.command}"
        
        return True, None


# Singleton instance
_processor: Optional[CommandProcessor] = None


def get_command_processor() -> CommandProcessor:
    """Get the singleton command processor instance."""
    global _processor
    if _processor is None:
        _processor = CommandProcessor()
    return _processor

