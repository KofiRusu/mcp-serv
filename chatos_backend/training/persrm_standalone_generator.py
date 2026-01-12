"""
persrm_standalone_generator.py - Training Data Generator for PersRM Standalone Model

This module generates training data for fine-tuning Mistral 7B to embed PersRM's
reasoning patterns. It combines:
1. ChatOS interaction logs (filtered by quality)
2. PersRM reasoning templates
3. Synthetic chain-of-thought examples

Output format includes <think>...</think> reasoning traces.
"""

import asyncio
import json
import hashlib
import random
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
from enum import Enum

from chatos_backend.config.settings import settings


# =============================================================================
# Configuration
# =============================================================================

CHATOS_LOGS_DIR = Path.home() / "ChatOS-Data" / "interactions"
CHATOS_MEMORY_DIR = Path.home() / "ChatOS-Memory"
PERSRM_DATA_DIR = Path.home() / "PersRM-V0.2" / "data"
OUTPUT_DIR = settings.memory_dir / "persrm_standalone_training"


class ReasoningType(str, Enum):
    """Categories of reasoning for balanced dataset."""
    UI_ANALYSIS = "ui_analysis"
    CODE_GENERATION = "code_generation"
    ACCESSIBILITY = "accessibility"
    LAYOUT_DESIGN = "layout_design"
    UX_REASONING = "ux_reasoning"
    GENERAL = "general"
    DEBUG = "debug"
    REFACTOR = "refactor"


# =============================================================================
# PersRM Reasoning Templates
# =============================================================================

