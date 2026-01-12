"""
data_generator.py - Generate targeted training data for knowledge gaps.

Uses Ollama to generate synthetic training examples for domains
that have insufficient coverage.
"""

import asyncio
import hashlib
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

from chatos_backend.config.settings import settings
from chatos_backend.database.connection import DatabaseSession
from chatos_backend.database.models import (
    ActiveLearningTask,
    DataSource,
    DifficultyLevel,
    ExampleStatus,
    KnowledgeDomain,
    SourceType,
    TaskStatus,
    TaskType,
    TrainingExample,
)


# =============================================================================
# Generation Templates
# =============================================================================

DOMAIN_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "python": {
        "system_prompt": "You are an expert Python developer and instructor.",
        "prompt_templates": [
            "Explain how to {topic} in Python with code examples.",
            "What is the best way to {topic} in Python?",
            "Write a Python function that {topic}.",
            "Debug this Python code: {code_snippet}",
            "Optimize this Python code for better performance: {code_snippet}",
        ],
        "topics": [
            "handle exceptions", "work with files", "use list comprehensions",
            "implement decorators", "use context managers", "work with async/await",
            "create classes and objects", "use type hints", "test with pytest",
            "manage dependencies with pip", "use virtual environments",
        ],
    },
    "javascript": {
        "system_prompt": "You are an expert JavaScript/TypeScript developer.",
        "prompt_templates": [
            "Explain how to {topic} in JavaScript.",
            "What is the modern way to {topic} in JavaScript?",
            "Write a function that {topic} using ES6+ features.",
            "Convert this callback-based code to async/await: {code_snippet}",
        ],
        "topics": [
            "handle promises", "use array methods", "work with the DOM",
            "implement event handling", "use destructuring", "work with modules",
            "handle errors properly", "use closures effectively",
        ],
    },
    "react": {
        "system_prompt": "You are an expert React developer specializing in modern React patterns.",
        "prompt_templates": [
            "How do I {topic} in React?",
            "Create a React component that {topic}.",
            "Explain the best practices for {topic} in React.",
            "Refactor this React component to use hooks: {code_snippet}",
        ],
        "topics": [
            "manage state with useState", "handle side effects with useEffect",
            "create custom hooks", "implement context for state management",
            "optimize performance with useMemo", "handle forms",
            "implement routing", "test components with React Testing Library",
        ],
    },
    "ui_components": {
        "system_prompt": "You are an expert UI/UX designer and developer specializing in component design.",
        "prompt_templates": [
            "Design a {component} component with proper accessibility.",
            "What are the UX best practices for a {component}?",
            "How should a {component} handle different states (loading, error, empty)?",
            "Create an accessible {component} with ARIA attributes.",
        ],
        "topics": [
            "button", "form input", "modal dialog", "dropdown menu",
            "navigation bar", "card", "table", "tabs", "accordion",
            "tooltip", "toast notification", "progress indicator",
        ],
    },
    "accessibility": {
        "system_prompt": "You are an accessibility expert with deep knowledge of WCAG guidelines.",
        "prompt_templates": [
            "How do I make a {component} accessible?",
            "What WCAG guidelines apply to {component}?",
            "Audit this code for accessibility issues: {code_snippet}",
            "What ARIA attributes should a {component} have?",
        ],
        "topics": [
            "modal", "dropdown", "form", "navigation", "data table",
            "image carousel", "video player", "search autocomplete",
        ],
    },
    "layout": {
        "system_prompt": "You are an expert in CSS layout and responsive design.",
        "prompt_templates": [
            "How do I create a {layout_type} layout with CSS?",
            "What's the best approach for {layout_type} responsive design?",
            "Implement a {layout_type} using CSS Grid/Flexbox.",
        ],
        "topics": [
            "two-column", "sidebar", "masonry", "card grid",
            "sticky header", "footer at bottom", "centered content",
        ],
    },
    "reasoning": {
        "system_prompt": "You are a logical reasoning expert. Provide step-by-step analysis.",
        "prompt_templates": [
            "Analyze this problem step by step: {problem}",
            "What is the logical approach to {problem}?",
            "Break down this complex problem: {problem}",
        ],
        "topics": [
            "debugging a performance issue", "designing a system architecture",
            "choosing between technologies", "optimizing a database query",
            "refactoring legacy code", "implementing a caching strategy",
        ],
    },
    "conversation": {
        "system_prompt": "You are a helpful AI assistant.",
        "prompt_templates": [
            "Help me understand {topic}.",
            "Can you explain {topic} in simple terms?",
            "What should I know about {topic}?",
        ],
        "topics": [
            "machine learning basics", "cloud computing", "API design",
            "version control with Git", "containerization with Docker",
            "CI/CD pipelines", "microservices architecture",
        ],
    },
    "instruction_following": {
        "system_prompt": "You are a helpful assistant that follows instructions precisely.",
        "prompt_templates": [
            "Write a {artifact_type} that {requirement}.",
            "Create a {artifact_type} with the following specifications: {specs}",
            "Generate a {artifact_type} for {use_case}.",
        ],
        "topics": [
            "README file", "API documentation", "code review checklist",
            "project proposal", "technical specification", "user guide",
        ],
    },
}


