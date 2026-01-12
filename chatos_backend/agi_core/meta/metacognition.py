"""
Metacognition Engine for AGI Core

Self-monitoring, quality assessment, and performance tracking.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


@dataclass
class QualityMetrics:
    """
    Quality metrics for a response or action.
    
    Attributes:
        factual_accuracy: Estimated factual accuracy (0-1)
        relevance: Relevance to the query/goal (0-1)
        completeness: How complete the response is (0-1)
        coherence: Logical coherence (0-1)
        hallucination_risk: Risk of hallucination (0-1, lower is better)
        confidence: Overall confidence (0-1)
        reasoning: Explanation of assessment
    """
    factual_accuracy: float = 0.5
    relevance: float = 0.5
    completeness: float = 0.5
    coherence: float = 0.5
    hallucination_risk: float = 0.5
    confidence: float = 0.5
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)
    
    def overall_score(self) -> float:
        """Calculate overall quality score."""
        return (
            self.factual_accuracy * 0.25 +
            self.relevance * 0.2 +
            self.completeness * 0.2 +
            self.coherence * 0.15 +
            (1 - self.hallucination_risk) * 0.2
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "factual_accuracy": self.factual_accuracy,
            "relevance": self.relevance,
            "completeness": self.completeness,
            "coherence": self.coherence,
            "hallucination_risk": self.hallucination_risk,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "overall_score": self.overall_score(),
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityMetrics":
        return cls(
            factual_accuracy=data.get("factual_accuracy", 0.5),
            relevance=data.get("relevance", 0.5),
            completeness=data.get("completeness", 0.5),
            coherence=data.get("coherence", 0.5),
            hallucination_risk=data.get("hallucination_risk", 0.5),
            confidence=data.get("confidence", 0.5),
            reasoning=data.get("reasoning", ""),
            timestamp=data.get("timestamp", time.time()),
        )


class MetacognitionEngine:
    """
    Engine for self-assessment and quality monitoring.
    
    Analyzes responses and actions for quality, detects potential
    issues, and tracks performance over time.
    
    Usage:
        engine = MetacognitionEngine(llm_provider=my_llm)
        metrics = await engine.assess_response(query, response)
    """
    
    def __init__(
        self,
        llm_provider: Optional[Callable] = None,
        storage_path: Optional[Path] = None,
    ):
        self.llm_provider = llm_provider
        self.storage_path = storage_path or Path.home() / "ChatOS-Memory" / "agi" / "meta"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.metrics_file = self.storage_path / "metrics_history.json"
        self._history: List[Dict[str, Any]] = []
        
        self._load_history()
    
    def _load_history(self) -> None:
        """Load metrics history from disk."""
        if not self.metrics_file.exists():
            return
        
        try:
            data = json.loads(self.metrics_file.read_text(encoding="utf-8"))
            self._history = data.get("history", [])
        except Exception:
            pass
    
    def _save_history(self) -> None:
        """Save metrics history to disk."""
        # Keep last 1000 entries
        self._history = self._history[-1000:]
        
        data = {
            "version": 1,
            "updated_at": time.time(),
            "history": self._history,
        }
        
        self.metrics_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
    
    async def assess_response(
        self,
        query: str,
        response: str,
        context: Optional[str] = None,
    ) -> QualityMetrics:
        """
        Assess the quality of a response.
        
        Args:
            query: The original query
            response: The generated response
            context: Optional context used
            
        Returns:
            QualityMetrics assessment
        """
        if self.llm_provider:
            return await self._llm_assessment(query, response, context)
        return self._heuristic_assessment(query, response, context)
    
    async def _llm_assessment(
        self,
        query: str,
        response: str,
        context: Optional[str],
    ) -> QualityMetrics:
        """Assess using LLM."""
        prompt = f"""Assess this response for quality:

Query: {query}

Response: {response}

{f'Context used: {context[:500]}' if context else ''}

Rate each from 0.0 to 1.0:
- factual_accuracy: How accurate are the facts?
- relevance: How relevant to the query?
- completeness: How complete is the answer?
- coherence: How logical and well-structured?
- hallucination_risk: Risk of made-up information (lower is better)

