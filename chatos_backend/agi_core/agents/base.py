"""
Base Agent Classes for AGI Core

Provides foundational agent interface and context management.
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class AgentContext:
    """
    Context passed to agents during execution.
    
    Attributes:
        goal: The current goal or objective
        task_description: Specific task to accomplish
        conversation_history: Recent conversation for context
        memories: Relevant memories
        available_tools: List of tool names agent can use
        world_state: Current state information
        metadata: Additional context data
    """
    goal: str = ""
    task_description: str = ""
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    memories: List[str] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=list)
    world_state: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_prompt_context(self) -> str:
        """Format context for LLM prompt."""
        parts = []
        
        if self.goal:
            parts.append(f"Goal: {self.goal}")
        
        if self.task_description:
            parts.append(f"Current task: {self.task_description}")
        
        if self.memories:
            parts.append("Relevant memories:")
            for mem in self.memories[:5]:
                parts.append(f"  - {mem}")
        
        if self.available_tools:
            parts.append(f"Available tools: {', '.join(self.available_tools)}")
        
        if self.conversation_history:
            parts.append("Recent conversation:")
            for msg in self.conversation_history[-5:]:
                role = msg.get("role", "user")
                content = msg.get("content", "")[:200]
                parts.append(f"  {role}: {content}")
        
        return "\n".join(parts)


@dataclass
class AgentResult:
    """
    Result returned from agent execution.
    
    Attributes:
        success: Whether the agent succeeded
        output: Main output from the agent
        reasoning: The agent's reasoning/thought process
        actions_taken: List of actions performed
        tool_calls: Tools called during execution
        suggestions: Suggestions for next steps
        confidence: Confidence score (0-1)
        metadata: Additional result data
    """
    success: bool
    output: Any = None
    reasoning: str = ""
    actions_taken: List[str] = field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "reasoning": self.reasoning,
            "actions_taken": self.actions_taken,
            "tool_calls": self.tool_calls,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "error": self.error,
        }


class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    
    Agents are specialized components that perform specific roles
    in the AGI system (planning, execution, criticism, etc.).
    
    Usage:
        class MyAgent(BaseAgent):
            def __init__(self):
                super().__init__(
                    name="MyAgent",
                    role="custom",
                    description="Does custom things"
                )
            
            async def act(self, context: AgentContext) -> AgentResult:
                # Implementation
                return AgentResult(success=True, output="Done")
    """
    
    def __init__(
        self,
        name: str,
        role: str,
        description: str,
        llm_provider: Optional[Callable] = None,
    ):
        """
        Initialize the agent.
        
        Args:
            name: Agent name
            role: Agent role (planner, worker, critic, etc.)
            description: What this agent does
            llm_provider: Optional callable for LLM inference
        """
        self.id = f"agent_{uuid.uuid4().hex[:8]}"
        self.name = name
        self.role = role
        self.description = description
        self.llm_provider = llm_provider
    
    @abstractmethod
    async def act(self, context: AgentContext) -> AgentResult:
        """
        Perform the agent's action.
        
        Args:
            context: The execution context
            
        Returns:
            Result of the agent's action
        """
        pass
    
    async def think(self, prompt: str) -> str:
        """
        Use LLM to generate a response.
        
        Args:
            prompt: The prompt to send to the LLM
            
        Returns:
            LLM response
        """
        if self.llm_provider:
            return await self.llm_provider(prompt)
        
        # Fallback: return a placeholder
        return f"[{self.name}] Thinking about: {prompt[:100]}..."
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent."""
        return f"""You are {self.name}, a {self.role} agent.
{self.description}

Your responses should be focused, actionable, and well-reasoned.
When you don't know something, say so. When you're uncertain, express your confidence level.
"""
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', role='{self.role}')"


class AgentMessage:
    """
    Message passed between agents.
    
    Attributes:
        sender: Agent that sent the message
        recipient: Intended recipient agent
        content: Message content
        message_type: Type of message (request, response, notification)
        metadata: Additional message data
    """
    
    def __init__(
        self,
        sender: str,
        recipient: str,
        content: Any,
        message_type: str = "request",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = f"msg_{uuid.uuid4().hex[:8]}"
        self.sender = sender
        self.recipient = recipient
        self.content = content
        self.message_type = message_type
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata,
        }

