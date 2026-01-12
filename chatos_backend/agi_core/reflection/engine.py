"""
Reflection Engine for AGI Core

Enables self-reflection and learning from experience.
"""

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from ..traces.recorder import TraceSession


@dataclass
class Reflection:
    """
    A reflection on a session or experience.
    
    Attributes:
        session_id: ID of the session being reflected on
        what_worked: Things that went well
        what_failed: Things that didn't work
        lessons_learned: Key takeaways
        improvements: Suggested improvements for future
        confidence: Confidence in this reflection
        timestamp: When reflection was created
    """
    session_id: str
    what_worked: List[str] = field(default_factory=list)
    what_failed: List[str] = field(default_factory=list)
    lessons_learned: List[str] = field(default_factory=list)
    improvements: List[str] = field(default_factory=list)
    confidence: float = 0.5
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "what_worked": self.what_worked,
            "what_failed": self.what_failed,
            "lessons_learned": self.lessons_learned,
            "improvements": self.improvements,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Reflection":
        return cls(
            session_id=data["session_id"],
            what_worked=data.get("what_worked", []),
            what_failed=data.get("what_failed", []),
            lessons_learned=data.get("lessons_learned", []),
            improvements=data.get("improvements", []),
            confidence=data.get("confidence", 0.5),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )
    
    def summary(self) -> str:
        """Get a text summary of the reflection."""
        parts = [f"Reflection on session {self.session_id}"]
        
        if self.what_worked:
            parts.append("\nWhat worked:")
            for item in self.what_worked:
                parts.append(f"  + {item}")
        
        if self.what_failed:
            parts.append("\nWhat failed:")
            for item in self.what_failed:
                parts.append(f"  - {item}")
        
        if self.lessons_learned:
            parts.append("\nLessons learned:")
            for item in self.lessons_learned:
                parts.append(f"  * {item}")
        
        if self.improvements:
            parts.append("\nImprovements for next time:")
            for item in self.improvements:
                parts.append(f"  > {item}")
        
        return "\n".join(parts)