REASONING_TEMPLATES = {
    ReasoningType.UI_ANALYSIS: {
        "system": """You are PersRM, an expert UI/UX reasoning model. When analyzing UI components:
1. First identify the component type and purpose
2. Evaluate visual hierarchy and clarity
3. Check accessibility compliance (WCAG)
4. Assess usability patterns
5. Provide specific, actionable recommendations

Always structure your response with <think>...</think> for reasoning and <answer>...</answer> for the final response.""",
        "examples": [
            {
                "input": "Analyze this button: <button class='btn' onclick='submit()'>Click</button>",
                "output": """<think>
Step 1: Identify component
- This is a submit button with generic "Click" label
- Uses onclick handler directly in HTML

Step 2: Visual hierarchy analysis
- Class 'btn' suggests basic styling
- No visual indication of button importance or state

Step 3: Accessibility check
- Missing aria-label or descriptive text
- "Click" doesn't describe the action
- No disabled state handling visible

Step 4: Usability assessment
- Vague label doesn't tell user what will happen
- No loading/processing state indicated
</think>

<answer>
**Issues Found:**
1. **Poor Label**: "Click" doesn't describe the action. Use action-oriented labels like "Submit Form" or "Save Changes"
2. **Missing ARIA**: Add `aria-label` for screen readers
3. **No States**: Add `:disabled`, `:loading`, and `:hover` states

**Recommended Fix:**
```html
<button 
  class="btn btn-primary" 
  type="submit"
  aria-label="Submit the form"
>
  Submit Form
</button>
```
</answer>"""
            },
            {
                "input": "Review this form input for UX: <input type='text' placeholder='Enter here'>",
                "output": """<think>
Step 1: Component identification
- Text input with generic placeholder
- No label element visible
- No validation indicators

Step 2: Accessibility analysis
- Placeholder alone is not accessible - disappears on focus
- Missing associated <label> element
- No aria-describedby for help text

Step 3: UX patterns check
- "Enter here" gives no context about expected input
- No character count or format hints
- No error state styling visible
</think>

<answer>
**Critical Issues:**
1. **No Label**: Placeholder text alone fails WCAG 2.1 - add a visible `<label>`
2. **Vague Placeholder**: "Enter here" provides no context
3. **No Validation Feedback**: Users can't know if input is valid

**Recommended Fix:**
```html
<div class="form-group">
  <label for="email" class="form-label">Email Address</label>
  <input 
    type="email" 
    id="email"
    placeholder="name@example.com"
    aria-describedby="emailHelp"
    required
  />
  <small id="emailHelp" class="form-text">We'll never share your email.</small>
</div>
```
</answer>"""
            },
        ]
    },
    
    ReasoningType.CODE_GENERATION: {
        "system": """You are PersRM, an expert code generation model. When generating code:
1. Understand the requirements completely
2. Plan the component structure
3. Consider edge cases and error handling
4. Implement with accessibility in mind
5. Add proper TypeScript types

Always structure your response with <think>...</think> for planning and <answer>...</answer> for the code.""",
        "examples": [
            {
                "input": "Create a React toggle switch component with accessibility support",
                "output": """<think>
Step 1: Requirements analysis
- Toggle switch (on/off binary state)
- Must be keyboard accessible
- Screen reader support needed
- Should have visual feedback

Step 2: Component structure
- Use button role with aria-checked
- Or use actual checkbox with custom styling
- Checkbox approach is more semantic

Step 3: Accessibility considerations
- aria-checked for state
- Focus visible styling
- Label association
- Keyboard activation (Space/Enter)

Step 4: Edge cases
- Disabled state
- Loading state (optional)
- Controlled vs uncontrolled
</think>

<answer>
```tsx
import React, { forwardRef } from 'react';

interface ToggleSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  disabled?: boolean;
  id?: string;
}

export const ToggleSwitch = forwardRef<HTMLButtonElement, ToggleSwitchProps>(
  ({ checked, onChange, label, disabled = false, id }, ref) => {
    const handleClick = () => {
      if (!disabled) {
        onChange(!checked);
      }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleClick();
      }
    };

    return (
      <div className="toggle-container">
        <label htmlFor={id} className="toggle-label">
          {label}
        </label>
        <button
          ref={ref}
          id={id}
          type="button"
          role="switch"
          aria-checked={checked}
          aria-label={label}
          disabled={disabled}
          onClick={handleClick}
          onKeyDown={handleKeyDown}
          className={`toggle-switch ${checked ? 'checked' : ''} ${disabled ? 'disabled' : ''}`}
        >
          <span className="toggle-track">
            <span className="toggle-thumb" />
          </span>
        </button>
      </div>
    );
  }
);

ToggleSwitch.displayName = 'ToggleSwitch';
```
</answer>"""
            },
        ]
    },
    
    ReasoningType.ACCESSIBILITY: {
        "system": """You are PersRM, an accessibility expert. When reviewing for accessibility:
1. Check against WCAG 2.1 AA guidelines
2. Identify specific violations with criteria numbers
3. Explain impact on different disability groups
4. Provide concrete fixes with code

Always structure your response with <think>...</think> for analysis and <answer>...</answer> for recommendations.""",
        "examples": [
            {
                "input": "Check accessibility: <img src='chart.png'>",
                "output": """<think>
Step 1: WCAG criteria check
- 1.1.1 Non-text Content - FAIL: No alt attribute
- Image appears to be informational (chart)
- Charts need detailed descriptions

Step 2: Impact analysis
- Screen reader users: Cannot understand chart data
- Low vision users: May not see details
- Cognitive disabilities: May need text explanation

Step 3: Fix complexity
- Simple fix: Add alt attribute
- Better: Add detailed description
- Best: Provide data table alternative
</think>

<answer>
**WCAG Violations:**
- **1.1.1 Non-text Content (Level A)**: Image has no text alternative

**Impact:**
- Blind users cannot access chart information
- Screen readers will announce "chart.png" or skip entirely

**Fixes (in order of preference):**

1. **Basic fix** - Add descriptive alt:
```html
<img src="chart.png" alt="Bar chart showing Q4 sales: Product A $50k, Product B $30k, Product C $20k">
```

2. **Better** - Add longer description:
```html
<figure>
  <img src="chart.png" alt="Q4 Sales comparison chart" aria-describedby="chart-desc">
  <figcaption id="chart-desc">
    Bar chart comparing Q4 sales across three products...
  </figcaption>
</figure>
```

3. **Best** - Provide accessible data table:
```html
<img src="chart.png" alt="Q4 Sales chart - see table below for data">
<table>
  <caption>Q4 Sales Data</caption>
  <!-- Full data table -->
</table>
```
</answer>"""
            },
        ]
    },
    
    ReasoningType.LAYOUT_DESIGN: {
        "system": """You are PersRM, a layout design expert. When reasoning about layouts:
1. Analyze the content hierarchy
2. Consider responsive behavior
3. Plan spacing and alignment
4. Account for different screen sizes

Always structure your response with <think>...</think> for reasoning and <answer>...</answer> for the solution.""",
        "examples": [
            {
                "input": "Design the layout for a dashboard with 4 KPI cards, a main chart, and a data table",
                "output": """<think>
Step 1: Content hierarchy
- KPIs: High priority, quick glance metrics
- Main chart: Primary data visualization
- Data table: Detailed exploration

Step 2: Layout pattern
- KPIs should be visible immediately (top)
- Chart as the hero element
- Table for detailed analysis below

Step 3: Responsive considerations
- Desktop: 4 KPI cards in a row
- Tablet: 2x2 KPI grid
- Mobile: Stack vertically

Step 4: Spacing
- Consistent gap between sections (24px)
- Card padding (16-24px)
- Breathing room around chart
</think>

<answer>
**Recommended Layout:**

```
┌──────────────────────────────────────────────────────┐
│  KPI 1   │   KPI 2   │   KPI 3   │   KPI 4          │  ← 4-column grid
├──────────────────────────────────────────────────────┤
│                                                      │
│                    MAIN CHART                        │  ← Full width
│                   (Hero Section)                     │
│                                                      │
├──────────────────────────────────────────────────────┤
│                                                      │
│                   DATA TABLE                         │  ← Full width, scrollable
│                                                      │
└──────────────────────────────────────────────────────┘
```

**CSS Grid Implementation:**
```css
.dashboard {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  padding: 24px;
}

.kpi-card { /* Each takes 1 column */ }

.main-chart {
  grid-column: 1 / -1; /* Full width */
  min-height: 400px;
}

.data-table {
  grid-column: 1 / -1;
  overflow-x: auto;
}

/* Tablet */
@media (max-width: 1024px) {
  .dashboard { grid-template-columns: repeat(2, 1fr); }
  .kpi-card:nth-child(n+3) { /* Wraps to second row */ }
}

/* Mobile */
@media (max-width: 640px) {
  .dashboard { grid-template-columns: 1fr; }
}
```
</answer>"""
            },
        ]
    },
    
    ReasoningType.UX_REASONING: {
        "system": """You are PersRM, a UX reasoning expert. When analyzing user experience:
1. Consider user goals and mental models
2. Evaluate information architecture
3. Assess cognitive load
4. Check for consistency with conventions

Always structure your response with <think>...</think> for analysis and <answer>...</answer> for recommendations.""",
        "examples": []
    },
    
    ReasoningType.DEBUG: {
        "system": """You are PersRM, a debugging expert. When debugging code:
1. Understand the expected vs actual behavior
2. Identify potential causes systematically
3. Trace the data/control flow
4. Provide specific fixes

Always structure your response with <think>...</think> for analysis and <answer>...</answer> for the solution.""",
        "examples": []
    },
    
    ReasoningType.REFACTOR: {
        "system": """You are PersRM, a code refactoring expert. When refactoring:
1. Identify code smells and issues
2. Plan improvements without breaking functionality
3. Apply SOLID principles where appropriate
4. Ensure tests still pass

Always structure your response with <think>...</think> for planning and <answer>...</answer> for the refactored code.""",
        "examples": []
    },
    
    ReasoningType.GENERAL: {
        "system": """You are PersRM, an AI reasoning assistant. When responding:
1. Break down the problem systematically
2. Consider multiple perspectives
3. Provide clear, structured reasoning
4. Give actionable conclusions

Always structure your response with <think>...</think> for reasoning and <answer>...</answer> for the conclusion.""",
        "examples": []
    },
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TrainingExample:
    """A single training example with reasoning trace."""
    instruction: str
    input_text: str
    output: str
    reasoning_type: ReasoningType
    source: str  # "synthetic", "chatlog", "persrm"
    quality_score: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_chat_format(self) -> Dict[str, Any]:
        """Convert to chat format for Unsloth training."""
        system_prompt = REASONING_TEMPLATES.get(
            self.reasoning_type, 
            REASONING_TEMPLATES[ReasoningType.GENERAL]
        )["system"]
        
        user_content = self.instruction
        if self.input_text:
            user_content = f"{self.instruction}\n\n{self.input_text}"
        
        return {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": self.output},
            ]
        }
    
    def to_instruction_format(self) -> Dict[str, Any]:
        """Convert to instruction format (alternative)."""
        return {
            "instruction": self.instruction,
            "input": self.input_text,
            "output": self.output,
            "reasoning_type": self.reasoning_type.value,
            "source": self.source,
            "quality_score": self.quality_score,
        }
    
    def content_hash(self) -> str:
        """Generate hash for deduplication."""
        content = f"{self.instruction}|{self.input_text}|{self.output}"
        return hashlib.md5(content.encode()).hexdigest()


