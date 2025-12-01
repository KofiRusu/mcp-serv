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

Performance Optimizations:
- Connection pooling with keep-alive
- Tiered timeouts for different request types
- Response caching with TTL
- Proper client lifecycle management
"""

import asyncio
import hashlib
import json
import time
import atexit
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from functools import lru_cache

import httpx

from ChatOS.controllers.model_config import (
    ModelConfig,
    ModelProvider,
    PROVIDER_INFO,
    get_model_config_manager,
)


# =============================================================================
# Timeout Configuration (Tiered)
# =============================================================================

class TimeoutTier:
    """Tiered timeout configuration for different request types."""
    # Quick requests (health checks, simple queries)
    QUICK = httpx.Timeout(connect=5.0, read=30.0, write=10.0, pool=5.0)
    # Standard LLM requests
    STANDARD = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=10.0)
    # Long-running requests (complex queries, streaming)
    EXTENDED = httpx.Timeout(connect=30.0, read=300.0, write=30.0, pool=30.0)
    # Streaming (very long read timeout)
    STREAMING = httpx.Timeout(connect=30.0, read=600.0, write=30.0, pool=30.0)


# =============================================================================
# Connection Pool Configuration
# =============================================================================

# Global connection limits for all providers
CONNECTION_LIMITS = httpx.Limits(
    max_keepalive_connections=20,
    max_connections=100,
    keepalive_expiry=30.0,  # Keep connections alive for 30 seconds
)


# =============================================================================
# Response Cache (LRU with TTL)
# =============================================================================

class ResponseCache:
    """
    Simple LRU cache with TTL for caching LLM responses.
    
    Caches identical prompts to reduce API calls and latency.
    """
    
    def __init__(self, maxsize: int = 100, ttl_seconds: float = 300.0):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._access_order: List[str] = []
    
    def _make_key(self, model_id: str, messages: List[Dict[str, str]], temperature: float) -> str:
        """Create a cache key from request parameters."""
        content = json.dumps({
            "model": model_id,
            "messages": messages,
            "temperature": temperature,
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, model_id: str, messages: List[Dict[str, str]], temperature: float) -> Optional[Any]:
        """Get cached response if valid."""
        key = self._make_key(model_id, messages, temperature)
        if key in self._cache:
            response, timestamp = self._cache[key]
            if time.time() - timestamp < self.ttl_seconds:
                # Move to end of access order (most recently used)
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return response
            else:
                # Expired, remove
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
        return None
    
    def set(self, model_id: str, messages: List[Dict[str, str]], temperature: float, response: Any) -> None:
        """Cache a response."""
        key = self._make_key(model_id, messages, temperature)
        
        # Evict oldest if at capacity
        while len(self._cache) >= self.maxsize and self._access_order:
            oldest_key = self._access_order.pop(0)
            self._cache.pop(oldest_key, None)
        
        self._cache[key] = (response, time.time())
        self._access_order.append(key)
    
    def clear(self) -> None:
        """Clear the cache."""
        self._cache.clear()
        self._access_order.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "maxsize": self.maxsize,
            "ttl_seconds": self.ttl_seconds,
        }


# Global response cache instance
_response_cache = ResponseCache(maxsize=100, ttl_seconds=300.0)


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
    finish_reason: Optional[str] = None


# =============================================================================
# LLM Client
# =============================================================================

class LLMClient:
    """
    Universal client for calling different LLM providers.
    
    Supports both streaming and non-streaming responses.
    
    Performance features:
    - Connection pooling with configurable limits
    - Tiered timeouts based on request type
    - Response caching with TTL
    - Proper client lifecycle management
    """
    
    def __init__(self, use_cache: bool = True):
        self.config_manager = get_model_config_manager()
        self._http_clients: Dict[str, httpx.AsyncClient] = {}
        self._use_cache = use_cache
        self._cache = _response_cache
        self._initialized = False
    
    async def _get_client(
        self,
        timeout_tier: httpx.Timeout = TimeoutTier.STANDARD,
        base_url: Optional[str] = None,
        http2: bool = True,
    ) -> httpx.AsyncClient:
        """
        Get or create HTTP client with connection pooling.
        
        Uses a pool of clients keyed by base URL for optimal connection reuse.
        """
        # Use base URL + http2 flag as key for client pooling
        pool_key = f"{base_url or 'default'}:http2={http2}"
        
        if pool_key not in self._http_clients or self._http_clients[pool_key].is_closed:
            self._http_clients[pool_key] = httpx.AsyncClient(
                timeout=timeout_tier,
                limits=CONNECTION_LIMITS,
                http2=http2,  # Enable HTTP/2 only for providers that support it
            )
        
        return self._http_clients[pool_key]
    
    async def _get_client_for_provider(
        self,
        provider: ModelProvider,
        base_url: Optional[str] = None,
        is_streaming: bool = False,
    ) -> httpx.AsyncClient:
        """Get an HTTP client optimized for a specific provider."""
        # Determine appropriate timeout tier
        if is_streaming:
            timeout = TimeoutTier.STREAMING
        elif provider in [ModelProvider.OLLAMA, ModelProvider.LLAMA_CPP]:
            # Local models may take longer to load
            timeout = TimeoutTier.EXTENDED
        elif provider == ModelProvider.DUMMY:
            timeout = TimeoutTier.QUICK
        else:
            timeout = TimeoutTier.STANDARD
        
        # Disable HTTP/2 for local providers (Ollama/llama.cpp don't support it)
        use_http2 = provider not in [ModelProvider.OLLAMA, ModelProvider.LLAMA_CPP]
        return await self._get_client(timeout_tier=timeout, base_url=base_url, http2=use_http2)
    
    async def close(self):
        """Close all HTTP clients and cleanup resources."""
        for key, client in list(self._http_clients.items()):
            if not client.is_closed:
                await client.aclose()
        self._http_clients.clear()
    
    async def __aenter__(self):
        """Context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        await self.close()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get response cache statistics."""
        return self._cache.stats()
    
    def clear_cache(self) -> None:
        """Clear the response cache."""
        self._cache.clear()
    
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
        use_cache: Optional[bool] = None,
    ) -> LLMResponse:
        """
        Generate a response from an LLM.
        
        Args:
            model_config: Model configuration
            messages: List of {"role": "user/assistant/system", "content": "..."}
            temperature: Override temperature
            max_tokens: Override max tokens
            stream: Whether to stream (aggregates chunks internally)
            use_cache: Override cache setting for this request
            
        Returns:
            LLMResponse with the generated text
        """
        temp = temperature if temperature is not None else model_config.temperature
        tokens = max_tokens if max_tokens is not None else model_config.max_tokens
        
        provider = model_config.provider
        
        # Check cache first (only for non-streaming, non-dummy requests)
        should_cache = (use_cache if use_cache is not None else self._use_cache)
        if should_cache and not stream and provider != ModelProvider.DUMMY:
            cached = self._cache.get(model_config.model_id, messages, temp)
            if cached is not None:
                return cached
        
        if stream:
            chunks: List[str] = []
            last_finish: Optional[str] = None
            try:
                async for chunk in self.stream_generate(
                    model_config,
                    messages,
                    temperature=temp,
                    max_tokens=tokens,
                ):
                    if chunk.text:
                        chunks.append(chunk.text)
                    if chunk.done:
                        last_finish = chunk.finish_reason or last_finish
                aggregated_text = "".join(chunks)
                return LLMResponse(
                    text=aggregated_text,
                    model=model_config.model_id,
                    provider=provider,
                    finish_reason=last_finish,
                )
            except Exception as exc:
                return LLMResponse(
                    text="",
                    model=model_config.model_id,
                    provider=provider,
                    error=str(exc),
                )
        
        try:
            if provider == ModelProvider.DUMMY:
                response = await self._generate_dummy(model_config, messages)
            
            elif provider == ModelProvider.OLLAMA:
                response = await self._generate_ollama(model_config, messages, temp, tokens)
            
            elif provider in [ModelProvider.LM_STUDIO, ModelProvider.LOCAL_API]:
                response = await self._generate_openai_compatible(
                    model_config, messages, temp, tokens,
                    model_config.base_url or PROVIDER_INFO[provider]["default_url"]
                )
            
            elif provider == ModelProvider.LLAMA_CPP:
                response = await self._generate_llamacpp(model_config, messages, temp, tokens)
            
            elif provider == ModelProvider.OPENAI:
                response = await self._generate_openai(model_config, messages, temp, tokens)
            
            elif provider == ModelProvider.ANTHROPIC:
                response = await self._generate_anthropic(model_config, messages, temp, tokens)
            
            elif provider == ModelProvider.GOOGLE:
                response = await self._generate_google(model_config, messages, temp, tokens)
            
            elif provider in [ModelProvider.GROQ, ModelProvider.TOGETHER, ModelProvider.OPENROUTER]:
                response = await self._generate_openai_compatible(
                    model_config, messages, temp, tokens,
                    PROVIDER_INFO[provider]["default_url"],
                    api_key=self.config_manager.get_api_key(provider)
                )
            
            elif provider == ModelProvider.MINIMAX:
                response = await self._generate_minimax(model_config, messages, temp, tokens)
            
            elif provider == ModelProvider.PERSRM:
                response = await self._generate_persrm(model_config, messages, temp, tokens)
            
            else:
                response = LLMResponse(
                    text="",
                    model=model_config.model_id,
                    provider=provider,
                    error=f"Unsupported provider: {provider.value}",
                )
            
            # Cache successful responses
            if should_cache and response.success and not stream:
                self._cache.set(model_config.model_id, messages, temp, response)
            
            return response
                
        except Exception as e:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=provider,
                error=str(e),
            )

    # =========================================================================
    # Streaming Interfaces
    # =========================================================================

    async def stream_generate(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Stream responses from an LLM provider.
        
        Yields:
            StreamChunk objects with partial text.
        """
        provider = model_config.provider
        temp = temperature if temperature is not None else model_config.temperature
        tokens = max_tokens if max_tokens is not None else model_config.max_tokens
        
        if provider == ModelProvider.DUMMY:
            response = await self._generate_dummy(model_config, messages)
            yield StreamChunk(text=response.text, done=True, finish_reason="stop")
            return
        
        if provider == ModelProvider.OLLAMA:
            async for chunk in self._stream_ollama(model_config, messages, temp, tokens):
                yield chunk
            return
        
        openai_like = {
            ModelProvider.LM_STUDIO,
            ModelProvider.LOCAL_API,
            ModelProvider.OPENAI,
            ModelProvider.GROQ,
            ModelProvider.TOGETHER,
            ModelProvider.OPENROUTER,
            ModelProvider.MINIMAX,
        }
        if provider in openai_like:
            base_url = model_config.base_url or PROVIDER_INFO[provider]["default_url"]
            api_key = None
            if provider == ModelProvider.OPENAI:
                api_key = self.config_manager.get_api_key(ModelProvider.OPENAI)
            elif provider in {ModelProvider.GROQ, ModelProvider.TOGETHER, ModelProvider.OPENROUTER, ModelProvider.MINIMAX}:
                api_key = self.config_manager.get_api_key(provider)
            async for chunk in self._stream_openai_compatible(
                model_config,
                messages,
                temp,
                tokens,
                base_url,
                api_key=api_key,
            ):
                yield chunk
            return
        
        # Fallback to non-streaming call
        response = await self.generate(
            model_config,
            messages,
            temperature=temp,
            max_tokens=tokens,
            stream=False,
        )
        yield StreamChunk(text=response.text, done=True, finish_reason=response.finish_reason or "stop")
    
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
        """Generate response from Ollama with optimized connection pooling."""
        base_url = model_config.base_url or "http://localhost:11434"
        client = await self._get_client_for_provider(
            ModelProvider.OLLAMA,
            base_url=base_url,
        )
        
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
        """Generate response from OpenAI-compatible API with connection pooling."""
        # Ensure URL ends properly
        url = base_url.rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        
        client = await self._get_client_for_provider(
            model_config.provider,
            base_url=url,
        )
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
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

    async def _stream_openai_compatible(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
        base_url: str,
        api_key: Optional[str] = None,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream responses from OpenAI-compatible chat completions."""
        url = base_url.rstrip("/")
        if not url.endswith("/v1"):
            url = f"{url}/v1"
        
        client = await self._get_client_for_provider(
            model_config.provider,
            base_url=url,
            is_streaming=True,
        )
        
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        payload = {
            "model": model_config.model_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        
        async with client.stream(
            "POST",
            f"{url}/chat/completions",
            headers=headers,
            json=payload,
        ) as response:
            if response.status_code != 200:
                text = await response.aread()
                raise RuntimeError(f"API error ({response.status_code}): {text.decode()}")
            
            async for line in response.aiter_lines():
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        yield StreamChunk(text="", done=True, finish_reason="stop")
                        break
                    try:
                        payload = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    choices = payload.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})
                    content = delta.get("content")
                    finish_reason = choices[0].get("finish_reason")
                    if content:
                        yield StreamChunk(text=content, done=False)
                    if finish_reason and finish_reason != "incomplete":
                        yield StreamChunk(text="", done=True, finish_reason=finish_reason)
                        break
    
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
        """Generate response from llama.cpp server with optimized connection pooling."""
        base_url = model_config.base_url or "http://localhost:8080"
        client = await self._get_client_for_provider(
            ModelProvider.LLAMA_CPP,
            base_url=base_url,
        )
        
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

    async def _stream_ollama(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> AsyncGenerator[StreamChunk, None]:
        """Stream responses from Ollama."""
        base_url = model_config.base_url or "http://localhost:11434"
        client = await self._get_client_for_provider(
            ModelProvider.OLLAMA,
            base_url=base_url,
            is_streaming=True,
        )
        
        prompt = self._messages_to_prompt(messages)
        payload = {
            "model": model_config.model_id,
            "prompt": prompt,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
            "stream": True,
        }
        
        async with client.stream(
            "POST",
            f"{base_url}/api/generate",
            json=payload,
        ) as response:
            if response.status_code != 200:
                text = await response.aread()
                raise RuntimeError(f"Ollama error ({response.status_code}): {text.decode()}")
            
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                chunk_text = data.get("response")
                if chunk_text:
                    yield StreamChunk(text=chunk_text, done=False)
                
                if data.get("done"):
                    yield StreamChunk(
                        text="",
                        done=True,
                        finish_reason=data.get("done_reason") or "stop",
                    )
                    break
    
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
        """Generate response from Anthropic with optimized connection pooling."""
        api_key = self.config_manager.get_api_key(ModelProvider.ANTHROPIC)
        if not api_key:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=ModelProvider.ANTHROPIC,
                error="Anthropic API key not configured",
            )
        
        client = await self._get_client_for_provider(
            ModelProvider.ANTHROPIC,
            base_url="https://api.anthropic.com",
        )
        
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
        """Generate response from Google AI with optimized connection pooling."""
        api_key = self.config_manager.get_api_key(ModelProvider.GOOGLE)
        if not api_key:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=ModelProvider.GOOGLE,
                error="Google AI API key not configured",
            )
        
        client = await self._get_client_for_provider(
            ModelProvider.GOOGLE,
            base_url="https://generativelanguage.googleapis.com",
        )
        
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
    # MiniMax AI
    # =========================================================================
    
    async def _generate_minimax(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Generate response from MiniMax AI."""
        # Check if it's a local model (run via Ollama/vLLM)
        local_models = PROVIDER_INFO[ModelProvider.MINIMAX].get("local_models", [])
        is_local = model_config.model_id in local_models
        
        if is_local:
            # Try to use via Ollama first
            return await self._generate_minimax_local(model_config, messages, temperature, max_tokens)
        else:
            # Use MiniMax API
            return await self._generate_minimax_api(model_config, messages, temperature, max_tokens)
    
    async def _generate_minimax_api(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Generate response from MiniMax API with optimized connection pooling."""
        api_key = self.config_manager.get_api_key(ModelProvider.MINIMAX)
        if not api_key:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=ModelProvider.MINIMAX,
                error="MiniMax API key not configured. Set MINIMAX_API_KEY env var or configure in settings.",
            )
        
        base_url = model_config.base_url or "https://api.minimax.chat/v1"
        client = await self._get_client_for_provider(
            ModelProvider.MINIMAX,
            base_url=base_url,
        )
        
        # MiniMax uses OpenAI-compatible API format
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        
        # Convert messages to MiniMax format
        minimax_messages = []
        for msg in messages:
            role = msg["role"]
            # MiniMax uses 'USER' and 'BOT' roles
            if role == "user":
                minimax_messages.append({"sender_type": "USER", "text": msg["content"]})
            elif role == "assistant":
                minimax_messages.append({"sender_type": "BOT", "text": msg["content"]})
            elif role == "system":
                # Prepend system message as context
                minimax_messages.insert(0, {"sender_type": "USER", "text": f"[System Instructions]: {msg['content']}"})
        
        try:
            response = await client.post(
                f"{base_url}/text/chatcompletion_v2",
                headers=headers,
                json={
                    "model": model_config.model_id,
                    "messages": minimax_messages,
                    "temperature": temperature,
                    "tokens_to_generate": max_tokens,
                    "mask_sensitive_info": False,
                },
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract response text
                reply = data.get("reply", "")
                if not reply and "choices" in data:
                    # OpenAI-compatible format fallback
                    choice = data.get("choices", [{}])[0]
                    reply = choice.get("message", {}).get("content", "")
                
                return LLMResponse(
                    text=reply,
                    model=model_config.model_id,
                    provider=ModelProvider.MINIMAX,
                    tokens_used=data.get("usage", {}).get("total_tokens"),
                    finish_reason=data.get("finish_reason", "stop"),
                )
            else:
                return LLMResponse(
                    text="",
                    model=model_config.model_id,
                    provider=ModelProvider.MINIMAX,
                    error=f"MiniMax API error ({response.status_code}): {response.text}",
                )
        except Exception as e:
            return LLMResponse(
                text="",
                model=model_config.model_id,
                provider=ModelProvider.MINIMAX,
                error=f"MiniMax API error: {str(e)}",
            )
    
    async def _generate_minimax_local(
        self,
        model_config: ModelConfig,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> LLMResponse:
        """Generate response from locally running MiniMax model (via Ollama or vLLM)."""
        # Check if the model is available in Ollama
        try:
            # First try Ollama
            ollama_model_id = model_config.model_id.lower().replace("-", "")
            ollama_config = ModelConfig(
                id=model_config.id,
                name=model_config.name,
                provider=ModelProvider.OLLAMA,
                model_id=ollama_model_id,
                base_url="http://localhost:11434",
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            result = await self._generate_ollama(ollama_config, messages, temperature, max_tokens)
            if result.success:
                # Override provider to show it's MiniMax
                return LLMResponse(
                    text=result.text,
                    model=f"MiniMax ({model_config.model_id})",
                    provider=ModelProvider.MINIMAX,
                    tokens_used=result.tokens_used,
                    finish_reason=result.finish_reason,
                )
        except Exception:
            pass
        
        # Try vLLM/OpenAI-compatible local server
        try:
            local_url = model_config.base_url or "http://localhost:8000"
            result = await self._generate_openai_compatible(
                model_config, messages, temperature, max_tokens, local_url
            )
            if result.success:
                return LLMResponse(
                    text=result.text,
                    model=f"MiniMax ({model_config.model_id})",
                    provider=ModelProvider.MINIMAX,
                    tokens_used=result.tokens_used,
                    finish_reason=result.finish_reason,
                )
        except Exception:
            pass
        
        return LLMResponse(
            text="",
            model=model_config.model_id,
            provider=ModelProvider.MINIMAX,
            error="MiniMax local model not available. Install via: ollama pull minimax-m1 or run vLLM server",
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
# Singleton & Lifecycle Management
# =============================================================================

_client: Optional[LLMClient] = None
_council: Optional[ModelCouncil] = None


def get_llm_client() -> LLMClient:
    """Get singleton LLM client with connection pooling."""
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


async def cleanup_llm_client() -> None:
    """Cleanup LLM client connections. Call on application shutdown."""
    global _client, _council
    if _client is not None:
        await _client.close()
        _client = None
    if _council is not None:
        await _council.client.close()
        _council = None


def get_response_cache_stats() -> Dict[str, Any]:
    """Get response cache statistics."""
    return _response_cache.stats()


def clear_response_cache() -> None:
    """Clear the response cache."""
    _response_cache.clear()


# Register cleanup on process exit (best effort)
def _sync_cleanup():
    """Synchronous cleanup wrapper for atexit."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(cleanup_llm_client())
        else:
            loop.run_until_complete(cleanup_llm_client())
    except Exception:
        pass  # Best effort cleanup

atexit.register(_sync_cleanup)