class ReflectionEngine:
    """
    Engine for generating and managing reflections.
    
    Analyzes execution traces to extract insights and learnings.
    
    Usage:
        engine = ReflectionEngine(llm_provider=my_llm)
        reflection = await engine.reflect_on_session(trace_session)
    """
    
    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        storage_path: Optional[Path] = None,
    ):
        self.llm_provider = llm_provider
        self.storage_path = storage_path or Path.home() / "ChatOS-Memory" / "agi" / "reflections"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self._reflections: Dict[str, Reflection] = {}
        self._load_reflections()
    
    def _load_reflections(self) -> None:
        """Load existing reflections from disk."""
        for filepath in self.storage_path.glob("*.json"):
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                reflection = Reflection.from_dict(data)
                self._reflections[reflection.session_id] = reflection
            except Exception:
                continue
    
    def _save_reflection(self, reflection: Reflection) -> None:
        """Save a reflection to disk."""
        filepath = self.storage_path / f"{reflection.session_id}.json"
        filepath.write_text(
            json.dumps(reflection.to_dict(), indent=2),
            encoding="utf-8",
        )
    
    async def reflect_on_session(
        self,
        session: TraceSession,
    ) -> Reflection:
        """
        Generate a reflection on a trace session.
        
        Args:
            session: The trace session to reflect on
            
        Returns:
            Generated reflection
        """
        if self.llm_provider:
            return await self._llm_reflection(session)
        return self._rule_based_reflection(session)
    
    async def _llm_reflection(self, session: TraceSession) -> Reflection:
        """Generate reflection using LLM."""
        prompt = self._build_reflection_prompt(session)
        
        response = await self.llm_provider(prompt)
        reflection = self._parse_reflection_response(response, session.session_id)
        
        self._reflections[session.session_id] = reflection
        self._save_reflection(reflection)
        
        return reflection
    
    def _rule_based_reflection(self, session: TraceSession) -> Reflection:
        """Generate reflection using rules (no LLM)."""
        what_worked = []
        what_failed = []
        lessons = []
        
        if session.status == "completed":
            what_worked.append("Goal was successfully completed")
        else:
            what_failed.append(f"Session ended with status: {session.status}")
        
        tool_usage = {}
        for step in session.steps:
            for tool in step.tools_used:
                tool_usage[tool] = tool_usage.get(tool, 0) + 1
        
        if tool_usage:
            most_used = max(tool_usage.keys(), key=lambda t: tool_usage[t])
            what_worked.append(f"Effectively used {most_used} tool ({tool_usage[most_used]} times)")
        
        if len(session.steps) > 10:
            what_failed.append("Took many steps - could be more efficient")
            lessons.append("Look for ways to accomplish goals in fewer steps")
        
        if session.error:
            what_failed.append(f"Error occurred: {session.error}")
            lessons.append("Add better error handling for similar situations")
        
        reflection = Reflection(
            session_id=session.session_id,
            what_worked=what_worked,
            what_failed=what_failed,
            lessons_learned=lessons,
            improvements=["Review and optimize tool selection"],
            confidence=0.5,
            metadata={"goal": session.goal, "step_count": len(session.steps)},
        )
        
        self._reflections[session.session_id] = reflection
        self._save_reflection(reflection)
        
        return reflection
    
    def _build_reflection_prompt(self, session: TraceSession) -> str:
        """Build prompt for LLM reflection."""
        steps_summary = []
        for step in session.steps[:10]:
            steps_summary.append(f"- Step {step.step_number}: {step.action}")
            if step.tools_used:
                steps_summary.append(f"  Tools: {', '.join(step.tools_used)}")
        
        return f"""Reflect on this execution session:

Goal: {session.goal}
Status: {session.status}
Steps taken: {len(session.steps)}
Duration: {session.duration_seconds():.1f}s

Steps:
{chr(10).join(steps_summary)}

{f'Error: {session.error}' if session.error else ''}
{f'Result: {session.result}' if session.result else ''}

Provide reflection as JSON:
{{
    "what_worked": ["list of things that went well"],
    "what_failed": ["list of things that didn't work"],
    "lessons_learned": ["key takeaways"],
    "improvements": ["suggestions for next time"]
}}
"""
    
    def _parse_reflection_response(
        self, response: str, session_id: str,
    ) -> Reflection:
        """Parse LLM response into Reflection."""
        json_match = re.search(r'\{[\s\S]*\}', response)
        
        if json_match:
            try:
                data = json.loads(json_match.group())
                return Reflection(
                    session_id=session_id,
                    what_worked=data.get("what_worked", []),
                    what_failed=data.get("what_failed", []),
                    lessons_learned=data.get("lessons_learned", []),
                    improvements=data.get("improvements", []),
                    confidence=0.7,
                )
            except json.JSONDecodeError:
                pass
        
        return Reflection(
            session_id=session_id,
            lessons_learned=[response[:500]],
            confidence=0.3,
        )
    
    def get_reflection(self, session_id: str) -> Optional[Reflection]:
        """Get a reflection by session ID."""
        return self._reflections.get(session_id)
    
    def get_recent_lessons(self, limit: int = 10) -> List[str]:
        """Get recent lessons learned across all reflections."""
        all_lessons = []
        
        sorted_reflections = sorted(
            self._reflections.values(),
            key=lambda r: r.timestamp,
            reverse=True,
        )
        
        for reflection in sorted_reflections[:limit]:
            all_lessons.extend(reflection.lessons_learned)
        
        return all_lessons[:limit]
    
    def get_common_failures(self, limit: int = 5) -> List[str]:
        """Get common failure patterns."""
        failure_counts = {}
        
        for reflection in self._reflections.values():
            for failure in reflection.what_failed:
                failure_counts[failure] = failure_counts.get(failure, 0) + 1
        
        sorted_failures = sorted(
            failure_counts.keys(),
            key=lambda f: failure_counts[f],
            reverse=True,
        )
        
        return sorted_failures[:limit]

