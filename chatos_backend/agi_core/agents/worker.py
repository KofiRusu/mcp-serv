"""
Worker Agent for AGI Core

Executes tasks using available tools and generates outputs.
"""

import time
from typing import Any, Callable, Dict, List, Optional

from .base import BaseAgent, AgentContext, AgentResult
from ..tools.base import ToolRegistry, ToolResult
from ..tasks.models import Task


class WorkerAgent(BaseAgent):
    """
    Agent responsible for task execution.
    
    Takes individual tasks and executes them using available tools,
    generating concrete outputs.
    
    Usage:
        worker = WorkerAgent(
            tool_registry=my_registry,
            llm_provider=my_llm
        )
        context = AgentContext(task_description="Calculate 15% tip on $85")
        result = await worker.act(context)
    """
    
    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        llm_provider: Optional[Callable] = None,
        max_tool_calls: int = 5,
    ):
        super().__init__(
            name="Worker",
            role="worker",
            description="Executes tasks by using tools and generating appropriate outputs.",
            llm_provider=llm_provider,
        )
        
        self.tool_registry = tool_registry or ToolRegistry()
        self.max_tool_calls = max_tool_calls
    
    def get_system_prompt(self) -> str:
        tool_descriptions = self.tool_registry.get_tool_descriptions()
        
        return f"""You are a Worker Agent that executes tasks efficiently.

Your role is to:
1. Understand the task requirements
2. Use available tools when needed
3. Generate clear, accurate outputs
4. Report your actions and reasoning

{tool_descriptions}

When you need to use a tool, output:
TOOL: tool_name
ARGS: {{"param": "value"}}

After getting tool results or when you have the final answer, output:
RESULT: Your final output here

Always explain your reasoning briefly before taking action.
"""
    
    async def act(self, context: AgentContext) -> AgentResult:
        """
        Execute the task described in context.
        
        Args:
            context: Context containing the task to execute
            
        Returns:
            AgentResult with execution output
        """
        task_desc = context.task_description or context.goal
        
        if not task_desc:
            return AgentResult(
                success=False,
                error="No task provided for execution",
            )
        
        actions_taken = []
        tool_calls = []
        reasoning_parts = []
        current_context = task_desc
        
        # Execution loop
        for iteration in range(self.max_tool_calls + 1):
            prompt = self._build_execution_prompt(
                context,
                current_context,
                tool_calls,
            )
            
            try:
                response = await self.think(prompt)
                reasoning_parts.append(response)
                
                # Check for tool call
                tool_name, tool_args = self._parse_tool_call(response)
                
                if tool_name:
                    # Execute tool
                    result = self.tool_registry.execute(tool_name, **tool_args)
                    
                    tool_calls.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result.to_dict(),
                    })
                    
                    actions_taken.append(f"Called {tool_name}")
                    
                    # Add result to context for next iteration
                    current_context = f"{current_context}\n\nTool {tool_name} returned: {result.output if result.success else result.error}"
                    
                else:
                    # Check for final result
                    final_result = self._parse_final_result(response)
                    
                    if final_result:
                        return AgentResult(
                            success=True,
                            output=final_result,
                            reasoning="\n---\n".join(reasoning_parts),
                            actions_taken=actions_taken,
                            tool_calls=tool_calls,
                            confidence=0.8,
                        )
                    
                    # No tool call and no final result - use response as result
                    return AgentResult(
                        success=True,
                        output=response,
                        reasoning="\n---\n".join(reasoning_parts),
                        actions_taken=actions_taken,
                        tool_calls=tool_calls,
                        confidence=0.6,
                    )
                    
            except Exception as e:
                return AgentResult(
                    success=False,
                    error=f"Execution error: {str(e)}",
                    reasoning="\n---\n".join(reasoning_parts),
                    actions_taken=actions_taken,
                    tool_calls=tool_calls,
                )
        
        # Max iterations reached
        return AgentResult(
            success=False,
            error=f"Max tool calls ({self.max_tool_calls}) reached without completion",
            reasoning="\n---\n".join(reasoning_parts),
            actions_taken=actions_taken,
            tool_calls=tool_calls,
        )
    
    def _build_execution_prompt(
        self,
        context: AgentContext,
        current_context: str,
        previous_tool_calls: List[Dict],
    ) -> str:
        """Build prompt for execution."""
        parts = [self.get_system_prompt(), ""]
        
        # Add context
        parts.append(f"Task: {current_context}")
        
        if context.memories:
            parts.append("\nRelevant information:")
            for mem in context.memories[:3]:
                parts.append(f"- {mem}")
        
        if previous_tool_calls:
            parts.append("\nPrevious tool calls in this session:")
            for tc in previous_tool_calls[-3:]:
                parts.append(f"- {tc['tool']}: {tc['result'].get('output', tc['result'].get('error'))}")
        
        parts.append("\nProceed with the task. Use tools if needed, or provide the final result.")
        
        return "\n".join(parts)
    
    def _parse_tool_call(self, response: str) -> tuple:
        """Parse tool call from response."""
        import re
        import json
        
        # Look for TOOL: pattern
        tool_match = re.search(r'TOOL:\s*(\w+)', response, re.IGNORECASE)
        
        if not tool_match:
            return None, {}
        
        tool_name = tool_match.group(1)
        
        # Look for ARGS: pattern
        args_match = re.search(r'ARGS:\s*(\{[^}]+\})', response, re.IGNORECASE | re.DOTALL)
        
        args = {}
        if args_match:
            try:
                args = json.loads(args_match.group(1))
            except json.JSONDecodeError:
                pass
        
        return tool_name, args
    
    def _parse_final_result(self, response: str) -> Optional[str]:
        """Parse final result from response."""
        import re
        
        # Look for RESULT: pattern
        result_match = re.search(r'RESULT:\s*(.+)', response, re.IGNORECASE | re.DOTALL)
        
        if result_match:
            return result_match.group(1).strip()
        
        return None
    
    async def execute_task(
        self,
        task: Task,
        context: Optional[AgentContext] = None,
    ) -> AgentResult:
        """
        Execute a Task object.
        
        Args:
            task: The Task to execute
            context: Optional additional context
            
        Returns:
            AgentResult with execution output
        """
        ctx = context or AgentContext()
        ctx.task_description = f"{task.title}: {task.description}"
        ctx.goal = task.title
        
        # Add task metadata to context
        ctx.metadata["task_id"] = task.id
        ctx.metadata["task_priority"] = task.priority.value
        
        return await self.act(ctx)