@dataclass
class GeneratedExample:
    """A generated training example."""
    user_input: str
    assistant_output: str
    domain_name: str
    difficulty: str
    generation_method: str


class TargetedDataGenerator:
    """
    Generate targeted training data for knowledge gaps.
    
    Uses Ollama to create synthetic training examples for domains
    that need more data.
    """
    
    def __init__(
        self,
        ollama_host: Optional[str] = None,
        model: str = "qwen2.5:7b",
    ):
        """
        Initialize the generator.
        
        Args:
            ollama_host: Ollama API host
            model: Model to use for generation
        """
        self.ollama_host = ollama_host or settings.ollama_host
        self.model = model
        self._source_id: Optional[int] = None
    
    def _ensure_source(self) -> int:
        """Get or create the synthetic data source."""
        if self._source_id:
            return self._source_id
        
        with DatabaseSession() as db:
            source = db.query(DataSource).filter(
                DataSource.name == "synthetic_active_learning"
            ).first()
            
            if not source:
                source = DataSource(
                    name="synthetic_active_learning",
                    source_type=SourceType.SYNTHETIC,
                    description="Synthetically generated data from active learning",
                    config={"generator": "ollama", "model": self.model},
                    is_active=True,
                )
                db.add(source)
                db.flush()
            
            self._source_id = source.id
        
        return self._source_id
    
    def _get_domain_config(self, domain_name: str) -> Dict[str, Any]:
        """Get generation config for a domain."""
        return DOMAIN_TEMPLATES.get(domain_name, DOMAIN_TEMPLATES["instruction_following"])
    
    def _generate_prompt(self, domain_name: str) -> Tuple[str, str]:
        """
        Generate a random prompt for a domain.
        
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        config = self._get_domain_config(domain_name)
        
        system_prompt = config["system_prompt"]
        template = random.choice(config["prompt_templates"])
        
        # Fill in template
        if "{topic}" in template:
            topic = random.choice(config.get("topics", ["this topic"]))
            user_prompt = template.format(topic=topic)
        elif "{component}" in template:
            component = random.choice(config.get("topics", ["component"]))
            user_prompt = template.format(component=component)
        elif "{layout_type}" in template:
            layout = random.choice(config.get("topics", ["responsive"]))
            user_prompt = template.format(layout_type=layout)
        elif "{problem}" in template:
            problem = random.choice(config.get("topics", ["complex problem"]))
            user_prompt = template.format(problem=problem)
        elif "{artifact_type}" in template:
            artifact = random.choice(config.get("topics", ["document"]))
            user_prompt = template.format(
                artifact_type=artifact,
                requirement="meets best practices",
                specs="standard format",
                use_case="general use",
            )
        elif "{code_snippet}" in template:
            # Generate a simple code snippet request
            user_prompt = template.format(code_snippet="[provide your code here]")
        else:
            user_prompt = template
        
        return system_prompt, user_prompt
    
    async def generate_example(
        self,
        domain_name: str,
        difficulty: DifficultyLevel = DifficultyLevel.INTERMEDIATE,
    ) -> Optional[GeneratedExample]:
        """
        Generate a single training example for a domain.
        
        Args:
            domain_name: Target knowledge domain
            difficulty: Difficulty level
        
        Returns:
            GeneratedExample or None if generation failed
        """
        system_prompt, user_prompt = self._generate_prompt(domain_name)
        
        # Adjust prompt based on difficulty
        if difficulty == DifficultyLevel.BASIC:
            user_prompt = f"(Beginner level) {user_prompt}"
        elif difficulty == DifficultyLevel.ADVANCED:
            user_prompt = f"(Advanced) {user_prompt}"
        elif difficulty == DifficultyLevel.EXPERT:
            user_prompt = f"(Expert level, detailed) {user_prompt}"
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.ollama_host}/api/chat",
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": False,
                        "options": {
                            "temperature": 0.8,
                            "num_predict": 2000,
                        },
                    },
                )
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                assistant_output = data.get("message", {}).get("content", "")
                
                if not assistant_output or len(assistant_output) < 50:
                    return None
                
                return GeneratedExample(
                    user_input=user_prompt,
                    assistant_output=assistant_output,
                    domain_name=domain_name,
                    difficulty=difficulty.value,
                    generation_method="ollama_targeted",
                )
                
        except Exception as e:
            print(f"Generation error: {e}")
            return None
    
    async def generate_batch(
        self,
        domain_name: str,
        count: int = 10,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[int, int]:
        """
        Generate a batch of examples for a domain.
        
        Args:
            domain_name: Target domain
            count: Number of examples to generate
            progress_callback: Optional progress callback
        
        Returns:
            Tuple of (generated, failed)
        """
        source_id = self._ensure_source()
        
        # Get domain ID
        with DatabaseSession() as db:
            domain = db.query(KnowledgeDomain).filter(
                KnowledgeDomain.name == domain_name
            ).first()
            domain_id = domain.id if domain else None
        
        generated = 0
        failed = 0
        
        # Distribute across difficulty levels
        difficulties = [
            DifficultyLevel.BASIC,
            DifficultyLevel.INTERMEDIATE,
            DifficultyLevel.INTERMEDIATE,
            DifficultyLevel.ADVANCED,
        ]
        
        for i in range(count):
            difficulty = difficulties[i % len(difficulties)]
            
            example = await self.generate_example(domain_name, difficulty)
            
            if example:
                # Save to database
                saved = self._save_example(example, source_id, domain_id)
                if saved:
                    generated += 1
                else:
                    failed += 1
            else:
                failed += 1
            
            if progress_callback:
                progress_callback(i + 1, count)
            
            # Small delay
            await asyncio.sleep(0.5)
        
        # Update source stats
        with DatabaseSession() as db:
            source = db.query(DataSource).filter(DataSource.id == source_id).first()
            if source:
                source.total_examples = (source.total_examples or 0) + generated
                source.last_sync_at = datetime.utcnow()
        
        return generated, failed
    
    def _save_example(
        self,
        example: GeneratedExample,
        source_id: int,
        domain_id: Optional[int],
    ) -> bool:
        """Save a generated example to the database."""
        content_hash = hashlib.sha256(
            f"{example.user_input}|||{example.assistant_output}".encode()
        ).hexdigest()
        
        difficulty_map = {
            "basic": DifficultyLevel.BASIC,
            "intermediate": DifficultyLevel.INTERMEDIATE,
            "advanced": DifficultyLevel.ADVANCED,
            "expert": DifficultyLevel.EXPERT,
        }
        
        with DatabaseSession() as db:
            # Check for duplicate
            existing = db.query(TrainingExample).filter(
                TrainingExample.content_hash == content_hash
            ).first()
            
            if existing:
                return False
            
            # Get system prompt
            config = self._get_domain_config(example.domain_name)
            
            training_example = TrainingExample(
                source_id=source_id,
                external_id=f"gen_{content_hash[:16]}",
                system_prompt=config["system_prompt"],
                user_input=example.user_input,
                assistant_output=example.assistant_output,
                domain_id=domain_id,
                difficulty=difficulty_map.get(example.difficulty, DifficultyLevel.INTERMEDIATE),
                quality_score=0.7,  # Default for synthetic
                status=ExampleStatus.PENDING,  # Needs review
                content_hash=content_hash,
                extra_data={
                    "generation_method": example.generation_method,
                    "model": self.model,
                    "generated_at": datetime.utcnow().isoformat(),
                },
            )
            db.add(training_example)
        
        return True
    
    async def fill_gap(
        self,
        domain_name: str,
        target_count: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, Any]:
        """
        Generate examples to fill a knowledge gap.
        
        Args:
            domain_name: Domain with gap
            target_count: Number to generate (auto-calculated if None)
            progress_callback: Optional progress callback
        
        Returns:
            Dict with generation results
        """
        # Calculate how many we need
        with DatabaseSession() as db:
            domain = db.query(KnowledgeDomain).filter(
                KnowledgeDomain.name == domain_name
            ).first()
            
            if not domain:
                return {"error": f"Domain '{domain_name}' not found"}
            
            current_count = db.query(TrainingExample).filter(
                TrainingExample.domain_id == domain.id,
                TrainingExample.status == ExampleStatus.PROCESSED,
            ).count()
            
            if target_count is None:
                # Generate enough to reach minimum
                needed = max(0, domain.min_examples_required - current_count)
                target_count = min(needed, 50)  # Cap at 50 per run
        
        if target_count <= 0:
            return {
                "domain": domain_name,
                "generated": 0,
                "message": "Domain has sufficient examples",
            }
        
        print(f"Generating {target_count} examples for {domain_name}...")
        
        generated, failed = await self.generate_batch(
            domain_name,
            target_count,
            progress_callback,
        )
        
        return {
            "domain": domain_name,
            "generated": generated,
            "failed": failed,
            "target": target_count,
            "success_rate": round(generated / target_count if target_count > 0 else 0, 3),
        }
    
    def create_task(
        self,
        domain_name: str,
        target_count: int = 20,
    ) -> int:
        """
        Create an active learning task for data generation.
        
        Args:
            domain_name: Target domain
            target_count: Examples to generate
        
        Returns:
            Task ID
        """
        with DatabaseSession() as db:
            domain = db.query(KnowledgeDomain).filter(
                KnowledgeDomain.name == domain_name
            ).first()
            
            task = ActiveLearningTask(
                task_type=TaskType.GAP_FILL,
                status=TaskStatus.PENDING,
                target_domain_id=domain.id if domain else None,
                target_count=target_count,
                config={
                    "domain_name": domain_name,
                    "model": self.model,
                },
            )
            db.add(task)
            db.flush()
            
            return task.id


# =============================================================================
# Convenience Functions
# =============================================================================

async def generate_for_gap(
    domain_name: str,
    count: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Dict[str, Any]:
    """
    Generate training data to fill a knowledge gap.
    
    Args:
        domain_name: Domain to generate for
        count: Number of examples (auto if None)
        progress_callback: Optional callback
    
    Returns:
        Generation results
    """
    generator = TargetedDataGenerator()
    return await generator.fill_gap(domain_name, count, progress_callback)


async def generate_batch(
    domain_name: str,
    count: int = 10,
    progress_callback: Optional[Callable[[int, int], None]] = None,
) -> Tuple[int, int]:
    """
    Generate a batch of examples.
    
    Returns:
        Tuple of (generated, failed)
    """
    generator = TargetedDataGenerator()
    return await generator.generate_batch(domain_name, count, progress_callback)


def get_available_domains() -> List[str]:
    """Get list of domains with generation templates."""
    return list(DOMAIN_TEMPLATES.keys())

