"""
deepthinking.py - Chain-of-thought reflection mode.

Implements /deepthinking command functionality:
- Extended reasoning with multiple reflection passes
- Self-critique and improvement
- Structured thought process output
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from chatos_backend.config import DEEPTHINKING_ITERATIONS, DEEPTHINKING_PROMPTS


@dataclass
class ThoughtStep:
    """A single step in the thinking process."""
    
    step_number: int
    phase: str  # "initial", "reflection", "critique", "refinement", "final"
    content: str
    confidence: float = 0.0
    insights: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "phase": self.phase,
            "content": self.content,
            "confidence": self.confidence,
            "insights": self.insights,
        }


@dataclass
class DeepThought:
    """Complete deep thinking result."""
    
    query: str
    thoughts: List[ThoughtStep] = field(default_factory=list)
    final_answer: str = ""
    total_iterations: int = 0
    thinking_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "thoughts": [t.to_dict() for t in self.thoughts],
            "final_answer": self.final_answer,
            "total_iterations": self.total_iterations,
            "thinking_time": self.thinking_time,
            "timestamp": self.timestamp.isoformat(),
        }


class DeepThinkingEngine:
    """
    Deep thinking engine for extended reasoning.
    
    Implements a multi-pass reflection process:
    1. Initial analysis - First pass understanding
    2. Reflection - Consider alternative angles
    3. Critique - Identify weaknesses
    4. Refinement - Improve based on critique
    5. Final synthesis - Produce best answer
    
    In production, each pass would query an LLM with
    specialized prompts for that phase.
    """
    
    def __init__(self, iterations: int = DEEPTHINKING_ITERATIONS):
        self.iterations = iterations
        self._thinking_history: List[DeepThought] = []
    
    async def think(
        self,
        query: str,
        context: str = "",
        verbose: bool = True
    ) -> DeepThought:
        """
        Perform deep thinking on a query.
        
        Args:
            query: The problem or question to think about
            context: Additional context
            verbose: Include detailed thought process
            
        Returns:
            DeepThought with complete reasoning chain
        """
        import time
        start_time = time.time()
        
        result = DeepThought(query=query)
        
        # Phase 1: Initial Analysis
        initial = await self._initial_analysis(query, context)
        result.thoughts.append(initial)
        
        # Phase 2-4: Reflection iterations
        current_thought = initial.content
        for i in range(self.iterations):
            reflection = await self._reflect(query, current_thought, i)
            result.thoughts.append(reflection)
            
            critique = await self._critique(query, reflection.content)
            result.thoughts.append(critique)
            
            refinement = await self._refine(query, reflection.content, critique.content)
            result.thoughts.append(refinement)
            current_thought = refinement.content
        
        # Phase 5: Final Synthesis
        final = await self._synthesize(query, result.thoughts)
        result.thoughts.append(final)
        result.final_answer = final.content
        
        result.total_iterations = self.iterations
        result.thinking_time = time.time() - start_time
        
        self._thinking_history.append(result)
        
        return result
    
    async def _initial_analysis(
        self,
        query: str,
        context: str
    ) -> ThoughtStep:
        """First pass analysis of the problem."""
        await asyncio.sleep(0.2)  # Simulate processing
        
        # Extract key components
        words = query.split()
        key_terms = [w for w in words if len(w) > 4][:5]
        
        content = f"""## Initial Analysis

**Understanding the problem:**
The query asks about: "{query[:100]}..."

**Key components identified:**
{chr(10).join(f'- {term}' for term in key_terms)}

**Initial approach:**
1. Break down the problem into manageable parts
2. Identify relevant knowledge domains
3. Consider practical constraints
4. Form initial hypothesis

**Preliminary thoughts:**
This appears to be a {'complex' if len(words) > 20 else 'focused'} query that requires 
careful consideration of multiple factors. Let me think through this systematically."""
        
        return ThoughtStep(
            step_number=1,
            phase="initial",
            content=content,
            confidence=0.4,
            insights=["Problem decomposition", "Key terms identified"],
        )
    
    async def _reflect(
        self,
        query: str,
        current_thought: str,
        iteration: int
    ) -> ThoughtStep:
        """Reflect on current thinking."""
        await asyncio.sleep(0.2)
        
        prompt = DEEPTHINKING_PROMPTS[iteration % len(DEEPTHINKING_PROMPTS)]
        
        content = f"""## Reflection Pass {iteration + 1}

{prompt}

**Reconsidering the approach:**
Looking at this from a different angle, I notice:

1. **Alternative perspective:** What if we approached this differently?
   - Consider the inverse of the problem
   - Look for patterns that aren't immediately obvious
   
2. **Hidden assumptions:** 
   - Am I assuming certain constraints that don't exist?
   - Are there implicit requirements I'm missing?

3. **Broader context:**
   - How does this relate to similar problems?
   - What solutions have worked in analogous situations?

