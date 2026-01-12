"""
persrm_data_generator.py - Generate synthetic UI/UX training data for PersRM.

This module generates training examples across multiple categories:
- Component Analysis
- Layout Reasoning
- Code Generation
- Accessibility
- Design Tokens

Uses Ollama for generation and produces data in chat format for Unsloth training.
"""

import asyncio
import json
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx

from chatos_backend.config.settings import settings


# =============================================================================
# Data Categories and Templates
# =============================================================================

@dataclass
class DataCategory:
    """Configuration for a training data category."""
    name: str
    description: str
    system_prompt: str
    example_prompts: List[str]
    target_count: int = 200


# UI/UX Reasoning Categories
CATEGORIES: Dict[str, DataCategory] = {
    "component_analysis": DataCategory(
        name="Component Analysis",
        description="Analyze UI components for usability, accessibility, and best practices",
        system_prompt="""You are an expert UI/UX analyst specializing in component design. 
Analyze the given UI component and provide detailed reasoning about:
- Visual hierarchy and clarity
- Usability considerations
- Accessibility compliance
- Best practices alignment
- Suggested improvements

Be specific and actionable in your analysis.""",
        example_prompts=[
            "Analyze this button component: `<button class='btn-primary' onclick='submit()'>Submit</button>`. What UX improvements would you suggest?",
            "Review this form input: `<input type='text' placeholder='Enter email'>`. Is this following accessibility best practices?",
            "Evaluate this navigation menu component that uses a hamburger icon on desktop. What are the UX implications?",
            "Analyze a card component with image, title, description, and CTA button. What's the ideal visual hierarchy?",
            "Review this modal dialog that doesn't trap focus. What accessibility issues does this create?",
            "Evaluate a dropdown menu that opens on hover instead of click. What are the usability concerns?",
            "Analyze this tooltip that appears after a 2-second delay. Is this good UX?",
            "Review a search input without a visible search button. What usability issues might arise?",
            "Evaluate this toggle switch that doesn't indicate its current state clearly. How to improve?",
            "Analyze a progress indicator that only shows percentage without context. What's missing?",
        ],
        target_count=200,
    ),
    
    "layout_reasoning": DataCategory(
        name="Layout Reasoning",
        description="Reason about layout decisions, visual hierarchy, and responsive design",
        system_prompt="""You are an expert in UI layout design and visual hierarchy.
Analyze layout decisions and provide reasoning about:
- Visual flow and hierarchy
- Spacing and alignment
- Responsive behavior
- Content organization
- Grid and flexbox usage

Explain your reasoning clearly with specific recommendations.""",
        example_prompts=[
            "Explain the visual hierarchy for a dashboard with 4 KPI cards, a main chart, and a data table.",
            "How should a product listing page arrange filters, sorting, and product grid for optimal UX?",
            "What's the ideal layout for a settings page with 20+ options across 5 categories?",
            "Design the layout flow for a multi-step checkout process. What should be visible at each step?",
            "How should a blog post layout handle long-form content with images, code blocks, and callouts?",
            "Explain the layout considerations for a pricing comparison table with 4 tiers.",
            "What's the best approach for a responsive navigation that works from mobile to desktop?",
            "How should a file upload component layout change when multiple files are selected?",
            "Design the layout for an error state page (404) that helps users recover.",
            "What layout pattern works best for a notification center with different notification types?",
        ],
        target_count=200,
    ),
    
    "code_generation": DataCategory(
        name="Code Generation",
        description="Generate React/TypeScript UI components following best practices",
        system_prompt="""You are an expert React/TypeScript developer specializing in UI components.
Generate clean, accessible, and well-structured code that:
- Follows React best practices
- Uses TypeScript for type safety
- Includes proper accessibility attributes
- Uses modern CSS (Tailwind or CSS modules)
- Handles edge cases and loading states

Provide complete, production-ready code with comments explaining key decisions.""",
        example_prompts=[
            "Generate a React component for a responsive navbar with logo, links, and mobile menu.",
            "Create a form component with email and password validation following UX best practices.",
            "Build a reusable Button component with variants (primary, secondary, outline, ghost).",
            "Generate a Modal component with proper focus trapping and keyboard navigation.",
            "Create a DataTable component with sorting, filtering, and pagination.",
            "Build a Toast notification system with different severity levels.",
            "Generate an Accordion component that's keyboard accessible.",
            "Create a Tabs component with lazy loading of tab content.",
            "Build a Search component with debounced input and loading states.",
            "Generate a Skeleton loader component for different content types.",
        ],
        target_count=300,
    ),
    
    "accessibility": DataCategory(
        name="Accessibility",
        description="Identify and fix accessibility issues following WCAG guidelines",
        system_prompt="""You are an accessibility expert with deep knowledge of WCAG 2.1 guidelines.
Analyze components and provide:
- Specific WCAG violations identified
- Impact on users with different disabilities
- Concrete fixes with code examples
- Testing recommendations

Be thorough and reference specific WCAG criteria (e.g., 1.1.1, 2.1.1).""",
        example_prompts=[
            "Identify WCAG violations in this image: `<img src='chart.png'>`. How to fix them?",
            "Review this custom checkbox for accessibility: `<div class='checkbox' onclick='toggle()'>✓</div>`",
            "What accessibility issues exist in a carousel that auto-advances every 3 seconds?",
            "Analyze this color combination: #777 text on #fff background. Does it meet WCAG AA?",
            "Review a form that only uses color (red border) to indicate errors. What's wrong?",
            "Identify issues with this link: `<a onclick='navigate()'>Click here</a>`",
            "What's wrong with a video player that has no captions or transcripts?",
            "Review this skip link implementation: `<a href='#main' style='display:none'>Skip to main</a>`",
            "Analyze a data visualization (pie chart) that only uses color to differentiate segments.",
            "Review a drag-and-drop interface with no keyboard alternative. How to make it accessible?",
        ],
        target_count=150,
    ),
    
    "design_tokens": DataCategory(
        name="Design Tokens",
        description="Recommend design tokens, color systems, and spacing scales",
        system_prompt="""You are a design systems expert specializing in design tokens and systematic design.
Provide recommendations for:
- Color palettes with accessibility in mind
- Typography scales and hierarchy
- Spacing systems (4px, 8px base)
- Component-specific tokens
- Dark mode considerations

Explain the rationale behind each recommendation.""",
        example_prompts=[
            "Suggest a color palette for an enterprise dashboard. Include primary, secondary, and semantic colors.",
            "What spacing system should a component library use? Define the scale and usage guidelines.",
            "Create a typography scale for a content-heavy application. Include heading and body styles.",
            "Define the design tokens for a Button component (colors, sizes, states).",
            "Suggest a color palette that works for both light and dark themes.",
            "What border-radius tokens should a design system include? Define the scale.",
            "Create elevation/shadow tokens for a card-based interface.",
            "Define responsive breakpoint tokens for a mobile-first design system.",
            "Suggest animation/transition tokens for micro-interactions.",
            "Create a set of z-index tokens to manage layering consistently.",
        ],
        target_count=150,
    ),
}


