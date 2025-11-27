"""
Dummy language model implementations.

ChatOS uses these dummy models to demonstrate how multiple
independent models can be orchestrated together. Each dummy
model exposes a `generate` method that returns a response based
on the supplied prompt and mode.

In production, you would replace these with real LLM backends.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class DummyModel:
    """
    A simplistic language model that simulates different response styles.
    
    Each model has a unique personality/behavior that affects its responses.
    This demonstrates how multiple models with different strengths can be
    combined in a council for better overall responses.
    
    Attributes:
        name: Display name for the model
        behavior: Response style - affects how the model "thinks"
        temperature: Simulated randomness (0.0-1.0)
    """

    name: str
    behavior: Literal["thoughtful", "concise", "creative", "analytical"] = "thoughtful"
    temperature: float = field(default=0.7)

    # Response templates for different behaviors
    _BEHAVIOR_TEMPLATES: dict = field(default_factory=lambda: {
        "thoughtful": [
            "Let me think about this carefully... {response}",
            "After consideration, I believe {response}",
            "This is an interesting question. {response}",
        ],
        "concise": [
            "{response}",
            "Simply put: {response}",
            "In brief: {response}",
        ],
        "creative": [
            "Here's an interesting perspective: {response}",
            "Thinking outside the box... {response}",
            "What if we consider... {response}",
        ],
        "analytical": [
            "Analyzing the components: {response}",
            "Breaking this down: {response}",
            "From a logical standpoint: {response}",
        ],
    }, repr=False)

    def generate(self, prompt: str, mode: str = "normal") -> str:
        """
        Generate a response for the given prompt and mode.

        Args:
            prompt: The full prompt including context and user message
            mode: Either "normal" or "code" - affects response format

        Returns:
            A generated response string
        """
        if mode == "code":
            return self._generate_code_response(prompt)
        return self._generate_normal_response(prompt)

    def _generate_code_response(self, prompt: str) -> str:
        """Generate a code-focused response."""
        # Extract what seems to be the request from the prompt
        lines = prompt.strip().split("\n")
        user_msg = lines[-1] if lines else prompt
        
        # Remove "User: " prefix if present
        if user_msg.startswith("User:"):
            user_msg = user_msg[5:].strip()

        code_templates = {
            "thoughtful": '''# {name}'s careful implementation
# Request: {request}

def solution():
    """
    A well-considered solution to the problem.
    """
    # Implementation here
    result = "Hello from {name}"
    return result

# Example usage
if __name__ == "__main__":
    print(solution())
''',
            "concise": '''# {name} - minimal solution
def main():
    return "{request}"
''',
            "creative": '''# {name}'s creative approach 🎨
# Thinking differently about: {request}

class CreativeSolution:
    """An unconventional but effective solution."""
    
    def __init__(self):
        self.answer = "Creatively solved by {name}"
    
    def execute(self):
        return self.answer

# Let's make something interesting!
solution = CreativeSolution()
print(solution.execute())
''',
            "analytical": '''# {name} - Analytical breakdown
# Problem: {request}
# Components identified:
# 1. Input processing
# 2. Logic execution  
# 3. Output formatting

def analyze_and_solve(input_data: str) -> str:
    """
    Methodically solve the problem through analysis.
    
    Args:
        input_data: The problem statement
        
    Returns:
        Analyzed solution
    """
    # Step 1: Parse input
    parsed = input_data.strip()
    
    # Step 2: Apply logic
    result = f"Analyzed by {name}: {{parsed}}"
    
    # Step 3: Format output
    return result

# Execute analysis
print(analyze_and_solve("{request}"))
''',
        }

        template = code_templates.get(self.behavior, code_templates["thoughtful"])
        return template.format(name=self.name, request=user_msg[:50])

    def _generate_normal_response(self, prompt: str) -> str:
        """Generate a normal conversational response."""
        lines = prompt.strip().split("\n")
        user_msg = lines[-1] if lines else prompt
        
        if user_msg.startswith("User:"):
            user_msg = user_msg[5:].strip()

        # Simulate different response lengths based on behavior
        responses = {
            "thoughtful": f"I've carefully considered your message about '{user_msg[:30]}...'. This is a thoughtful response from {self.name}, taking into account various perspectives and nuances of your question.",
            "concise": f"Re: '{user_msg[:20]}...' - Quick answer from {self.name}.",
            "creative": f"Ooh, interesting! '{user_msg[:25]}...' makes me think of something unique. Here's my creative take from {self.name}: imagine the possibilities!",
            "analytical": f"Analyzing '{user_msg[:25]}...': Breaking this down systematically. Point 1: Context noted. Point 2: Key elements identified. Point 3: Conclusion from {self.name}.",
        }

        base_response = responses.get(self.behavior, f"Response from {self.name}")
        
        # Apply template
        templates = self._BEHAVIOR_TEMPLATES.get(self.behavior, ["{response}"])
        template = random.choice(templates)
        
        return template.format(response=base_response)

    def __repr__(self) -> str:
        return f"DummyModel(name='{self.name}', behavior='{self.behavior}')"