**Updated understanding:**
After reflection, the core challenge seems to be balancing competing concerns
while maintaining practical applicability."""
        
        return ThoughtStep(
            step_number=2 + (iteration * 3),
            phase="reflection",
            content=content,
            confidence=0.5 + (iteration * 0.1),
            insights=[f"Reflection {iteration + 1}", "Alternative perspectives considered"],
        )
    
    async def _critique(
        self,
        query: str,
        reflection: str
    ) -> ThoughtStep:
        """Self-critique the current thinking."""
        await asyncio.sleep(0.2)
        
        content = """## Critical Analysis

**Potential weaknesses in current thinking:**

1. ⚠️ **Scope concerns:**
   - Am I being too narrow in my focus?
   - Have I considered edge cases?

2. ⚠️ **Logical gaps:**
   - Are there steps in my reasoning that need more support?
   - Could my conclusions be challenged?

3. ⚠️ **Practical limitations:**
   - Is this solution actually implementable?
   - What resources or constraints affect feasibility?

4. ⚠️ **Bias check:**
   - Am I favoring certain approaches due to familiarity?
   - Have I given fair consideration to alternatives?

**Areas requiring improvement:**
- Need more concrete examples
- Should validate assumptions
- Consider failure modes"""
        
        return ThoughtStep(
            step_number=0,  # Will be set properly
            phase="critique",
            content=content,
            confidence=0.6,
            insights=["Self-critique completed", "Weaknesses identified"],
        )
    
    async def _refine(
        self,
        query: str,
        reflection: str,
        critique: str
    ) -> ThoughtStep:
        """Refine thinking based on critique."""
        await asyncio.sleep(0.2)
        
        content = """## Refined Analysis

**Addressing identified weaknesses:**

Based on the critical analysis, I'm improving my approach:

1. ✅ **Expanded scope:**
   - Incorporated edge cases into consideration
   - Broadened perspective on potential solutions

2. ✅ **Strengthened reasoning:**
   - Added supporting evidence for key claims
   - Validated logical steps

3. ✅ **Practical adjustments:**
   - Considered implementation constraints
   - Added fallback options

4. ✅ **Balanced perspective:**
   - Reconsidered alternative approaches
   - Integrated best elements from different strategies

**Improved understanding:**
The refined approach now accounts for:
- Multiple user scenarios
- Technical constraints
- Long-term maintainability
- Error handling needs"""
        
        return ThoughtStep(
            step_number=0,
            phase="refinement",
            content=content,
            confidence=0.75,
            insights=["Weaknesses addressed", "Approach strengthened"],
        )
    
    async def _synthesize(
        self,
        query: str,
        thoughts: List[ThoughtStep]
    ) -> ThoughtStep:
        """Synthesize final answer from all thinking."""
        await asyncio.sleep(0.3)
        
        # Gather insights from all phases
        all_insights = []
        for thought in thoughts:
            all_insights.extend(thought.insights)
        
        unique_insights = list(set(all_insights))[:5]
        
        content = f"""## Final Synthesis

After {len(thoughts)} phases of deep analysis, here is my comprehensive response:

### Summary

This query has been analyzed through multiple perspectives:
- Initial decomposition and understanding
- {self.iterations} rounds of reflection and refinement
- Critical self-evaluation

### Key Insights

{chr(10).join(f'✨ {insight}' for insight in unique_insights)}

### Conclusion

**Regarding: "{query[:50]}..."**

Based on thorough analysis, the best approach involves:

1. **Primary recommendation:** Address the core requirements systematically
2. **Implementation strategy:** Start with fundamentals, iterate based on feedback
3. **Risk mitigation:** Have fallback plans for potential complications
4. **Validation:** Test assumptions early and often

### Confidence Level

After deep reflection: **HIGH** (85%)

This conclusion incorporates multiple perspectives, addresses identified weaknesses,
and provides a balanced, practical solution to the problem at hand."""
        
        return ThoughtStep(
            step_number=len(thoughts) + 1,
            phase="final",
            content=content,
            confidence=0.85,
            insights=["Final synthesis complete", "High confidence conclusion"],
        )
    
    def format_for_display(self, thought: DeepThought) -> str:
        """
        Format deep thought for display in UI.
        
        Args:
            thought: The deep thought result
            
        Returns:
            Formatted markdown string
        """
        lines = [
            f"# 🧠 Deep Thinking: {thought.query[:50]}...",
            "",
            f"*Thinking time: {thought.thinking_time:.2f}s | Iterations: {thought.total_iterations}*",
            "",
            "---",
            "",
        ]
        
        for step in thought.thoughts:
            phase_icon = {
                "initial": "🔍",
                "reflection": "🔄",
                "critique": "⚠️",
                "refinement": "✨",
                "final": "🎯",
            }.get(step.phase, "📝")
            
            lines.append(f"{phase_icon} **{step.phase.title()}** (confidence: {step.confidence:.0%})")
            lines.append("")
            lines.append(step.content)
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return '\n'.join(lines)


# Singleton instance
_engine: Optional[DeepThinkingEngine] = None


def get_deepthinking_engine() -> DeepThinkingEngine:
    """Get the singleton deep thinking engine instance."""
    global _engine
    if _engine is None:
        _engine = DeepThinkingEngine()
    return _engine