@dataclass
class DatasetStats:
    """Statistics for the generated dataset."""
    total_examples: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)
    by_source: Dict[str, int] = field(default_factory=dict)
    avg_quality_score: float = 0.0
    deduped_count: int = 0
    train_count: int = 0
    eval_count: int = 0


# =============================================================================
# Data Loading Functions
# =============================================================================

def load_chatlog_interactions(
    min_quality: float = 0.5,
    max_examples: Optional[int] = None,
) -> List[TrainingExample]:
    """
    Load training examples from ChatOS interaction logs.
    
    Args:
        min_quality: Minimum quality score (based on thumbs up/down)
        max_examples: Maximum number of examples to load
    """
    examples = []
    
    # Load from interaction logs
    if CHATOS_LOGS_DIR.exists():
        for log_file in sorted(CHATOS_LOGS_DIR.glob("interactions_*.jsonl")):
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            
                            # Only process chat messages with responses
                            if data.get("type") != "chat_message":
                                continue
                            if not data.get("content") or not data.get("response"):
                                continue
                            
                            # Calculate quality score
                            quality = 0.7  # Default
                            if data.get("success") is False:
                                quality = 0.3
                            
                            if quality < min_quality:
                                continue
                            
                            # Determine reasoning type from content
                            reasoning_type = _classify_reasoning_type(data["content"])
                            
                            # Wrap response in reasoning format if not already
                            output = data["response"]
                            if "<think>" not in output:
                                output = _add_reasoning_wrapper(output, reasoning_type)
                            
                            examples.append(TrainingExample(
                                instruction=data["content"],
                                input_text="",
                                output=output,
                                reasoning_type=reasoning_type,
                                source="chatlog",
                                quality_score=quality,
                                metadata={
                                    "model": data.get("model"),
                                    "timestamp": data.get("timestamp"),
                                    "session_id": data.get("session_id"),
                                }
                            ))
                            
                            if max_examples and len(examples) >= max_examples:
                                return examples
                                
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"Error loading {log_file}: {e}")
    
    # Also load from memory logs
    memory_logs_dir = CHATOS_MEMORY_DIR / "logs"
    if memory_logs_dir.exists():
        for log_file in sorted(memory_logs_dir.glob("conversations_*.jsonl")):
            try:
                with open(log_file, "r") as f:
                    for line in f:
                        try:
                            data = json.loads(line.strip())
                            messages = data.get("messages", [])
                            
                            # Extract user-assistant pairs
                            for i, msg in enumerate(messages):
                                if msg.get("role") == "user" and i + 1 < len(messages):
                                    next_msg = messages[i + 1]
                                    if next_msg.get("role") == "assistant":
                                        # Quality from thumbs up/down
                                        quality = 0.7
                                        if data.get("thumbs_up") is True:
                                            quality = 1.0
                                        elif data.get("thumbs_up") is False:
                                            quality = 0.3
                                        elif data.get("quality") == "excellent":
                                            quality = 1.0
                                        elif data.get("quality") == "poor":
                                            quality = 0.3
                                        
                                        if quality < min_quality:
                                            continue
                                        
                                        reasoning_type = _classify_reasoning_type(msg["content"])
                                        output = next_msg["content"]
                                        if "<think>" not in output:
                                            output = _add_reasoning_wrapper(output, reasoning_type)
                                        
                                        examples.append(TrainingExample(
                                            instruction=msg["content"],
                                            input_text="",
                                            output=output,
                                            reasoning_type=reasoning_type,
                                            source="chatlog",
                                            quality_score=quality,
                                            metadata={
                                                "model": data.get("chosen_model"),
                                                "conversation_id": data.get("conversation_id"),
                                            }
                                        ))
                                        
                                        if max_examples and len(examples) >= max_examples:
                                            return examples
                                            
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"Error loading {log_file}: {e}")
    
    print(f"Loaded {len(examples)} examples from ChatOS logs")
    return examples


