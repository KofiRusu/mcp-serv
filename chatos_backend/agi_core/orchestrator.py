"""
Autonomous Runner for AGI Core

Main execution loop for autonomous goal pursuit.
"""

import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .agents.base import AgentContext, AgentResult
from .agents.orchestrator import AgentOrchestrator
from .memory.manager import MemoryManager
from .tasks.manager import TaskManager
from .traces.recorder import TraceRecorder
from .reflection.engine import ReflectionEngine
from .tools.base import ToolRegistry
from .tools.builtin import get_builtin_tools


class RunnerStatus(Enum):
    """Status of the autonomous runner."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class AutonomousRunner:
    """
    Autonomous execution loop for AGI-style goal pursuit.
    
    Implements the Plan → Act → Reflect → Repeat cycle with
    safety limits and progress tracking.
    
    Usage:
        runner = AutonomousRunner(
            llm_provider=my_llm,
            goal="Research quantum computing and summarize findings"
        )
        result = await runner.run(max_steps=20)
    """
    
    def __init__(
        self,
        goal: str,
        llm_provider: Optional[Callable] = None,
        tool_registry: Optional[ToolRegistry] = None,
        memory_manager: Optional[MemoryManager] = None,
        max_steps: int = 20,
        reflect_every: int = 5,
        timeout_seconds: float = 300.0,
    ):
        """
        Initialize the autonomous runner.
        
        Args:
            goal: The goal to pursue
            llm_provider: Callable for LLM inference
            tool_registry: Available tools
            memory_manager: Memory system
            max_steps: Maximum execution steps
            reflect_every: Reflect after this many steps
            timeout_seconds: Overall timeout
        """
        self.goal = goal
        self.llm_provider = llm_provider
        self.max_steps = max_steps
        self.reflect_every = reflect_every
        self.timeout_seconds = timeout_seconds
        
        # Initialize tool registry with builtins
        self.tool_registry = tool_registry or ToolRegistry()
        if self.tool_registry.count() == 0:
            for tool in get_builtin_tools():
                self.tool_registry.register(tool)
        
        # Initialize components
        self.memory_manager = memory_manager or MemoryManager()
        self.task_manager = TaskManager()
        self.trace_recorder = TraceRecorder()
        self.reflection_engine = ReflectionEngine(llm_provider=llm_provider)
        
        self.orchestrator = AgentOrchestrator(
            llm_provider=llm_provider,
            tool_registry=self.tool_registry,
            memory_manager=self.memory_manager,
            task_manager=self.task_manager,
            trace_recorder=self.trace_recorder,
        )
        
        # State
        self.status = RunnerStatus.IDLE
        self.steps_taken = 0
        self.results: List[Any] = []
        self.reflections: List[str] = []
        self.start_time: Optional[float] = None
        self._stop_requested = False
    
    async def run(self, max_steps: Optional[int] = None) -> AgentResult:
        """
        Run the autonomous loop until goal is achieved or limits reached.
        
        Args:
            max_steps: Override default max steps
            
        Returns:
            Final AgentResult
        """
        max_steps = max_steps or self.max_steps
        self.start_time = time.time()
        self._stop_requested = False
        
        # Store goal in memory
        self.memory_manager.remember(
            f"Current goal: {self.goal}",
            importance=1.0,
            source="goal",
        )
        
        # Get recent lessons to inform execution
        recent_lessons = self.reflection_engine.get_recent_lessons(limit=5)
        
        context = AgentContext(
            goal=self.goal,
            available_tools=self.tool_registry.list_names(),
            memories=recent_lessons,
        )
        
        self.status = RunnerStatus.PLANNING
        
        try:
            # Main execution through orchestrator
            result = await self.orchestrator.execute_goal(self.goal, context)
            
            # Reflect on the session
            self.status = RunnerStatus.REFLECTING
            await self._final_reflection(result)
            
            self.status = RunnerStatus.COMPLETED if result.success else RunnerStatus.FAILED
            
            return result
            
        except TimeoutError:
            self.status = RunnerStatus.FAILED
            return AgentResult(
                success=False,
                error=f"Timeout after {self.timeout_seconds}s",
            )
        except Exception as e:
            self.status = RunnerStatus.FAILED
            return AgentResult(
                success=False,
                error=f"Execution error: {str(e)}",
            )
    
    async def _final_reflection(self, result: AgentResult) -> None:
        """Generate final reflection on the execution."""
        sessions = self.trace_recorder.list_sessions(limit=1)
        
        if sessions:
            session = self.trace_recorder.get_session(sessions[0]["session_id"])
            if session:
                reflection = await self.reflection_engine.reflect_on_session(session)
                self.reflections.append(reflection.summary())
                
                # Store lessons in memory
                for lesson in reflection.lessons_learned:
                    self.memory_manager.remember(
                        lesson,
                        importance=0.8,
                        source="reflection",
                    )
    
    def stop(self) -> None:
        """Request the runner to stop."""
        self._stop_requested = True
        self.status = RunnerStatus.STOPPED
    
    def get_progress(self) -> Dict[str, Any]:
        """Get current progress information."""
        elapsed = time.time() - self.start_time if self.start_time else 0
        
        return {
            "goal": self.goal,
            "status": self.status.value,
            "steps_taken": self.steps_taken,
            "max_steps": self.max_steps,
            "elapsed_seconds": elapsed,
            "timeout_seconds": self.timeout_seconds,
            "results_count": len(self.results),
            "reflections_count": len(self.reflections),
        }
    
    async def run_interactive(
        self,
        on_step: Optional[Callable[[Dict], None]] = None,
    ) -> AgentResult:
        """
        Run with step-by-step callbacks for interactive use.
        
        Args:
            on_step: Callback called after each step with progress dict
            
        Returns:
            Final AgentResult
        """
        result = await self.run()
        
        if on_step:
            on_step(self.get_progress())
        
        return result


# Convenience function for quick execution
async def run_goal(
    goal: str,
    llm_provider: Optional[Callable] = None,
    max_steps: int = 10,
) -> AgentResult:
    """
    Quick convenience function to run a goal.
    
    Args:
        goal: The goal to pursue
        llm_provider: Optional LLM provider
        max_steps: Maximum steps
        
    Returns:
        AgentResult
    """
    runner = AutonomousRunner(
        goal=goal,
        llm_provider=llm_provider,
        max_steps=max_steps,
    )
    return await runner.run()

