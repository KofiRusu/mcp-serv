"""
Agent Orchestrator for AGI Core

Coordinates multi-agent workflows for complex goals.
"""

import time
from typing import Any, Callable, Dict, List, Optional

from .base import BaseAgent, AgentContext, AgentResult
from .planner import PlannerAgent
from .worker import WorkerAgent
from .critic import CriticAgent
from ..tasks.models import Task, TaskStatus
from ..tasks.manager import TaskManager
from ..tools.base import ToolRegistry
from ..memory.manager import MemoryManager
from ..traces.recorder import TraceRecorder


class AgentOrchestrator:
    """
    Orchestrates multi-agent workflows.
    
    Coordinates Planner, Worker, and Critic agents to accomplish
    complex goals through planning, execution, and review cycles.
    """
    
    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        tool_registry: Optional[ToolRegistry] = None,
        memory_manager: Optional[MemoryManager] = None,
        task_manager: Optional[TaskManager] = None,
        trace_recorder: Optional[TraceRecorder] = None,
        max_iterations: int = 10,
        max_retries_per_task: int = 2,
    ):
        self.llm_provider = llm_provider
        self.tool_registry = tool_registry or ToolRegistry()
        self.memory_manager = memory_manager or MemoryManager()
        self.task_manager = task_manager or TaskManager()
        self.trace_recorder = trace_recorder or TraceRecorder()
        
        self.max_iterations = max_iterations
        self.max_retries_per_task = max_retries_per_task
        
        self.planner = PlannerAgent(llm_provider=llm_provider)
        self.worker = WorkerAgent(
            tool_registry=tool_registry,
            llm_provider=llm_provider,
        )
        self.critic = CriticAgent(llm_provider=llm_provider)
    
    async def execute_goal(
        self,
        goal: str,
        context: Optional[AgentContext] = None,
    ) -> AgentResult:
        """Execute a high-level goal using multi-agent collaboration."""
        session_id = self.trace_recorder.start_session(
            goal=goal,
            metadata={"type": "goal_execution"},
        )
        
        ctx = context or AgentContext()
        ctx.goal = goal
        ctx.available_tools = self.tool_registry.list_names()
        
        memories = self.memory_manager.recall(goal, k=5)
        ctx.memories = [m.content for m in memories]
        
        results = []
        completed_tasks = []
        failed_tasks = []
        
        try:
            self.trace_recorder.record_step(
                session_id, action="planning",
                input_data={"goal": goal},
            )
            
            plan_result = await self.planner.act(ctx)
            
            if not plan_result.success:
                self.trace_recorder.end_session(session_id, error=plan_result.error)
                return AgentResult(
                    success=False,
                    error=f"Planning failed: {plan_result.error}",
                    reasoning=plan_result.reasoning,
                )
            
            tasks = plan_result.output or []
            
            for iteration in range(self.max_iterations):
                if not tasks:
                    break
                
                task = tasks.pop(0)
                task_result = await self._execute_task(task, ctx, session_id)
                
                if task_result.success:
                    completed_tasks.append(task)
                    results.append(task_result.output)
                    self.memory_manager.remember(
                        f"Completed: {task.title} - {task_result.output}",
                        importance=0.6,
                        source="task_completion",
                    )
                else:
                    failed_tasks.append((task, task_result.error))
            
            final_result = await self._synthesize_results(
                goal, results, completed_tasks, failed_tasks, ctx,
            )
            
            self.trace_recorder.end_session(
                session_id,
                result=final_result.output if final_result.success else None,
                error=final_result.error,
            )
            
            return final_result
            
        except Exception as e:
            self.trace_recorder.end_session(session_id, error=str(e))
            return AgentResult(success=False, error=f"Orchestration failed: {str(e)}")
    
    async def _execute_task(
        self, task: Task, context: AgentContext, session_id: str,
    ) -> AgentResult:
        """Execute a single task with review."""
        start_time = time.time()
        
        task_ctx = AgentContext(
            goal=context.goal,
            task_description=f"{task.title}: {task.description}",
            memories=context.memories,
            available_tools=context.available_tools,
        )
        
        for attempt in range(self.max_retries_per_task + 1):
            result = await self.worker.act(task_ctx)
            
            if not result.success:
                continue
            
            review = await self.critic.review(result.output, task_ctx)
            
            if review.metadata.get("approved", True) or review.confidence > 0.7:
                result.confidence = review.confidence
                return result
            
            task_ctx.memories.extend(review.suggestions)
        
        return AgentResult(
            success=False,
            error=f"Task failed after {self.max_retries_per_task + 1} attempts",
        )
    
    async def _synthesize_results(
        self, goal: str, results: List[Any],
        completed_tasks: List[Task], failed_tasks: List[tuple],
        context: AgentContext,
    ) -> AgentResult:
        """Synthesize final result from task outputs."""
        if not results:
            return AgentResult(
                success=False, error="No tasks completed successfully",
                metadata={"failed_tasks": [{"title": t.title, "error": e} for t, e in failed_tasks]}
            )
        
        task_outputs = "\n".join([
            f"- {completed_tasks[i].title}: {results[i]}"
            for i in range(len(results))
        ])
        
        prompt = f"""Synthesizing results for goal: {goal}

Completed work:
{task_outputs}

Provide a cohesive summary and final answer."""
        
        if self.llm_provider:
            response = await self.llm_provider(prompt)
        else:
            response = f"Completed {len(results)} tasks:\n{task_outputs}"
        
        return AgentResult(
            success=True, output=response,
            actions_taken=[f"Completed: {t.title}" for t in completed_tasks],
            confidence=min(0.9, 0.5 + 0.1 * len(completed_tasks)),
            metadata={"completed_count": len(completed_tasks), "failed_count": len(failed_tasks)}
        )