def load_persrm_data() -> List[TrainingExample]:
    """Load examples from PersRM reasoning data files."""
    examples = []
    
    # Load reasoning.jsonl
    reasoning_file = PERSRM_DATA_DIR / "reasoning.jsonl"
    if reasoning_file.exists():
        try:
            with open(reasoning_file, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        input_text = data.get("input", "")
                        output_text = data.get("expected_reasoning", "")
                        
                        if input_text and output_text:
                            reasoning_type = _classify_reasoning_type(input_text)
                            
                            # Ensure reasoning format
                            if "<think>" not in output_text:
                                output_text = _add_reasoning_wrapper(output_text, reasoning_type)
                            
                            examples.append(TrainingExample(
                                instruction=input_text,
                                input_text="",
                                output=output_text,
                                reasoning_type=reasoning_type,
                                source="persrm",
                                quality_score=0.9,
                            ))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error loading {reasoning_file}: {e}")
    
    # Load reasoning_instruction.jsonl
    instruction_file = PERSRM_DATA_DIR / "reasoning_instruction.jsonl"
    if instruction_file.exists():
        try:
            with open(instruction_file, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        instruction = data.get("instruction", "")
                        output = data.get("output", "")
                        
                        if instruction and output:
                            reasoning_type = _classify_reasoning_type(instruction)
                            
                            if "<think>" not in output:
                                output = _add_reasoning_wrapper(output, reasoning_type)
                            
                            examples.append(TrainingExample(
                                instruction=instruction,
                                input_text="",
                                output=output,
                                reasoning_type=reasoning_type,
                                source="persrm",
                                quality_score=0.9,
                            ))
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error loading {instruction_file}: {e}")
    
    print(f"Loaded {len(examples)} examples from PersRM data")
    return examples


def generate_synthetic_examples(
    count_per_type: int = 50,
) -> List[TrainingExample]:
    """
    Generate synthetic training examples from templates.
    These are high-quality seed examples to bootstrap training.
    """
    examples = []
    
    for reasoning_type, template_data in REASONING_TEMPLATES.items():
        for example in template_data.get("examples", []):
            examples.append(TrainingExample(
                instruction=example["input"],
                input_text="",
                output=example["output"],
                reasoning_type=reasoning_type,
                source="synthetic",
                quality_score=1.0,
            ))
    
    # Generate variations using prompts
    prompt_variations = _generate_prompt_variations(count_per_type)
    examples.extend(prompt_variations)
    
    print(f"Generated {len(examples)} synthetic examples")
    return examples


# =============================================================================
# Helper Functions
# =============================================================================

def _classify_reasoning_type(text: str) -> ReasoningType:
    """Classify the reasoning type based on text content."""
    text_lower = text.lower()
    
    # UI/Component analysis
    if any(kw in text_lower for kw in ["button", "input", "component", "modal", "card", "form"]):
        return ReasoningType.UI_ANALYSIS
    
    # Accessibility
    if any(kw in text_lower for kw in ["accessibility", "wcag", "aria", "screen reader", "a11y"]):
        return ReasoningType.ACCESSIBILITY
    
    # Code generation
    if any(kw in text_lower for kw in ["create", "generate", "build", "implement", "write code"]):
        return ReasoningType.CODE_GENERATION
    
    # Layout
    if any(kw in text_lower for kw in ["layout", "grid", "flexbox", "responsive", "spacing"]):
        return ReasoningType.LAYOUT_DESIGN
    
    # Debug
    if any(kw in text_lower for kw in ["debug", "fix", "error", "bug", "issue", "not working"]):
        return ReasoningType.DEBUG
    
    # Refactor
    if any(kw in text_lower for kw in ["refactor", "clean up", "improve code", "optimize"]):
        return ReasoningType.REFACTOR
    
    # UX
    if any(kw in text_lower for kw in ["user experience", "usability", "ux", "user flow"]):
        return ReasoningType.UX_REASONING
    
    return ReasoningType.GENERAL


def _add_reasoning_wrapper(response: str, reasoning_type: ReasoningType) -> str:
    """Wrap a response in reasoning format if not already formatted."""
    # Generate a simple reasoning trace based on response length
    if len(response) < 100:
        think_content = "Analyzing the request and formulating a concise response."
    else:
        think_content = f"""Step 1: Understanding the request
The user is asking about {reasoning_type.value.replace('_', ' ')}.

Step 2: Key considerations
- Breaking down the problem systematically
- Considering best practices and patterns
- Ensuring the response is actionable

Step 3: Formulating response
Providing a comprehensive answer with specific recommendations."""
    
    return f"<think>\n{think_content}\n</think>\n\n<answer>\n{response}\n</answer>"


def _generate_prompt_variations(count_per_type: int) -> List[TrainingExample]:
    """Generate additional prompt variations for each reasoning type."""
    examples = []
    
    ui_prompts = [
        "Analyze this {component} component for usability issues",
        "Review the UX of this {component}",
        "What accessibility problems exist in this {component}?",
        "How can we improve this {component}'s design?",
        "Evaluate the visual hierarchy of this {component}",
    ]
    
    components = ["button", "form", "modal", "dropdown", "navigation", "card", "table", "input"]
    
    # Note: These are template prompts - actual generation would need an LLM
    # For now, we just return the seed examples from templates
    
    return examples


def deduplicate_examples(examples: List[TrainingExample]) -> Tuple[List[TrainingExample], int]:
    """Remove duplicate examples based on content hash."""
    seen_hashes: Set[str] = set()
    unique_examples = []
    duplicates = 0
    
    for example in examples:
        content_hash = example.content_hash()
        if content_hash not in seen_hashes:
            seen_hashes.add(content_hash)
            unique_examples.append(example)
        else:
            duplicates += 1
    
    return unique_examples, duplicates


def balance_by_type(
    examples: List[TrainingExample],
    max_per_type: int = 500,
) -> List[TrainingExample]:
    """Balance examples across reasoning types."""
    by_type: Dict[ReasoningType, List[TrainingExample]] = {}
    
    for example in examples:
        if example.reasoning_type not in by_type:
            by_type[example.reasoning_type] = []
        by_type[example.reasoning_type].append(example)
    
    balanced = []
    for reasoning_type, type_examples in by_type.items():
        # Sort by quality score, take top examples
        type_examples.sort(key=lambda x: x.quality_score, reverse=True)
        balanced.extend(type_examples[:max_per_type])
    
    random.shuffle(balanced)
    return balanced


def split_train_eval(
    examples: List[TrainingExample],
    eval_ratio: float = 0.1,
) -> Tuple[List[TrainingExample], List[TrainingExample]]:
    """Split examples into training and evaluation sets."""
    random.shuffle(examples)
    split_idx = int(len(examples) * (1 - eval_ratio))
    return examples[:split_idx], examples[split_idx:]


# =============================================================================
# Main Generator Class
# =============================================================================

class PersRMStandaloneGenerator:
    """
    Generates training data for PersRM standalone model fine-tuning.
    
    Combines:
    - ChatOS interaction logs (filtered by quality)
    - PersRM reasoning data
    - Synthetic chain-of-thought examples
    """
    
    def __init__(
        self,
        output_dir: Optional[Path] = None,
        min_quality: float = 0.5,
        max_per_type: int = 500,
    ):
        self.output_dir = output_dir or OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.min_quality = min_quality
        self.max_per_type = max_per_type
        self.examples: List[TrainingExample] = []
        self.stats = DatasetStats()
    
    def load_all_data(self) -> 'PersRMStandaloneGenerator':
        """Load data from all sources."""
        # Load ChatOS logs
        chatlog_examples = load_chatlog_interactions(
            min_quality=self.min_quality
        )
        
        # Load PersRM data
        persrm_examples = load_persrm_data()
        
        # Generate synthetic examples
        synthetic_examples = generate_synthetic_examples()
        
        # Combine all
        self.examples = chatlog_examples + persrm_examples + synthetic_examples
        
        return self
    
    def process(self) -> 'PersRMStandaloneGenerator':
        """Process and clean the examples."""
        # Deduplicate
        self.examples, deduped = deduplicate_examples(self.examples)
        self.stats.deduped_count = deduped
        
        # Balance by type
        self.examples = balance_by_type(self.examples, self.max_per_type)
        
        return self
    
    def compute_stats(self) -> DatasetStats:
        """Compute statistics about the dataset."""
        self.stats.total_examples = len(self.examples)
        
        # Count by type
        self.stats.by_type = {}
        for example in self.examples:
            type_name = example.reasoning_type.value
            self.stats.by_type[type_name] = self.stats.by_type.get(type_name, 0) + 1
        
        # Count by source
        self.stats.by_source = {}
        for example in self.examples:
            self.stats.by_source[example.source] = self.stats.by_source.get(example.source, 0) + 1
        
        # Average quality
        if self.examples:
            self.stats.avg_quality_score = sum(e.quality_score for e in self.examples) / len(self.examples)
        
        return self.stats
    
    def save(
        self,
        eval_ratio: float = 0.1,
        format: str = "chat",  # "chat" or "instruction"
    ) -> Dict[str, Path]:
        """
        Save the dataset to files.
        
        Args:
            eval_ratio: Fraction for evaluation set
            format: Output format ("chat" for messages, "instruction" for instruction/output)
        
        Returns:
            Dict with paths to train and eval files
        """
        # Split
        train_examples, eval_examples = split_train_eval(self.examples, eval_ratio)
        self.stats.train_count = len(train_examples)
        self.stats.eval_count = len(eval_examples)
        
        # Prepare output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        train_path = self.output_dir / f"persrm_standalone_train_{timestamp}.jsonl"
        eval_path = self.output_dir / f"persrm_standalone_eval_{timestamp}.jsonl"
        stats_path = self.output_dir / f"stats_{timestamp}.json"
        
        # Write training file
        with open(train_path, "w") as f:
            for example in train_examples:
                if format == "chat":
                    data = example.to_chat_format()
                else:
                    data = example.to_instruction_format()
                f.write(json.dumps(data) + "\n")
        
        # Write eval file
        with open(eval_path, "w") as f:
            for example in eval_examples:
                if format == "chat":
                    data = example.to_chat_format()
                else:
                    data = example.to_instruction_format()
                f.write(json.dumps(data) + "\n")
        
        # Write stats
        self.compute_stats()
        with open(stats_path, "w") as f:
            json.dump({
                "total_examples": self.stats.total_examples,
                "train_count": self.stats.train_count,
                "eval_count": self.stats.eval_count,
                "by_type": self.stats.by_type,
                "by_source": self.stats.by_source,
                "avg_quality_score": self.stats.avg_quality_score,
                "deduped_count": self.stats.deduped_count,
                "created_at": timestamp,
            }, f, indent=2)
        
        # Create symlinks to latest
        latest_train = self.output_dir / "persrm_standalone_train_latest.jsonl"
        latest_eval = self.output_dir / "persrm_standalone_eval_latest.jsonl"
        
        for latest, current in [(latest_train, train_path), (latest_eval, eval_path)]:
            if latest.exists():
                latest.unlink()
            latest.symlink_to(current.name)
        
        print(f"\nDataset saved:")
        print(f"  Train: {train_path} ({self.stats.train_count} examples)")
        print(f"  Eval: {eval_path} ({self.stats.eval_count} examples)")
        print(f"  Stats: {stats_path}")
        
        return {
            "train": train_path,
            "eval": eval_path,
            "stats": stats_path,
        }
    
    def get_summary(self) -> str:
        """Get a human-readable summary."""
        self.compute_stats()
        
        lines = [
            "=" * 50,
            "PersRM Standalone Training Data Summary",
            "=" * 50,
            f"Total Examples: {self.stats.total_examples}",
            f"Train: {self.stats.train_count}, Eval: {self.stats.eval_count}",
            f"Deduplicated: {self.stats.deduped_count}",
            f"Avg Quality: {self.stats.avg_quality_score:.2f}",
            "",
            "By Reasoning Type:",
        ]
        
        for type_name, count in sorted(self.stats.by_type.items()):
            lines.append(f"  {type_name}: {count}")
        
        lines.append("")
        lines.append("By Source:")
        for source, count in sorted(self.stats.by_source.items()):
            lines.append(f"  {source}: {count}")
        
        return "\n".join(lines)


# =============================================================================
# API Functions
# =============================================================================

def generate_persrm_standalone_dataset(
    output_dir: Optional[Path] = None,
    min_quality: float = 0.5,
    eval_ratio: float = 0.1,
) -> Dict[str, Any]:
    """
    Generate the PersRM standalone training dataset.
    
    This is the main entry point for dataset generation.
    
    Args:
        output_dir: Output directory
        min_quality: Minimum quality score
        eval_ratio: Fraction for evaluation
    
    Returns:
        Dict with paths and stats
    """
    generator = PersRMStandaloneGenerator(
        output_dir=output_dir,
        min_quality=min_quality,
    )
    
    generator.load_all_data()
    generator.process()
    paths = generator.save(eval_ratio=eval_ratio)
    
    print(generator.get_summary())
    
    return {
        "paths": paths,
        "stats": generator.stats,
    }


def get_training_data_stats() -> Dict[str, Any]:
    """Get statistics about available training data without generating."""
    chatlog_count = 0
    persrm_count = 0
    
    # Count chatlog examples
    if CHATOS_LOGS_DIR.exists():
        for log_file in CHATOS_LOGS_DIR.glob("interactions_*.jsonl"):
            try:
                with open(log_file) as f:
                    chatlog_count += sum(1 for line in f if '"type": "chat_message"' in line)
            except:
                pass
    
    if (CHATOS_MEMORY_DIR / "logs").exists():
        for log_file in (CHATOS_MEMORY_DIR / "logs").glob("conversations_*.jsonl"):
            try:
                with open(log_file) as f:
                    chatlog_count += sum(1 for _ in f)
            except:
                pass
    
    # Count PersRM examples
    for file_name in ["reasoning.jsonl", "reasoning_instruction.jsonl"]:
        file_path = PERSRM_DATA_DIR / file_name
        if file_path.exists():
            try:
                with open(file_path) as f:
                    persrm_count += sum(1 for _ in f)
            except:
                pass
    
    total = chatlog_count + persrm_count
    ready = total >= 100  # Minimum for meaningful training
    
    return {
        "chatlog_examples": chatlog_count,
        "persrm_examples": persrm_count,
        "total_examples": total,
        "ready_for_training": ready,
        "minimum_required": 100,
        "recommended": 1000,
    }


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate PersRM Standalone Training Data")
    parser.add_argument("--output", type=str, help="Output directory")
    parser.add_argument("--min-quality", type=float, default=0.5, help="Minimum quality score")
    parser.add_argument("--eval-ratio", type=float, default=0.1, help="Evaluation set ratio")
    parser.add_argument("--stats-only", action="store_true", help="Only show stats")
    
    args = parser.parse_args()
    
    if args.stats_only:
        stats = get_training_data_stats()
        print(json.dumps(stats, indent=2))
    else:
        output_dir = Path(args.output) if args.output else None
        result = generate_persrm_standalone_dataset(
            output_dir=output_dir,
            min_quality=args.min_quality,
            eval_ratio=args.eval_ratio,
        )

