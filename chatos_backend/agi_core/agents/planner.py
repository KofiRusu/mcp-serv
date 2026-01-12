"""
Planner Agent for AGI Core

Decomposes goals into actionable tasks and plans execution strategies.
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional

from .base import BaseAgent, AgentContext, AgentResult
from ..tasks.models import Task, TaskPriority


class PlannerAgent(BaseAgent):
    """
    Agent responsible for planning and task decomposition.
    
    Takes high-level goals and breaks them down into concrete,
    actionable tasks with dependencies and priorities.
    
    Usage:
        planner = PlannerAgent(llm_provider=my_llm)
        context = AgentContext(goal="Write a research paper on AI safety")
        result = await planner.act(context)
        tasks = result.output  # List of Task objects
    """
    
    def __init__(self, llm_provider: Optional[Callable] = None):
        super().__init__(
            name="Planner",
            role="planner",
            description="Analyzes goals and creates actionable task plans with clear steps, dependencies, and priorities.",
            llm_provider=llm_provider,
        )
    
    def get_system_prompt(self) -> str:
        return """You are a Planning Agent specializing in task decomposition and strategy.

Your role is to:
1. Analyze complex goals and break them into concrete, actionable tasks
2. Identify dependencies between tasks
3. Assign priorities based on importance and urgency
4. Ensure plans are realistic and achievable

When creating a plan, output a JSON array of tasks with this structure:
{
    "tasks": [
        {
            "title": "Short task title",
            "description": "Detailed description of what needs to be done",
            "priority": "low|medium|high|critical",
            "dependencies": ["task_title_1", "task_title_2"],
            "estimated_duration": "15min|1hr|4hr|1day"
        }
    ],
    "reasoning": "Explanation of why this plan makes sense"
}

Keep tasks atomic and specific. Each task should be completable in a single work session.
"""
    
    async def act(self, context: AgentContext) -> AgentResult:
        """
        Create a plan from the goal in context.
        
        Args:
            context: Context containing the goal to plan for
            
        Returns:
            AgentResult with list of Task objects as output
        """
        goal = context.goal or context.task_description
        
        if not goal:
            return AgentResult(
                success=False,
                error="No goal provided for planning",
            )
        
        # Build prompt
        prompt = self._build_planning_prompt(context)
        
        # Get LLM response
        try:
            response = await self.think(prompt)
            tasks, reasoning = self._parse_plan_response(response)
            
            return AgentResult(
                success=True,
                output=tasks,
                reasoning=reasoning,
                confidence=0.8 if tasks else 0.3,
                metadata={
                    "task_count": len(tasks),
                    "goal": goal,
                }
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Planning failed: {str(e)}",
            )
    
    def _build_planning_prompt(self, context: AgentContext) -> str:
        """Build the prompt for planning."""
        parts = [
            self.get_system_prompt(),
            "",
            f"Goal to plan: {context.goal or context.task_description}",
        ]
        
        if context.memories:
            parts.append("\nRelevant context:")
            for mem in context.memories[:3]:
                parts.append(f"- {mem}")
        
        if context.available_tools:
            parts.append(f"\nAvailable tools: {', '.join(context.available_tools)}")
        
        parts.append("\nCreate a detailed plan to achieve this goal. Output valid JSON.")
        
        return "\n".join(parts)
    
    def _parse_plan_response(self, response: str) -> tuple:
        """
        Parse the LLM response into Task objects.
        
        Returns:
            Tuple of (list of Tasks, reasoning string)
        """
        tasks = []
        reasoning = ""
        
        # Try to extract JSON from response
        json_match = re.search(r'\{[\s\S]*\}', response)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                reasoning = data.get("reasoning", "")
                
                for task_data in data.get("tasks", []):
                    priority_str = task_data.get("priority", "medium").lower()
                    priority_map = {
                        "low": TaskPriority.LOW,
                        "medium": TaskPriority.MEDIUM,
                        "high": TaskPriority.HIGH,
                        "critical": TaskPriority.CRITICAL,
                    }
                    
                    task = Task(
                        title=task_data.get("title", "Unnamed task"),
                        description=task_data.get("description", ""),
                        priority=priority_map.get(priority_str, TaskPriority.MEDIUM),
                        tags=["planned", "auto-generated"],
                        metadata={
                            "estimated_duration": task_data.get("estimated_duration"),
                            "dependency_titles": task_data.get("dependencies", []),
                        }
                    )
                    tasks.append(task)
                    
            except json.JSONDecodeError:
                # Fall back to simple parsing
                tasks = self._simple_parse(response)
                reasoning = "Parsed from unstructured response"
        else:
            tasks = self._simple_parse(response)
            reasoning = "Parsed from unstructured response"
        
        return tasks, reasoning
    
    def _simple_parse(self, response: str) -> List[Task]:
        """Simple fallback parser for non-JSON responses."""
        tasks = []
        
        # Look for numbered lists
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            # Match patterns like "1. Do something" or "- Do something"
            match = re.match(r'^[\d\.\-\*]+\s*(.+)', line)
            if match and len(match.group(1)) > 5:
                task = Task(
                    title=match.group(1)[:100],
                    description=match.group(1),
                    priority=TaskPriority.MEDIUM,
                    tags=["planned", "auto-generated"],
                )
                tasks.append(task)
        
        return tasks
    
    async def refine_plan(
        self,
        tasks: List[Task],
        feedback: str,
        context: AgentContext,
    ) -> AgentResult:
        """
        Refine an existing plan based on feedback.
        
        Args:
            tasks: Current list of tasks
            feedback: Feedback to incorporate
            context: Execution context
            
        Returns:
            AgentResult with refined tasks
        """
        task_summary = "\n".join([f"- {t.title}: {t.description}" for t in tasks])
        
        prompt = f"""{self.get_system_prompt()}

Current plan:
{task_summary}

Feedback to incorporate:
{feedback}

Original goal: {context.goal}

Please refine the plan based on this feedback. Output valid JSON with the updated tasks.
"""
        
        try:
            response = await self.think(prompt)
            refined_tasks, reasoning = self._parse_plan_response(response)
            
            return AgentResult(
                success=True,
                output=refined_tasks,
                reasoning=f"Refined based on feedback: {reasoning}",
                confidence=0.7,
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Plan refinement failed: {str(e)}",
            )