Output as JSON:
{{"factual_accuracy": 0.8, "relevance": 0.9, ...}}
"""
        
        try:
            result = await self.llm_provider(prompt)
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', result)
            if json_match:
                data = json.loads(json_match.group())
                metrics = QualityMetrics(
                    factual_accuracy=data.get("factual_accuracy", 0.5),
                    relevance=data.get("relevance", 0.5),
                    completeness=data.get("completeness", 0.5),
                    coherence=data.get("coherence", 0.5),
                    hallucination_risk=data.get("hallucination_risk", 0.5),
                    confidence=0.7,
                    reasoning=result,
                )
                
                self._record_metrics(query, response, metrics)
                return metrics
        except Exception:
            pass
        
        return self._heuristic_assessment(query, response, context)
    
    def _heuristic_assessment(
        self,
        query: str,
        response: str,
        context: Optional[str],
    ) -> QualityMetrics:
        """Assess using heuristics."""
        metrics = QualityMetrics()
        
        # Relevance: keyword overlap
        query_words = set(query.lower().split())
        response_words = set(response.lower().split())
        overlap = len(query_words & response_words) / max(len(query_words), 1)
        metrics.relevance = min(1.0, overlap * 2)
        
        # Completeness: response length relative to query
        response_len = len(response)
        if response_len < 50:
            metrics.completeness = 0.3
        elif response_len < 200:
            metrics.completeness = 0.5
        elif response_len < 500:
            metrics.completeness = 0.7
        else:
            metrics.completeness = 0.8
        
        # Coherence: sentence structure
        sentences = response.split('.')
        if len(sentences) > 1:
            metrics.coherence = 0.7
        else:
            metrics.coherence = 0.5
        
        # Hallucination indicators
        uncertainty_phrases = [
            'i think', 'probably', 'might be', 'could be',
            'not sure', 'possibly', 'approximately'
        ]
        response_lower = response.lower()
        uncertainty_count = sum(1 for p in uncertainty_phrases if p in response_lower)
        
        if uncertainty_count > 2:
            metrics.hallucination_risk = 0.3  # Lower risk with uncertainty
        else:
            metrics.hallucination_risk = 0.5  # Unknown
        
        # Factual accuracy: hard to assess without knowledge
        metrics.factual_accuracy = 0.5
        
        metrics.confidence = 0.4  # Low confidence for heuristics
        metrics.reasoning = "Assessed using heuristic rules"
        
        self._record_metrics(query, response, metrics)
        return metrics
    
    def _record_metrics(
        self,
        query: str,
        response: str,
        metrics: QualityMetrics,
    ) -> None:
        """Record metrics to history."""
        self._history.append({
            "query": query[:200],
            "response_len": len(response),
            "metrics": metrics.to_dict(),
            "timestamp": time.time(),
        })
        self._save_history()
    
    def detect_hallucination_patterns(self, response: str) -> Dict[str, Any]:
        """
        Detect potential hallucination indicators.
        
        Args:
            response: Text to analyze
            
        Returns:
            Dict with detected patterns and risk level
        """
        patterns = {
            "specific_numbers": [],
            "dates": [],
            "citations": [],
            "definitive_claims": [],
        }
        
        import re
        
        # Specific numbers (often hallucinated)
        numbers = re.findall(r'\b\d{4,}\b', response)
        patterns["specific_numbers"] = numbers[:5]
        
        # Dates
        dates = re.findall(r'\b\d{4}\b', response)
        patterns["dates"] = dates[:5]
        
        # Citation-like patterns
        citations = re.findall(r'\([^)]*\d{4}[^)]*\)', response)
        patterns["citations"] = citations[:5]
        
        # Definitive claims
        definitive = re.findall(r'(?:always|never|exactly|precisely|certainly)', response.lower())
        patterns["definitive_claims"] = definitive[:5]
        
        # Calculate risk
        risk = 0.3
        if patterns["specific_numbers"]:
            risk += 0.1
        if patterns["citations"]:
            risk += 0.2  # Citations are often hallucinated
        if patterns["definitive_claims"]:
            risk += 0.1
        
        return {
            "patterns": patterns,
            "risk_level": min(risk, 1.0),
            "recommendation": "Verify specific facts" if risk > 0.5 else "Low risk",
        }
    
    def get_performance_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get performance summary over recent history."""
        cutoff = time.time() - (days * 86400)
        
        recent = [h for h in self._history if h.get("timestamp", 0) > cutoff]
        
        if not recent:
            return {"message": "No recent data", "count": 0}
        
        avg_scores = {
            "factual_accuracy": 0,
            "relevance": 0,
            "completeness": 0,
            "coherence": 0,
            "hallucination_risk": 0,
        }
        
        for entry in recent:
            metrics = entry.get("metrics", {})
            for key in avg_scores:
                avg_scores[key] += metrics.get(key, 0.5)
        
        for key in avg_scores:
            avg_scores[key] /= len(recent)
        
        return {
            "count": len(recent),
            "days": days,
            "average_scores": avg_scores,
            "overall_average": sum(avg_scores.values()) / len(avg_scores),
        }