# =============================================================================
# Generation Templates
# =============================================================================

# Additional prompt variations to expand the dataset
PROMPT_VARIATIONS = {
    "component_analysis": [
        "What are the UX issues with {component}?",
        "How can we improve the accessibility of {component}?",
        "Analyze the visual design of {component}.",
        "What best practices is {component} missing?",
        "Review {component} for mobile usability.",
        "Identify interaction issues in {component}.",
        "How does {component} handle edge cases?",
        "What loading states should {component} have?",
        "Review error handling in {component}.",
        "How can {component} be more intuitive?",
    ],
    "layout_reasoning": [
        "What's the best layout for {use_case}?",
        "How should {use_case} adapt to mobile?",
        "Explain the visual hierarchy for {use_case}.",
        "What grid system works for {use_case}?",
        "How to handle overflow in {use_case}?",
        "What spacing is appropriate for {use_case}?",
        "How should {use_case} handle empty states?",
        "Design the responsive breakpoints for {use_case}.",
        "What's the ideal content flow for {use_case}?",
        "How to maintain consistency in {use_case}?",
    ],
    "code_generation": [
        "Generate a {component} component in React.",
        "Create a TypeScript {component} with proper types.",
        "Build an accessible {component} component.",
        "Implement {component} with Tailwind CSS.",
        "Create a reusable {component} with variants.",
        "Generate {component} with loading and error states.",
        "Build {component} with keyboard navigation.",
        "Create {component} following atomic design.",
        "Implement {component} with proper ARIA attributes.",
        "Generate a performant {component} component.",
    ],
    "accessibility": [
        "What WCAG violations exist in {element}?",
        "How to make {element} screen reader friendly?",
        "Fix keyboard navigation in {element}.",
        "What ARIA attributes does {element} need?",
        "How to announce {element} changes to assistive tech?",
        "Review color contrast in {element}.",
        "Make {element} work without JavaScript.",
        "Add proper focus management to {element}.",
        "How to provide text alternatives for {element}?",
        "Review {element} for cognitive accessibility.",
    ],
    "design_tokens": [
        "Define color tokens for {context}.",
        "Create spacing tokens for {context}.",
        "Suggest typography tokens for {context}.",
        "Design elevation tokens for {context}.",
        "Create animation tokens for {context}.",
        "Define responsive tokens for {context}.",
        "Suggest border tokens for {context}.",
        "Create icon size tokens for {context}.",
        "Define opacity tokens for {context}.",
        "Create focus ring tokens for {context}.",
    ],
}

