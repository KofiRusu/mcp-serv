"""
Critic Agent for AGI Core

Reviews and evaluates outputs from other agents.
"""

import json
import re
from typing import Any, Callable, Dict, List, Optional

from .base import BaseAgent, AgentContext, AgentResult


class CriticAgent(BaseAgent):
    """
    Agent responsible for reviewing and improving outputs.
    
    Evaluates work quality, identifies issues, and suggests improvements.
    
    Usage:
        critic = CriticAgent(llm_provider=my_llm)
        context = AgentContext(goal="Write clean Python code")
        result = await critic.review(
            output="def foo(x): return x+1",
            context=context
        )
    """
    
    def __init__(self, llm_provider: Optional[Callable] = None):
        super().__init__(
            name="Critic",
            role="critic",
            description="Reviews outputs for quality, correctness, and completeness. Provides constructive feedback and suggestions for improvement.",
            llm_provider=llm_provider,
        )
    
    def get_system_prompt(self) -> str:
        return """You are a Critic Agent specializing in quality assessment.

Your role is to:
1. Review outputs objectively and thoroughly
2. Identify errors, issues, or areas for improvement
3. Assess whether the output meets the stated goals
4. Provide specific, actionable feedback
5. Rate confidence in the output's quality

When reviewing, output JSON in this format:
{
    "approved": true/false,
    "quality_score": 0.0-1.0,
    "issues": ["list of issues found"],
    "strengths": ["list of positive aspects"],
    "suggestions": ["specific improvement suggestions"],
    "reasoning": "explanation of your assessment"
}

Be constructive but honest. High standards are important but so is recognizing good work.
"""
    
    async def act(self, context: AgentContext) -> AgentResult:
        """
        Review the output in context.
        
        Args:
            context: Context containing output to review in metadata
            
        Returns:
            AgentResult with review assessment
        """
        output_to_review = context.metadata.get("output_to_review")
        
        if not output_to_review:
            return AgentResult(
                success=False,
                error="No output provided for review",
            )
        
        return await self.review(output_to_review, context)
    
    async def review(
        self,
        output: Any,
        context: AgentContext,
        criteria: Optional[List[str]] = None,
    ) -> AgentResult:
        """
        Review an output against given criteria.
        
        Args:
            output: The output to review
            context: Context with goal and requirements
            criteria: Optional specific criteria to check
            
        Returns:
            AgentResult with review assessment
        """
        prompt = self._build_review_prompt(output, context, criteria)
        
        try:
            response = await self.think(prompt)
            assessment = self._parse_review_response(response)
            
            return AgentResult(
                success=True,
                output=assessment,
                reasoning=assessment.get("reasoning", ""),
                confidence=assessment.get("quality_score", 0.5),
                suggestions=assessment.get("suggestions", []),
                metadata={
                    "approved": assessment.get("approved", False),
                    "issues": assessment.get("issues", []),
                    "strengths": assessment.get("strengths", []),
                }
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Review failed: {str(e)}",
            )
    
    def _build_review_prompt(
        self,
        output: Any,
        context: AgentContext,
        criteria: Optional[List[str]] = None,
    ) -> str:
        """Build the review prompt."""
        parts = [self.get_system_prompt(), ""]
        
        parts.append(f"Goal/Requirements: {context.goal or context.task_description}")
        
        if criteria:
            parts.append("\nSpecific criteria to check:")
            for c in criteria:
                parts.append(f"- {c}")
        
        parts.append(f"\nOutput to review:\n```\n{output}\n```")
        
        parts.append("\nProvide your assessment as JSON.")
        
        return "\n".join(parts)
    
    def _parse_review_response(self, response: str) -> Dict[str, Any]:
        """Parse the review response."""
        # Try to extract JSON
        json_match = re.search(r'\{[\s\S]*\}', response)
        
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        # Fallback: construct assessment from response text
        return {
            "approved": "approved" in response.lower() or "good" in response.lower(),
            "quality_score": 0.5,
            "issues": [],
            "strengths": [],
            "suggestions": [],
            "reasoning": response,
        }
    
    async def compare(
        self,
        outputs: List[Any],
        context: AgentContext,
    ) -> AgentResult:
        """
        Compare multiple outputs and select the best.
        
        Args:
            outputs: List of outputs to compare
            context: Context with selection criteria
            
        Returns:
            AgentResult with best output index and comparison
        """
        prompt = self._build_comparison_prompt(outputs, context)
        
        try:
            response = await self.think(prompt)
            
            # Try to extract winner index
            winner_match = re.search(r'(?:best|winner|select).*?(\d+)', response, re.IGNORECASE)
            winner_index = int(winner_match.group(1)) - 1 if winner_match else 0
            winner_index = max(0, min(winner_index, len(outputs) - 1))
            
            return AgentResult(
                success=True,
                output={
                    "winner_index": winner_index,
                    "winner": outputs[winner_index],
                },
                reasoning=response,
                confidence=0.7,
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Comparison failed: {str(e)}",
            )
    
    def _build_comparison_prompt(
        self,
        outputs: List[Any],
        context: AgentContext,
    ) -> str:
        """Build comparison prompt."""
        parts = [
            f"You are comparing {len(outputs)} outputs for the following goal:",
            context.goal or context.task_description,
            "",
        ]
        
        for i, output in enumerate(outputs):
            parts.append(f"Output {i + 1}:\n```\n{output}\n```\n")
        
        parts.append("Which output is best? Explain your reasoning and state the winner number.")
        
        return "\n".join(parts)
    
    async def suggest_improvements(
        self,
        output: Any,
        issues: List[str],
        context: AgentContext,
    ) -> AgentResult:
        """
        Suggest specific improvements for identified issues.
        
        Args:
            output: The output with issues
            issues: List of identified issues
            context: Execution context
            
        Returns:
            AgentResult with improvement suggestions
        """
        prompt = f"""{self.get_system_prompt()}

Original output:
```
{output}
```

Identified issues:
{chr(10).join(f'- {issue}' for issue in issues)}

Goal: {context.goal or context.task_description}

Provide specific, actionable suggestions to fix each issue. Be concrete and provide examples where helpful.
"""
        
        try:
            response = await self.think(prompt)
            
            return AgentResult(
                success=True,
                output=response,
                suggestions=self._extract_suggestions(response),
                confidence=0.7,
            )
            
        except Exception as e:
            return AgentResult(
                success=False,
                error=f"Failed to generate improvements: {str(e)}",
            )
    
    def _extract_suggestions(self, response: str) -> List[str]:
        """Extract suggestions from response."""
        suggestions = []
        
        # Look for numbered or bulleted items
        lines = response.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^[\d\.\-\*]+\s+', line):
                suggestion = re.sub(r'^[\d\.\-\*]+\s+', '', line)
                if len(suggestion) > 10:
                    suggestions.append(suggestion)
        
        return suggestions

