"""
llm_client.py - Universal LLM client for multiple providers.

Handles communication with:
- Ollama (local)
- LM Studio (local)
- llama.cpp (local)
- OpenAI-compatible APIs
- Anthropic
- Google AI
- And more
"""

import asyncio
import json
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from ChatOS.controllers.model_config import (
    ModelConfig,
    ModelProvider,
    PROVIDER_INFO,
    get_model_config_manager,
)


# =============================================================================
# Response Types
# =============================================================================

@dataclass
class LLMResponse:
    """Response from an LLM."""
    
    text: str
    model: str
    provider: ModelProvider
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.error is None


@dataclass
class StreamChunk:
    """A chunk from streaming response."""
    
    text: str
    done: bool = False


# =============================================================================
# LLM Client
# =============================================================================

class LLMClient:
    """
    Universal client for calling different LLM providers.
    
    Supports both streaming and non-streaming responses.
    """
    
    def __init__(self):
        self.config_manager = get_model_config_manager()
        self._http_client: Optional[httpx.AsyncClient] = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=120.0)
        return self._http_client
    
    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    # =========================================================================
    # Main Generate Method
    # =========================================================================
    
    async def generate(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> LLMResponse:
        """
        Generate a response from an LLM.
        
        Args:
            model_config: Model configuration
            messages: List of {"role": "user/assistant/system", "content": "..."}
            temperature: Override temperature
            max_tokens: Override max tokens
            stream: Whether to stream (not fully implemented yet)
            
        Returns:
            LLMResponse with the generated text
        """
        temp = temperature if temperature is not None else model_config.temperature
        tokens = max_tokens if max_tokens is not None else model_config.max_tokens
        
        provider = model_config.provider
        
        try:
            if provider == ModelProvider.DUMMY:
                return await self._generate_dummy(model_config, messages)
            
            elif provider == ModelProvider.OLLAMA:
                return await self._generate_ollama(model_config, messages, temp, tokens)
            
            elif provider in [ModelProvider.LM_STUDIO, ModelProvider.LOCAL_API]:
                return await self._generate_openai_compatible(
                    model_config, messages, temp, tokens,
                    model_config.base_url or PROVIDER_INFO[provider]["default_url"]
                )
            
            elif provider == ModelProvider.LLAMA_CPP:
                return await self._generate_llamacpp(model_config, messages, temp, tokens)
            
            elif provider == ModelProvider.OPENAI:
                return await self._generate_openai(model_config, messages, temp, tokens)
            
            elif provider == ModelProvider.ANTHROPIC:
                return await self._generate_anthropic(model_config, messages, temp, tokens)
            
            elif provider == ModelProvider.GOOGLE:
                return await self._generate_google(model_config, messages, temp, tokens)
            
            elif provider in [ModelProvider.GROQ, ModelProvider.TOGETHER, ModelProvider.OPENROUTER]:
                return await self._generate_openai_compatible(
                    model_config, messages, temp, tokens,
                    PROVIDER_INFO[provider]["default_url"],
                    api_key=self.config_manager.get_api_key(provider)
                )
            
            elif provider == ModelProvider.PERSRM:
                return await self._generate_persrm(model_config, messages, temp, tokens)
            
            else:
                return LLMResponse(
                    text="",
                    model=model_config.model_id,
                    provider=provider,
                    error=f"Unsupported provider: {provider.value}",
                )
                
        except Exception as e:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=provider,
                error=str(e),
            )
    
    # =========================================================================
    # Dummy Provider (Built-in)
    # =========================================================================
    
    async def _generate_dummy(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
    ) -> LLMResponse:
        """Generate response from dummy model."""
        from ChatOS.models.dummy_model import DummyModel
        
        # Get the last user message
        user_message = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_message = msg["content"]
                break
        
        # Determine mode from context
        mode = "normal"
        for msg in messages:
            if "code" in msg.get("content", "").lower():
                mode = "code"
                break
        
        model = DummyModel(model_config.name, behavior=model_config.model_id)
        response = model.generate(user_message, mode=mode)
        
        return LLMResponse(
            text=response,
            model=model_config.name,
            provider=ModelProvider.DUMMY,
        )
    
    # =========================================================================
    # Ollama
    # =========================================================================
    
    async def _generate_ollama(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Generate response from Ollama."""
        client = await self._get_client()
        base_url = model_config.base_url or "http://localhost:11434"
        
        # Convert to Ollama format
        prompt = self._messages_to_prompt(messages)
        
        response = await client.post(
            f"{base_url}/api/generate",
            json={
                "model": model_config.model_id,
                "prompt": prompt,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
                "stream": False,
            },
        )
        
        if response.status_code == 200:
            data = response.json()
            return LLMResponse(
                text=data.get("response", ""),
                model=model_config.model_id,
                provider=ModelProvider.OLLAMA,
                tokens_used=data.get("eval_count"),
            )
        else:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=ModelProvider.OLLAMA,
                error=f"Ollama error: {response.text}",
            )
    
    # =========================================================================
    # OpenAI-Compatible APIs
    # =========================================================================
    
    async def _generate_openai_compatible(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        base_url: str,
        api_key: Optional[str] = None,
    ) -> LLMResponse:
        """Generate response from OpenAI-compatible API."""
        client = await self._get_client()
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        # Ensure URL ends properly
        url = base_url.rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        
        response = await client.post(
            f"{url}/chat/completions",
            headers=headers,
            json={
                "model": model_config.model_id,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        
        if response.status_code == 200:
            data = response.json()
            choice = data.get("choices", [{}])[0]
            return LLMResponse(
                text=choice.get("message", {}).get("content", ""),
                model=model_config.model_id,
                provider=model_config.provider,
                tokens_used=data.get("usage", {}).get("total_tokens"),
                finish_reason=choice.get("finish_reason"),
            )
        else:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=model_config.provider,
                error=f"API error ({response.status_code}): {response.text}",
            )
    
    async def _generate_openai(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Generate response from OpenAI."""
        api_key = self.config_manager.get_api_key(ModelProvider.OPENAI)
        if not api_key:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=ModelProvider.OPENAI,
                error="OpenAI API key not configured",
            )
        
        return await self._generate_openai_compatible(
            model_config, messages, temperature, max_tokens,
            "https://api.openai.com/v1",
            api_key,
        )
    
    # =========================================================================
    # llama.cpp Server
    # =========================================================================
    
    async def _generate_llamacpp(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Generate response from llama.cpp server."""
        client = await self._get_client()
        base_url = model_config.base_url or "http://localhost:8080"
        
        prompt = self._messages_to_prompt(messages)
        
        response = await client.post(
            f"{base_url}/completion",
            json={
                "prompt": prompt,
                "temperature": temperature,
                "n_predict": max_tokens,
            },
        )
        
        if response.status_code == 200:
            data = response.json()
            return LLMResponse(
                text=data.get("content", ""),
                model="llama.cpp",
                provider=ModelProvider.LLAMA_CPP,
                tokens_used=data.get("tokens_evaluated"),
            )
        else:
            return LLMResponse(
                text="",
                model="llama.cpp",
                provider=ModelProvider.LLAMA_CPP,
                error=f"llama.cpp error: {response.text}",
            )
    
    # =========================================================================
    # Anthropic
    # =========================================================================
    
    async def _generate_anthropic(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Generate response from Anthropic."""
        api_key = self.config_manager.get_api_key(ModelProvider.ANTHROPIC)
        if not api_key:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=ModelProvider.ANTHROPIC,
                error="Anthropic API key not configured",
            )
        
        client = await self._get_client()
        
        # Convert messages - Anthropic uses different format
        system_message = ""
        anthropic_messages = []
        
        for msg in messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                anthropic_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })
        
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model_config.model_id,
                "messages": anthropic_messages,
                "system": system_message,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        
        if response.status_code == 200:
            data = response.json()
            text = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    text += block.get("text", "")
            
            return LLMResponse(
                text=text,
                model=model_config.model_id,
                provider=ModelProvider.ANTHROPIC,
                tokens_used=data.get("usage", {}).get("input_tokens", 0) + 
                           data.get("usage", {}).get("output_tokens", 0),
                finish_reason=data.get("stop_reason"),
            )
        else:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=ModelProvider.ANTHROPIC,
                error=f"Anthropic error ({response.status_code}): {response.text}",
            )
    
    # =========================================================================
    # Google AI
    # =========================================================================
    
    async def _generate_google(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Generate response from Google AI."""
        api_key = self.config_manager.get_api_key(ModelProvider.GOOGLE)
        if not api_key:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=ModelProvider.GOOGLE,
                error="Google AI API key not configured",
            )
        
        client = await self._get_client()
        
        # Convert to Google format
        contents = []
        for msg in messages:
            if msg["role"] == "system":
                # Prepend system as user message
                contents.insert(0, {
                    "role": "user",
                    "parts": [{"text": f"[System]: {msg['content']}"}],
                })
            else:
                contents.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [{"text": msg["content"]}],
                })
        
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1/models/{model_config.model_id}:generateContent?key={api_key}",
            json={
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            },
        )
        
        if response.status_code == 200:
            data = response.json()
            text = ""
            for candidate in data.get("candidates", []):
                for part in candidate.get("content", {}).get("parts", []):
                    text += part.get("text", "")
            
            return LLMResponse(
                text=text,
                model=model_config.model_id,
                provider=ModelProvider.GOOGLE,
            )
        else:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=ModelProvider.GOOGLE,
                error=f"Google AI error ({response.status_code}): {response.text}",
            )
    
    # =========================================================================
    # PersRM Reasoning Engine
    # =========================================================================
    
    async def _generate_persrm(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Generate response using PersRM reasoning engine."""
        from ChatOS.plugins.persrm_bridge import PersRMBridge, PersRMConfig
        
        # Get the last user message
        user_message = ""
        context = ""
        for msg in messages:
            if msg["role"] == "user":
                user_message = msg["content"]
            elif msg["role"] == "system":
                context = msg["content"]
        
        # Determine which PersRM mode to use based on model_id
        mode = model_config.model_id
        
        try:
            config = PersRMConfig()
            bridge = PersRMBridge(config)
            
            if mode == "persrm-code":
                # Use code generation mode
                result = await bridge.generate_code(
                    prompt=user_message,
                    language="typescript",
                )
            else:
                # Use reasoning mode (default)
                result = await bridge.reason(
                    prompt=user_message,
                    context=context if context else None,
                )
            
            await bridge.close()
            
            if result.success:
                return LLMResponse(
                    text=result.reasoning,
                    model=f"PersRM ({result.model_used})",
                    provider=ModelProvider.PERSRM,
                    finish_reason="stop",
                )
            else:
                return LLMResponse(
                    text="",
                    model=model_config.model_id,
                    provider=ModelProvider.PERSRM,
                    error=result.error or "PersRM reasoning failed",
                )
                
        except Exception as e:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=ModelProvider.PERSRM,
                error=str(e),
            )
    
    # =========================================================================
    # Helpers
    # =========================================================================
    
    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Convert messages to a single prompt string."""
        parts = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                parts.append(f"System: {content}")
            elif role == "user":
                parts.append(f"User: {content}")
            elif role == "assistant":
                parts.append(f"Assistant: {content}")
        
        parts.append("Assistant:")
        return "\n\n".join(parts)


# =============================================================================
# Council with Real Models
# =============================================================================

class ModelCouncil:
    """
    Orchestrates multiple models to generate and select responses.
    """
    
    def __init__(self):
        self.config_manager = get_model_config_manager()
        self.client = LLMClient()
    
    async def generate_council_response(
        self,
        messages: List[Dict[str, str]],
        mode: str = "normal",
    ) -> Dict[str, Any]:
        """
        Generate responses from all council models and select the best.
        
        Args:
            messages: Conversation messages
            mode: "normal" or "code"
            
        Returns:
            Dict with answer, chosen_model, and all responses
        """
        council_models = self.config_manager.get_council_models()
        
        if not council_models:
            # Fallback to dummy models
            return await self._fallback_response(messages, mode)
        
        # Generate responses in parallel
        tasks = [
            self.client.generate(model, messages)
            for model in council_models
        ]
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect successful responses
        model_responses = []
        for model, response in zip(council_models, responses):
            if isinstance(response, Exception):
                model_responses.append({
                    "model": model.name,
                    "text": f"[Error: {str(response)}]",
                    "error": True,
                })
            elif response.error:
                model_responses.append({
                    "model": model.name,
                    "text": f"[Error: {response.error}]",
                    "error": True,
                })
            else:
                model_responses.append({
                    "model": model.name,
                    "text": response.text,
                    "error": False,
                })
        
        # Select winner based on strategy
        strategy = self.config_manager.settings.council_strategy
        winner = self._select_winner(model_responses, strategy)
        
        return {
            "answer": winner["text"],
            "chosen_model": winner["model"],
            "responses": model_responses,
        }
    
    def _select_winner(
        self,
        responses: List[Dict[str, Any]],
        strategy: str,
    ) -> Dict[str, Any]:
        """Select the winning response based on strategy."""
        
        # Filter out errors
        valid = [r for r in responses if not r.get("error")]
        
        if not valid:
            # Return first response even if error
            return responses[0] if responses else {"model": "none", "text": "No response available"}
        
        if strategy == "first":
            return valid[0]
        
        elif strategy == "voting":
            # Simple voting based on response similarity
            # For now, just return longest
            return max(valid, key=lambda r: len(r["text"]))
        
        else:  # "longest" (default)
            return max(valid, key=lambda r: len(r["text"]))
    
    async def _fallback_response(
        self,
        messages: List[Dict[str, str]],
        mode: str,
    ) -> Dict[str, Any]:
        """Generate fallback response using dummy models."""
        from ChatOS.controllers.chat import chat_endpoint
        
        # Get user message
        user_msg = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                user_msg = msg["content"]
                break
        
        return await chat_endpoint(user_msg, mode=mode)


# =============================================================================
# Singleton
# =============================================================================

_client: Optional[LLMClient] = None
_council: Optional[ModelCouncil] = None


def get_llm_client() -> LLMClient:
    """Get singleton LLM client."""
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def get_model_council() -> ModelCouncil:
    """Get singleton model council."""
    global _council
    if _council is None:
        _council = ModelCouncil()
    return _council

