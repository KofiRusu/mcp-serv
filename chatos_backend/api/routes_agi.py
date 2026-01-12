"""
AGI Core API Routes for ChatOS

Exposes AGI features through REST endpoints.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from chatos_backend.agi_core import (
    MemoryManager,
    TaskManager,
    GoalManager,
    ToolRegistry,
    RAGStore,
    TraceRecorder,
    get_builtin_tools,
    Task, TaskPriority, TaskStatus,
    Goal, GoalStatus,
)
from chatos_backend.agi_core.sandbox import get_sandbox_logger, SandboxOperation

router = APIRouter(prefix="/api/agi", tags=["AGI Core"])

# Singletons
_memory_manager: Optional[MemoryManager] = None
_task_manager: Optional[TaskManager] = None
_goal_manager: Optional[GoalManager] = None
_tool_registry: Optional[ToolRegistry] = None
_rag_store: Optional[RAGStore] = None
_trace_recorder: Optional[TraceRecorder] = None


def get_agi_memory_manager() -> MemoryManager:
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(session_id="chatos_main")
    return _memory_manager


def get_agi_task_manager() -> TaskManager:
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager()
    return _task_manager


def get_agi_goal_manager() -> GoalManager:
    global _goal_manager
    if _goal_manager is None:
        _goal_manager = GoalManager()
    return _goal_manager


def get_agi_tool_registry() -> ToolRegistry:
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        for tool in get_builtin_tools():
            _tool_registry.register(tool)
    return _tool_registry


def get_agi_rag_store() -> RAGStore:
    global _rag_store
    if _rag_store is None:
        _rag_store = RAGStore()
    return _rag_store


def get_agi_trace_recorder() -> TraceRecorder:
    global _trace_recorder
    if _trace_recorder is None:
        _trace_recorder = TraceRecorder()
    return _trace_recorder


# =============================================================================
# Request/Response Models
# =============================================================================

class MemoryRequest(BaseModel):
    content: str
    importance: float = 0.5
    source: str = "user"


class RecallRequest(BaseModel):
    query: str
    k: int = 5


class TaskRequest(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"


class GoalRequest(BaseModel):
    description: str
    priority: int = 5


class ToolExecuteRequest(BaseModel):
    tool_name: str
    args: Dict[str, Any] = {}


class KnowledgeQueryRequest(BaseModel):
    query: str
    k: int = 5


class IndexDirectoryRequest(BaseModel):
    path: str
    patterns: List[str] = None


# =============================================================================
# Memory Endpoints
# =============================================================================

@router.get("/memory/stats")
async def get_memory_stats():
    """Get AGI memory statistics."""
    mm = get_agi_memory_manager()
    return mm.get_stats()


@router.post("/memory/remember")
async def remember(request: MemoryRequest):
    """Store a memory."""
    mm = get_agi_memory_manager()
    memory_id = mm.remember(
        request.content,
        importance=request.importance,
        source=request.source,
    )
    return {"success": True, "memory_id": memory_id}


@router.post("/memory/recall")
async def recall(request: RecallRequest):
    """Recall relevant memories."""
    mm = get_agi_memory_manager()
    results = mm.recall(request.query, k=request.k)
    return {
        "results": [
            {
                "id": m.id,
                "content": m.content,
                "importance": m.importance,
                "source": m.source,
            }
            for m in results
        ]
    }


@router.get("/memory/context")
async def get_context(query: str = ""):
    """Get relevant context for a query."""
    mm = get_agi_memory_manager()
    context = mm.get_relevant_context(query or "general")
    return {"context": context}


@router.delete("/memory/{memory_id}")
async def forget(memory_id: str):
    """Delete a memory."""
    mm = get_agi_memory_manager()
    if mm.forget(memory_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Memory not found")


@router.post("/memory/conversation")
async def add_conversation(user_message: str, assistant_message: str):
    """Add a conversation turn to memory."""
    mm = get_agi_memory_manager()
    mm.add_turn(user_message, assistant_message)
    return {"success": True}


# =============================================================================
# Task Endpoints
# =============================================================================

@router.get("/tasks")
async def list_agi_tasks(status: str = None):
    """List all AGI tasks."""
    tm = get_agi_task_manager()
    status_filter = TaskStatus(status) if status else None
    tasks = tm.list_tasks(status=status_filter)
    return {
        "tasks": [t.to_dict() for t in tasks],
        "stats": tm.get_stats(),
    }


@router.get("/tasks/ready")
async def get_ready_tasks():
    """Get tasks ready to execute."""
    tm = get_agi_task_manager()
    tasks = tm.get_ready_tasks()
    return {"tasks": [t.to_dict() for t in tasks]}


@router.post("/tasks")
async def create_agi_task(request: TaskRequest):
    """Create a new task."""
    tm = get_agi_task_manager()
    priority_map = {
        "low": TaskPriority.LOW,
        "medium": TaskPriority.MEDIUM,
        "high": TaskPriority.HIGH,
        "critical": TaskPriority.CRITICAL,
    }
    task = tm.create_task(
        title=request.title,
        description=request.description,
        priority=priority_map.get(request.priority.lower(), TaskPriority.MEDIUM),
    )
    return {"success": True, "task": task.to_dict()}


@router.get("/tasks/{task_id}")
async def get_agi_task(task_id: str):
    """Get a specific task."""
    tm = get_agi_task_manager()
    task = tm.get_task(task_id)
    if task:
        return {"task": task.to_dict()}
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/{task_id}/start")
async def start_agi_task(task_id: str):
    """Start a task."""
    tm = get_agi_task_manager()
    task = tm.start_task(task_id)
    if task:
        return {"success": True, "task": task.to_dict()}
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/{task_id}/complete")
async def complete_agi_task(task_id: str, result: str = None):
    """Complete a task."""
    tm = get_agi_task_manager()
    task = tm.complete_task(task_id, result=result)
    if task:
        return {"success": True, "task": task.to_dict()}
    raise HTTPException(status_code=404, detail="Task not found")


@router.post("/tasks/{task_id}/fail")
async def fail_agi_task(task_id: str, error: str = ""):
    """Mark a task as failed."""
    tm = get_agi_task_manager()
    task = tm.fail_task(task_id, error)
    if task:
        return {"success": True, "task": task.to_dict()}
    raise HTTPException(status_code=404, detail="Task not found")


@router.delete("/tasks/{task_id}")
async def delete_agi_task(task_id: str):
    """Delete a task."""
    tm = get_agi_task_manager()
    if tm.delete_task(task_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Task not found")


# =============================================================================
# Goal Endpoints
# =============================================================================

@router.get("/goals")
async def list_goals(status: str = None):
    """List all goals."""
    gm = get_agi_goal_manager()
    status_filter = GoalStatus(status) if status else None
    goals = gm.list_goals(status=status_filter)
    return {
        "goals": [g.to_dict() for g in goals],
        "stats": gm.get_stats(),
    }


@router.get("/goals/active")
async def get_active_goals():
    """Get active goals."""
    gm = get_agi_goal_manager()
    goals = gm.get_active_goals()
    return {"goals": [g.to_dict() for g in goals]}


@router.post("/goals")
async def create_goal(request: GoalRequest):
    """Create a new goal."""
    gm = get_agi_goal_manager()
    goal = gm.create_goal(
        description=request.description,
        priority=request.priority,
    )
    return {"success": True, "goal": goal.to_dict()}


@router.get("/goals/{goal_id}")
async def get_goal(goal_id: str):
    """Get a specific goal."""
    gm = get_agi_goal_manager()
    goal = gm.get_goal(goal_id)
    if goal:
        return {"goal": goal.to_dict()}
    raise HTTPException(status_code=404, detail="Goal not found")


@router.post("/goals/{goal_id}/progress")
async def update_goal_progress(goal_id: str, progress: float):
    """Update goal progress."""
    gm = get_agi_goal_manager()
    goal = gm.update_progress(goal_id, progress)
    if goal:
        return {"success": True, "goal": goal.to_dict()}
    raise HTTPException(status_code=404, detail="Goal not found")


@router.post("/goals/{goal_id}/complete")
async def complete_goal(goal_id: str):
    """Mark goal as complete."""
    gm = get_agi_goal_manager()
    goal = gm.complete_goal(goal_id)
    if goal:
        return {"success": True, "goal": goal.to_dict()}
    raise HTTPException(status_code=404, detail="Goal not found")


@router.post("/goals/{goal_id}/pause")
async def pause_goal(goal_id: str):
    """Pause a goal."""
    gm = get_agi_goal_manager()
    goal = gm.pause_goal(goal_id)
    if goal:
        return {"success": True, "goal": goal.to_dict()}
    raise HTTPException(status_code=404, detail="Goal not found")


@router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str):
    """Delete a goal."""
    gm = get_agi_goal_manager()
    if gm.delete_goal(goal_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Goal not found")


# =============================================================================
# Tool Endpoints
# =============================================================================

@router.get("/tools")
async def list_tools():
    """List available tools."""
    registry = get_agi_tool_registry()
    return {
        "tools": [
            {
                "name": t.name,
                "description": t.description,
                "is_dangerous": t.is_dangerous,
                "requires_confirmation": t.requires_confirmation,
            }
            for t in registry.list()
        ],
        "count": registry.count(),
    }


@router.post("/tools/execute")
async def execute_tool(request: ToolExecuteRequest):
    """Execute a tool."""
    registry = get_agi_tool_registry()
    
    tool = registry.get(request.tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool not found: {request.tool_name}")
    
    if tool.is_dangerous:
        # For dangerous tools, require explicit confirmation
        if not request.args.get("_confirmed"):
            return {
                "success": False,
                "requires_confirmation": True,
                "message": f"Tool '{request.tool_name}' is dangerous. Add '_confirmed': true to args to proceed.",
            }
    
    result = tool.execute(**{k: v for k, v in request.args.items() if not k.startswith("_")})
    return result.to_dict()


# =============================================================================
# Knowledge Endpoints
# =============================================================================

@router.post("/knowledge/query")
async def query_knowledge(request: KnowledgeQueryRequest):
    """Query the knowledge base."""
    store = get_agi_rag_store()
    results = store.query(request.query, k=request.k)
    return {"results": results, "count": len(results)}


@router.get("/knowledge/documents")
async def list_documents():
    """List indexed documents."""
    store = get_agi_rag_store()
    return {
        "documents": store.list_documents(),
        "count": store.count(),
    }


@router.post("/knowledge/index")
async def index_directory(request: IndexDirectoryRequest):
    """Index a directory for RAG."""
    store = get_agi_rag_store()
    try:
        count = store.index_directory(request.path, request.patterns)
        return {"success": True, "indexed_count": count}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/knowledge/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document from the knowledge base."""
    store = get_agi_rag_store()
    if store.delete_document(doc_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Document not found")


# =============================================================================
# Traces Endpoints
# =============================================================================

@router.get("/traces")
async def list_traces(limit: int = 20, status: str = None):
    """List recent execution traces."""
    recorder = get_agi_trace_recorder()
    sessions = recorder.list_sessions(limit=limit, status=status)
    return {"sessions": sessions, "stats": recorder.get_stats()}


@router.get("/traces/{session_id}")
async def get_trace(session_id: str):
    """Get a specific trace session."""
    recorder = get_agi_trace_recorder()
    session = recorder.get_session(session_id)
    if session:
        return session.to_dict()
    raise HTTPException(status_code=404, detail="Trace not found")


@router.delete("/traces/{session_id}")
async def delete_trace(session_id: str):
    """Delete a trace session."""
    recorder = get_agi_trace_recorder()
    if recorder.delete_session(session_id):
        return {"success": True}
    raise HTTPException(status_code=404, detail="Trace not found")


# =============================================================================
# Overview Endpoint
# =============================================================================

@router.get("/overview")
async def get_agi_overview():
    """Get AGI Core system overview."""
    mm = get_agi_memory_manager()
    tm = get_agi_task_manager()
    gm = get_agi_goal_manager()
    registry = get_agi_tool_registry()
    store = get_agi_rag_store()
    recorder = get_agi_trace_recorder()
    sandbox_logger = get_sandbox_logger()
    
    return {
        "memory": mm.get_stats(),
        "tasks": tm.get_stats(),
        "goals": gm.get_stats(),
        "tools": {"count": registry.count()},
        "knowledge": {"documents": store.count()},
        "traces": recorder.get_stats(),
        "sandbox": sandbox_logger.get_stats(),
    }


# =============================================================================
# Sandbox Logging Endpoints
# =============================================================================

@router.get("/sandbox/stats")
async def get_sandbox_stats():
    """Get sandbox usage statistics."""
    logger = get_sandbox_logger()
    return logger.get_stats()


@router.get("/sandbox/operations")
async def get_sandbox_operations(limit: int = 50, operation: str = None):
    """Get recent sandbox operations."""
    logger = get_sandbox_logger()
    op_filter = SandboxOperation(operation) if operation else None
    return {
        "operations": logger.get_recent_operations(limit=limit, operation=op_filter),
    }


@router.get("/sandbox/executions")
async def get_sandbox_executions(limit: int = 20, successful_only: bool = False):
    """Get recent code executions."""
    logger = get_sandbox_logger()
    return {
        "executions": logger.get_recent_executions(limit=limit, successful_only=successful_only),
    }


@router.post("/sandbox/log/read")
async def log_sandbox_read(path: str, success: bool = True, size: int = 0, error: str = None):
    """Log a file read operation."""
    logger = get_sandbox_logger()
    entry = logger.log_file_read(path, success, size, error)
    return {"success": True, "entry": entry.to_dict()}


@router.post("/sandbox/log/write")
async def log_sandbox_write(path: str, success: bool = True, size: int = 0, error: str = None):
    """Log a file write operation."""
    logger = get_sandbox_logger()
    entry = logger.log_file_write(path, success, size, error)
    return {"success": True, "entry": entry.to_dict()}


@router.post("/sandbox/log/execute")
async def log_sandbox_execute(
    code: str,
    file_path: str = None,
    stdout: str = "",
    stderr: str = "",
    exit_code: int = 0,
    execution_time: float = 0.0,
):
    """Log a code execution."""
    logger = get_sandbox_logger()
    log = logger.log_execution(code, file_path, stdout, stderr, exit_code, execution_time)
    return {"success": True, "log": log.to_dict()}


@router.post("/sandbox/export-training")
async def export_sandbox_training(successful_only: bool = True):
    """Export sandbox execution logs as training data."""
    logger = get_sandbox_logger()
    count = logger.export_for_training(min_success=successful_only)
    return {"success": True, "examples_exported": count}


@router.delete("/sandbox/logs")
async def clear_sandbox_logs(older_than_days: int = 30):
    """Clear old sandbox logs."""
    logger = get_sandbox_logger()
    removed = logger.clear_logs(older_than_days)
    return {"success": True, "removed": removed}

