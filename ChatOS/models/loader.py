"""
Model loader for ChatOS.

This module exposes a `load_models` function that returns a
dictionary mapping model names to model instances. The council
uses multiple models to generate diverse responses.

============================================================================
HOW TO ADD REAL LLM BACKENDS
============================================================================

To integrate a real language model (e.g., Ollama, llama.cpp, vLLM), 
create a wrapper class that implements the same interface:

```python
class OllamaModel:
    def __init__(self, name: str, model_id: str = "llama2"):
        self.name = name
        self.model_id = model_id
        # Initialize your client here
        # self.client = ollama.Client()
    
    def generate(self, prompt: str, mode: str = "normal") -> str:
        # Call your LLM backend
        # response = self.client.generate(model=self.model_id, prompt=prompt)
        # return response['response']
        pass
```

Then register it in load_models():

```python
def load_models() -> Dict[str, Any]:
    models = {}
    # Add your real models
    models["Llama-2-7B"] = OllamaModel(name="Llama-2-7B", model_id="llama2")
    models["Mistral-7B"] = OllamaModel(name="Mistral-7B", model_id="mistral")
    return models
```

Supported backends to consider:
- Ollama (ollama.ai) - Easy local LLM serving
- llama.cpp Python bindings - Direct GGUF model loading
- vLLM - High-throughput serving
- LocalAI - OpenAI-compatible local server
- text-generation-webui API

============================================================================
"""

from typing import Any, Dict

from ChatOS.config import MODEL_BEHAVIORS, NUM_COUNCIL_MODELS

from .dummy_model import DummyModel


def load_models() -> Dict[str, Any]:
    """
    Load available models into memory and return as a dict.
    
    Returns:
        Dictionary mapping model names to model instances.
        Each model must implement a `generate(prompt, mode)` method.
    """
    models: Dict[str, Any] = {}
    
    # Create a diverse council of dummy models
    # In production, replace with real LLM backends
    model_configs = [
        ("Atlas", "thoughtful", 0.7),
        ("Bolt", "concise", 0.5),
        ("Nova", "creative", 0.9),
        ("Logic", "analytical", 0.6),
    ]
    
    for i, (name, behavior, temp) in enumerate(model_configs[:NUM_COUNCIL_MODELS]):
        models[name] = DummyModel(
            name=name,
            behavior=behavior,
            temperature=temp,
        )
    
    # TODO: Add real model integrations here
    # Example for Ollama:
    # if OLLAMA_ENABLED:
    #     models["Llama2"] = OllamaModel(name="Llama2", model_id="llama2")
    
    return models


def get_model_info() -> list[dict]:
    """
    Get information about available models for the UI.
    
    Returns:
        List of dicts with model name, behavior, and description.
    """
    models = load_models()
    info = []
    
    for name, model in models.items():
        info.append({
            "name": name,
            "behavior": getattr(model, "behavior", "unknown"),
            "description": f"{name} - {getattr(model, 'behavior', 'standard').title()} responses",
        })
    
    return info

