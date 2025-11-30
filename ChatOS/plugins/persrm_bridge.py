"""
persrm_bridge.py - ChatOS ↔ PersRM Integration Bridge

Provides bidirectional integration between ChatOS and PersRM:
1. ChatOS can use PersRM's reasoning capabilities via /reason command
2. PersRM can use ChatOS's local models (including fine-tuned) for inference

Usage:
    from ChatOS.plugins.persrm_bridge import PersRMBridge, get_persrm_reasoning
    
    # Initialize bridge
    bridge = PersRMBridge()
    
    # Get reasoning from PersRM (if running)
    result = await bridge.reason("How should I design this form?")
    
    # Or use direct Ollama reasoning
    result = await get_persrm_reasoning("Design question", model="ft-qwen25-v1-quality")
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import httpx

logger = logging.getLogger(__name__)


@dataclass
class ReasoningResult:
    """Result from a reasoning operation."""
    success: bool
    reasoning: str
    model_used: str
    source: str  # "persrm", "ollama", or "chatos"
    execution_time: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass 
class PersRMConfig:
    """Configuration for PersRM integration."""
    # PersRM settings
    persrm_enabled: bool = True
    persrm_path: Path = field(default_factory=lambda: Path.home() / "PersRM-V0.2")
    persrm_api_url: str = "http://localhost:3000"  # Default Next.js port
    
    # Ollama settings (shared with ChatOS)
    ollama_url: str = "http://localhost:11434"
    
    # Model preferences - Fine-tuned model for BOTH reasoning AND coding
    reasoning_model: str = "ft-qwen25-v1-quality"
    code_model: str = "ft-qwen25-v1-quality"  # Fine-tuned for code too
    code_fallback: str = "qwen2.5-coder:7b"
    general_model: str = "qwen2.5:7b"
    fallback_model: str = "mistral:7b"
    
    # Timeouts
    reasoning_timeout: int = 120
    api_timeout: int = 30


class PersRMBridge:
    """
    Bridge between ChatOS and PersRM.
    
    Provides:
    - Reasoning via PersRM API (if running)
    - Fallback to direct Ollama calls
    - Model selection and fallback chain
    """
    
    def __init__(self, config: Optional[PersRMConfig] = None):
        self.config = config or PersRMConfig()
        self._http_client: Optional[httpx.AsyncClient] = None
        self._persrm_available: Optional[bool] = None
        
    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            # Use the longer reasoning timeout for all requests
            self._http_client = httpx.AsyncClient(timeout=self.config.reasoning_timeout)
        return self._http_client
        
    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
            
    async def check_persrm_available(self) -> bool:
        """Check if PersRM server is running."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.config.persrm_api_url}/api/health", timeout=5)
            self._persrm_available = response.status_code == 200
        except Exception:
            self._persrm_available = False
        return self._persrm_available
        
    async def reason(
        self,
        prompt: str,
        context: Optional[str] = None,
        model: Optional[str] = None,
        use_persrm: bool = True,
    ) -> ReasoningResult:
        """
        Get reasoning for a prompt.
        
        Args:
            prompt: The question or challenge to reason about
            context: Optional context to include
            model: Override the default model
            use_persrm: Try PersRM first if available
            
        Returns:
            ReasoningResult with the reasoning and metadata
        """
        start_time = datetime.now()
        model_to_use = model or self.config.reasoning_model
        
        # Try PersRM first if enabled and requested
        if use_persrm and self.config.persrm_enabled:
            if self._persrm_available is None:
                await self.check_persrm_available()
                
            if self._persrm_available:
                try:
                    result = await self._reason_via_persrm(prompt, context)
                    result.execution_time = (datetime.now() - start_time).total_seconds()
                    return result
                except Exception as e:
                    logger.warning(f"PersRM reasoning failed, falling back to Ollama: {e}")
        
        # Fallback to direct Ollama
        return await self._reason_via_ollama(
            prompt, 
            context, 
            model_to_use,
            start_time
        )
        
    async def _reason_via_persrm(
        self, 
        prompt: str, 
        context: Optional[str] = None
    ) -> ReasoningResult:
        """Call PersRM's reasoning API."""
        client = await self._get_client()
        
        payload = {
            "prompt": prompt,
            "context": context,
            "model": self.config.reasoning_model,
        }
        
        response = await client.post(
            f"{self.config.persrm_api_url}/api/reasoning",
            json=payload,
            timeout=self.config.reasoning_timeout,
        )
        response.raise_for_status()
        
        data = response.json()
        return ReasoningResult(
            success=True,
            reasoning=data.get("reasoning", ""),
            model_used=data.get("model", self.config.reasoning_model),
            source="persrm",
            execution_time=0,  # Will be set by caller
            metadata=data.get("metadata", {}),
        )
        
    async def _reason_via_ollama(
        self,
        prompt: str,
        context: Optional[str],
        model: str,
        start_time: datetime,
    ) -> ReasoningResult:
        """Call Ollama directly for reasoning."""
        client = await self._get_client()
        
        # Build system prompt
        system_prompt = """You are an expert reasoning assistant. Provide detailed, structured reasoning 
for the following question or challenge. Focus on:
1. Breaking down the problem into components
2. Considering multiple perspectives
3. Weighing tradeoffs and alternatives
4. Drawing clear conclusions with justification

Be thorough but concise."""
        
        if context:
            system_prompt += f"\n\nAdditional context: {context}"
        
        # Try models in fallback order
        models_to_try = [
            model,
            self.config.reasoning_model,
            self.config.general_model,
            self.config.fallback_model,
        ]
        # Remove duplicates while preserving order
        models_to_try = list(dict.fromkeys(models_to_try))
        
        last_error = None
        for model_name in models_to_try:
            try:
                logger.info(f"Trying Ollama model: {model_name}")
                
                response = await client.post(
                    f"{self.config.ollama_url}/api/generate",
                    json={
                        "model": model_name,
                        "prompt": prompt,
                        "system": system_prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 2048,
                        },
                    },
                    timeout=self.config.reasoning_timeout,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return ReasoningResult(
                        success=True,
                        reasoning=data.get("response", ""),
                        model_used=model_name,
                        source="ollama",
                        execution_time=(datetime.now() - start_time).total_seconds(),
                        metadata={
                            "eval_count": data.get("eval_count"),
                            "eval_duration": data.get("eval_duration"),
                        },
                    )
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Model {model_name} failed: {e}")
                continue
                
        return ReasoningResult(
            success=False,
            reasoning="",
            model_used="none",
            source="error",
            execution_time=(datetime.now() - start_time).total_seconds(),
            error=f"All models failed. Last error: {last_error}",
        )
        
    async def generate_code(
        self,
        prompt: str,
        language: str = "typescript",
        model: Optional[str] = None,
    ) -> ReasoningResult:
        """
        Generate code using the code-optimized model.
        """
        model_to_use = model or self.config.code_model
        start_time = datetime.now()
        
        client = await self._get_client()
        
        system_prompt = f"""You are an expert {language} developer. Generate clean, 
well-structured, production-ready code. Include:
1. Proper types/interfaces
2. Error handling
3. Comments for complex logic
4. Best practices for the language

Return only the code, no explanations."""
        
        try:
            response = await client.post(
                f"{self.config.ollama_url}/api/generate",
                json={
                    "model": model_to_use,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower for code
                        "num_predict": 4096,
                    },
                },
                timeout=self.config.reasoning_timeout,
            )
            
            if response.status_code == 200:
                data = response.json()
                return ReasoningResult(
                    success=True,
                    reasoning=data.get("response", ""),
                    model_used=model_to_use,
                    source="ollama",
                    execution_time=(datetime.now() - start_time).total_seconds(),
                )
        except Exception as e:
            return ReasoningResult(
                success=False,
                reasoning="",
                model_used=model_to_use,
                source="error",
                execution_time=(datetime.now() - start_time).total_seconds(),
                error=str(e),
            )


# Convenience function for direct reasoning
async def get_persrm_reasoning(
    prompt: str,
    context: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """
    Convenience function to get reasoning without managing a bridge instance.
    
    Args:
        prompt: The question or challenge
        context: Optional context
        model: Optional model override
        
    Returns:
        The reasoning text, or empty string on failure
    """
    bridge = PersRMBridge()
    try:
        result = await bridge.reason(prompt, context, model)
        return result.reasoning if result.success else ""
    finally:
        await bridge.close()


# Synchronous wrapper for non-async contexts
def get_persrm_reasoning_sync(
    prompt: str,
    context: Optional[str] = None,
    model: Optional[str] = None,
) -> str:
    """Synchronous wrapper for get_persrm_reasoning."""
    return asyncio.run(get_persrm_reasoning(prompt, context, model))