# Component/element variations for prompts
COMPONENTS = [
    "button", "input field", "dropdown", "modal", "card", "table",
    "navigation", "sidebar", "tabs", "accordion", "tooltip", "alert",
    "badge", "avatar", "breadcrumb", "pagination", "progress bar",
    "slider", "toggle", "checkbox", "radio button", "select",
    "autocomplete", "date picker", "file upload", "stepper",
]

USE_CASES = [
    "e-commerce product page", "dashboard analytics view", "user profile settings",
    "search results page", "checkout flow", "onboarding wizard",
    "email inbox", "calendar view", "kanban board", "chat interface",
    "file manager", "photo gallery", "news feed", "pricing page",
    "landing page hero section", "footer with sitemap", "login form",
    "registration flow", "password reset", "notification center",
]

CONTEXTS = [
    "SaaS dashboard", "e-commerce platform", "social media app",
    "enterprise software", "mobile app", "marketing website",
    "documentation site", "admin panel", "content management system",
    "healthcare portal", "financial application", "education platform",
]


# =============================================================================
# Data Generator
# =============================================================================

@dataclass
class GenerationStats:
    """Statistics for data generation run."""
    category: str
    generated: int = 0
    failed: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    @property
    def duration_seconds(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0


class PersRMDataGenerator:
    """Generate synthetic training data for PersRM fine-tuning."""
    
    def __init__(
        self,
        ollama_host: str = "http://localhost:11434",
        model: str = "qwen2.5:7b",
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize the data generator.
        
        Args:
            ollama_host: Ollama API host
            model: Model to use for generation
            output_dir: Directory to save generated data
        """
        self.ollama_host = ollama_host
        self.model = model
        self.output_dir = output_dir or (settings.memory_dir / "persrm_training_data")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.categories = CATEGORIES
        self.stats: Dict[str, GenerationStats] = {}
    
    async def _generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.8,
        max_tokens: int = 2048,
    ) -> Optional[str]:
        """Generate a completion using Ollama."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
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
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("message", {}).get("content", "")
                else:
                    print(f"Ollama error: {response.status_code}")
                    return None
                    
            except Exception as e:
                print(f"Generation error: {e}")
                return None
    
    def _create_training_example(
        self,
        system_prompt: str,
        user_prompt: str,
        assistant_response: str,
    ) -> Dict[str, Any]:
        """Create a training example in chat format."""
        return {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": assistant_response},
            ]
        }
    
    def _generate_prompt_variations(
        self,
        category_key: str,
        count: int,
    ) -> List[str]:
        """Generate varied prompts for a category."""
        prompts = []
        base_prompts = self.categories[category_key].example_prompts.copy()
        variations = PROMPT_VARIATIONS.get(category_key, [])
        
        # Add base prompts
        prompts.extend(base_prompts)
        
        # Generate variations
        while len(prompts) < count:
            if variations:
                template = random.choice(variations)
                
                if "{component}" in template:
                    component = random.choice(COMPONENTS)
                    prompt = template.format(component=component)
                elif "{use_case}" in template:
                    use_case = random.choice(USE_CASES)
                    prompt = template.format(use_case=use_case)
                elif "{context}" in template:
                    context = random.choice(CONTEXTS)
                    prompt = template.format(context=context)
                elif "{element}" in template:
                    element = random.choice(COMPONENTS)
                    prompt = template.format(element=element)
                else:
                    prompt = template
                
                prompts.append(prompt)
            else:
                # Cycle through base prompts with slight variations
                base = random.choice(base_prompts)
                prompts.append(base)
        
        return prompts[:count]
    
    async def generate_category(
        self,
        category_key: str,
        count: Optional[int] = None,
        progress_callback: Optional[callable] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate training examples for a specific category.
        
        Args:
            category_key: Category to generate for
            count: Number of examples (uses category default if not specified)
            progress_callback: Optional callback for progress updates
        
        Returns:
            List of training examples
        """
        category = self.categories[category_key]
        target_count = count or category.target_count
        
        self.stats[category_key] = GenerationStats(category=category_key)
        examples = []
        
        # Generate prompts
        prompts = self._generate_prompt_variations(category_key, target_count)
        
        print(f"\nGenerating {target_count} examples for {category.name}...")
        
        for i, prompt in enumerate(prompts):
            # Generate response
            response = await self._generate_completion(
                system_prompt=category.system_prompt,
                user_prompt=prompt,
            )
            
            if response:
                example = self._create_training_example(
                    system_prompt=category.system_prompt,
                    user_prompt=prompt,
                    assistant_response=response,
                )
                examples.append(example)
                self.stats[category_key].generated += 1
            else:
                self.stats[category_key].failed += 1
            
            # Progress update
            if progress_callback:
                progress_callback(i + 1, target_count, category_key)
            elif (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{target_count}")
            
            # Small delay to avoid overwhelming Ollama
            await asyncio.sleep(0.1)
        
        self.stats[category_key].end_time = datetime.now()
        
        return examples
    
    async def generate_all(
        self,
        progress_callback: Optional[callable] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Generate training data for all categories.
        
        Returns:
            Dict mapping category to list of examples
        """
        all_examples = {}
        
        for category_key in self.categories:
            examples = await self.generate_category(
                category_key,
                progress_callback=progress_callback,
            )
            all_examples[category_key] = examples
        
        return all_examples
    
    def save_to_jsonl(
        self,
        examples: List[Dict[str, Any]],
        filename: str,
    ) -> Path:
        """Save examples to JSONL file."""
        output_path = self.output_dir / filename
        
        with open(output_path, "w") as f:
            for example in examples:
                f.write(json.dumps(example) + "\n")
        
        return output_path
    
    def save_all_categories(
        self,
        all_examples: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Path]:
        """Save all category examples to separate files."""
        paths = {}
        all_combined = []
        
        for category_key, examples in all_examples.items():
            # Save category-specific file
            filename = f"persrm_{category_key}.jsonl"
            path = self.save_to_jsonl(examples, filename)
            paths[category_key] = path
            
            # Add to combined list
            all_combined.extend(examples)
        
        # Save combined file
        combined_path = self.save_to_jsonl(all_combined, "persrm_all_training.jsonl")
        paths["combined"] = combined_path
        
        return paths
    
    def get_stats_summary(self) -> Dict[str, Any]:
        """Get summary of generation statistics."""
        total_generated = sum(s.generated for s in self.stats.values())
        total_failed = sum(s.failed for s in self.stats.values())
        total_duration = sum(s.duration_seconds for s in self.stats.values())
        
        return {
            "total_generated": total_generated,
            "total_failed": total_failed,
            "total_duration_seconds": total_duration,
            "categories": {
                key: {
                    "generated": stats.generated,
                    "failed": stats.failed,
                    "duration_seconds": stats.duration_seconds,
                }
                for key, stats in self.stats.items()
            },
        }


# =============================================================================
# Quick Generation Functions
# =============================================================================

async def generate_training_data(
    categories: Optional[List[str]] = None,
    count_per_category: Optional[int] = None,
    model: str = "qwen2.5:7b",
    output_dir: Optional[Path] = None,
) -> Tuple[int, Dict[str, Path]]:
    """
    Generate PersRM training data.
    
    Args:
        categories: List of categories to generate (None for all)
        count_per_category: Override count per category
        model: Ollama model to use
        output_dir: Output directory
    
    Returns:
        Tuple of (total_count, paths_dict)
    """
    generator = PersRMDataGenerator(model=model, output_dir=output_dir)
    
    if categories:
        all_examples = {}
        for cat in categories:
            if cat in generator.categories:
                examples = await generator.generate_category(cat, count_per_category)
                all_examples[cat] = examples
    else:
        all_examples = await generator.generate_all()
    
    paths = generator.save_all_categories(all_examples)
    stats = generator.get_stats_summary()
    
    return stats["total_generated"], paths


def get_available_categories() -> List[Dict[str, Any]]:
    """Get list of available generation categories."""
    return [
        {
            "key": key,
            "name": cat.name,
            "description": cat.description,
            "target_count": cat.target_count,
        }
        for key, cat in CATEGORIES.items()
    ]


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate PersRM training data")
    parser.add_argument("--category", type=str, help="Specific category to generate")
    parser.add_argument("--count", type=int, help="Number of examples per category")
    parser.add_argument("--model", type=str, default="qwen2.5:7b", help="Ollama model")
    parser.add_argument("--output", type=str, help="Output directory")
    
    args = parser.parse_args()
    
    categories = [args.category] if args.category else None
    output_dir = Path(args.output) if args.output else None
    
    total, paths = asyncio.run(generate_training_data(
        categories=categories,
        count_per_category=args.count,
        model=args.model,
        output_dir=output_dir,
    ))
    
    print(f"\nGenerated {total} examples")
    print("Output files:")
    for name, path in paths.items():
        print(f"  {name}: {path}")

