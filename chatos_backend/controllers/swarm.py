"""
swarm.py - Multi-agent coding swarm coordination.

Implements /swarm command functionality:
- Multiple specialized coding agents
- Collaborative problem solving
- Structured code generation workflow
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from chatos_backend.config import SWARM_AGENTS


class AgentRole(Enum):
    """Roles for swarm agents."""
    ARCHITECT = "architect"
    IMPLEMENTER = "implementer"
    REVIEWER = "reviewer"
    TESTER = "tester"
    DOCUMENTER = "documenter"


@dataclass
class AgentResponse:
    """Response from a single swarm agent."""
    
    agent_role: str
    agent_name: str
    content: str
    artifacts: List[Dict[str, str]] = field(default_factory=list)  # {type, name, content}
    suggestions: List[str] = field(default_factory=list)
    confidence: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_role": self.agent_role,
            "agent_name": self.agent_name,
            "content": self.content,
            "artifacts": self.artifacts,
            "suggestions": self.suggestions,
            "confidence": self.confidence,
        }


@dataclass
class SwarmResult:
    """Complete swarm collaboration result."""
    
    task: str
    responses: List[AgentResponse] = field(default_factory=list)
    final_code: str = ""
    file_structure: Dict[str, str] = field(default_factory=dict)
    tests: List[str] = field(default_factory=list)
    documentation: str = ""
    collaboration_log: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "responses": [r.to_dict() for r in self.responses],
            "final_code": self.final_code,
            "file_structure": self.file_structure,
            "tests": self.tests,
            "documentation": self.documentation,
            "collaboration_log": self.collaboration_log,
            "timestamp": self.timestamp.isoformat(),
        }


class SwarmAgent:
    """
    A specialized agent in the coding swarm.
    
    Each agent has a specific role and expertise area.
    In production, each agent would be backed by an LLM
    with role-specific system prompts.
    """
    
    def __init__(self, role: str):
        self.role = role
        self.info = SWARM_AGENTS.get(role, {
            "name": role.title(),
            "role": "General assistance",
            "icon": "🤖",
        })
        self.name = self.info["name"]
        self.icon = self.info["icon"]
    
    async def process(
        self,
        task: str,
        context: Dict[str, Any] = None
    ) -> AgentResponse:
        """
        Process a task according to this agent's role.
        
        Args:
            task: The coding task
            context: Previous agent outputs and context
            
        Returns:
            AgentResponse with role-specific output
        """
        await asyncio.sleep(0.3)  # Simulate processing
        
        context = context or {}
        
        if self.role == "architect":
            return await self._architect_response(task, context)
        elif self.role == "implementer":
            return await self._implementer_response(task, context)
        elif self.role == "reviewer":
            return await self._reviewer_response(task, context)
        elif self.role == "tester":
            return await self._tester_response(task, context)
        elif self.role == "documenter":
            return await self._documenter_response(task, context)
        else:
            return AgentResponse(
                agent_role=self.role,
                agent_name=self.name,
                content="Unknown role",
                confidence=0.0,
            )
    
    async def _architect_response(
        self,
        task: str,
        context: Dict
    ) -> AgentResponse:
        """Generate architecture design."""
        words = task.lower().split()
        
        # Detect task type
        is_api = any(w in words for w in ["api", "rest", "endpoint", "server"])
        is_cli = any(w in words for w in ["cli", "command", "terminal"])
        is_web = any(w in words for w in ["web", "frontend", "ui", "page"])
        
        if is_api:
            arch_type = "REST API"
            structure = """
project/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app
│   ├── models/          # Pydantic models
│   ├── routes/          # API endpoints
│   ├── services/        # Business logic
│   └── utils/           # Helpers
├── tests/
├── requirements.txt
└── README.md"""
        elif is_web:
            arch_type = "Web Application"
            structure = """
project/
├── src/
│   ├── components/      # React components
│   ├── pages/           # Page components
│   ├── hooks/           # Custom hooks
│   ├── utils/           # Utilities
│   └── App.tsx
├── public/
├── package.json
└── README.md"""
        else:
            arch_type = "Python Module"
            structure = """
project/
├── src/
│   ├── __init__.py
│   ├── core.py          # Core logic
│   ├── utils.py         # Utilities
│   └── cli.py           # CLI interface
├── tests/
├── setup.py
└── README.md"""
        
        content = f"""## 🏗️ Architecture Design

### Task Analysis
**Request:** {task[:100]}...

### Recommended Architecture: {arch_type}

### Project Structure
```
{structure}
```

### Key Design Decisions
1. **Modularity:** Separated concerns for maintainability
2. **Testability:** Clear boundaries for unit testing
3. **Scalability:** Structure supports future growth

### Technology Stack
- Language: Python 3.10+
- Framework: FastAPI / Click / React (as appropriate)
- Testing: pytest
- Documentation: Sphinx / Storybook

### Next Steps
1. Implementer: Create core modules
2. Tester: Set up test framework
3. Documenter: Initialize documentation"""
        
        return AgentResponse(
            agent_role=self.role,
            agent_name=self.name,
            content=content,
            artifacts=[{
                "type": "structure",
                "name": "project_structure.txt",
                "content": structure,
            }],
            suggestions=[
                "Consider adding type hints throughout",
                "Set up CI/CD pipeline",
                "Add pre-commit hooks",
            ],
            confidence=0.85,
        )
    
    async def _implementer_response(
        self,
        task: str,
        context: Dict
    ) -> AgentResponse:
        """Generate implementation code."""
        # Extract key terms for code generation
        words = task.lower().split()
        
        # Generate contextual code
        if "sort" in words:
            code = '''def sort_list(items: list, reverse: bool = False) -> list:
    """
    Sort a list of items.
    
    Args:
        items: List to sort
        reverse: Sort in descending order if True
        
    Returns:
        Sorted list
    """
    return sorted(items, reverse=reverse)


def quicksort(arr: list) -> list:
    """Quicksort implementation for educational purposes."""
    if len(arr) <= 1:
        return arr
    
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    
    return quicksort(left) + middle + quicksort(right)
'''
        elif "api" in words or "endpoint" in words:
            code = '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="Generated API")


class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None


# In-memory storage
items_db: List[Item] = []


@app.get("/items", response_model=List[Item])
async def list_items():
    """Get all items."""
    return items_db


@app.post("/items", response_model=Item)
async def create_item(item: Item):
    """Create a new item."""
    item.id = len(items_db) + 1
    items_db.append(item)
    return item


@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    """Get item by ID."""
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")
'''
        else:
            # Generic implementation
            func_name = '_'.join(words[:3]) if len(words) >= 3 else 'process_data'
            code = f'''def {func_name}(data):
    """
    Process the given data.
    
    Args:
        data: Input data to process
        
    Returns:
        Processed result
    """
    # Implementation based on: {task[:50]}
    result = []
    
    # Process each item
    for item in data:
        processed = item  # Transform as needed
        result.append(processed)
    
    return result


class DataProcessor:
    """Class-based approach for complex processing."""
    
    def __init__(self, config=None):
        self.config = config or {{}}
    
    def process(self, data):
        """Main processing method."""
        return {func_name}(data)
    
    def validate(self, data):
        """Validate input data."""
        if not data:
            raise ValueError("Data cannot be empty")
        return True
'''
        
        content = f"""## 💻 Implementation

### Generated Code

```python
{code}
```

### Implementation Notes
- Type hints included for better IDE support
- Docstrings follow Google style
- Error handling for common cases
- Ready for testing and integration

### Files to Create
1. `core.py` - Main implementation
2. `__init__.py` - Package exports

### Dependencies
- Python 3.9+
- typing (standard library)
- FastAPI (if API route)"""
        
        return AgentResponse(
            agent_role=self.role,
            agent_name=self.name,
            content=content,
            artifacts=[{
                "type": "code",
                "name": "core.py",
                "content": code,
            }],
            suggestions=[
                "Add input validation",
                "Consider async versions",
                "Add logging",
            ],
            confidence=0.80,
        )
    
    async def _reviewer_response(
        self,
        task: str,
        context: Dict
    ) -> AgentResponse:
        """Generate code review."""
        content = """## 🔍 Code Review

### Review Summary
Overall: **APPROVED with suggestions** ✅

### Checklist
- [x] Code follows style guidelines
- [x] Functions have docstrings
- [x] Type hints are present
- [ ] Edge cases need more coverage
- [ ] Consider adding logging

### Detailed Feedback

#### Strengths 💪
1. Clean, readable code structure
2. Good separation of concerns
3. Appropriate use of type hints
4. Docstrings are informative

#### Areas for Improvement 📝
1. **Error handling:** Add try/except for external operations
2. **Validation:** Validate inputs at function boundaries
3. **Constants:** Extract magic numbers to named constants
4. **Testing:** Ensure 80%+ code coverage

### Security Considerations 🔒
- Validate all user inputs
- Sanitize data before storage
- Use parameterized queries for DB operations

### Performance Notes ⚡
- Consider lazy loading for large datasets
- Cache frequently accessed data
- Profile before optimizing"""
        
        return AgentResponse(
            agent_role=self.role,
            agent_name=self.name,
            content=content,
            artifacts=[],
            suggestions=[
                "Run static analysis tools",
                "Add integration tests",
                "Document API changes",
            ],
            confidence=0.90,
        )
    
    async def _tester_response(
        self,
        task: str,
        context: Dict
    ) -> AgentResponse:
        """Generate test cases."""
        test_code = '''import pytest
from core import process_data, DataProcessor


class TestProcessData:
    """Tests for process_data function."""
    
    def test_empty_input(self):
        """Test with empty input."""
        result = process_data([])
        assert result == []
    
    def test_single_item(self):
        """Test with single item."""
        result = process_data([1])
        assert result == [1]
    
    def test_multiple_items(self):
        """Test with multiple items."""
        data = [1, 2, 3, 4, 5]
        result = process_data(data)
        assert len(result) == len(data)
    
    def test_none_input(self):
        """Test with None input raises error."""
        with pytest.raises(TypeError):
            process_data(None)


class TestDataProcessor:
    """Tests for DataProcessor class."""
    
    @pytest.fixture
    def processor(self):
        """Create processor instance."""
        return DataProcessor()
    
    def test_initialization(self, processor):
        """Test default initialization."""
        assert processor.config == {}
    
    def test_process_method(self, processor):
        """Test process method."""
        result = processor.process([1, 2, 3])
        assert isinstance(result, list)
    
    def test_validate_empty(self, processor):
        """Test validation with empty data."""
        with pytest.raises(ValueError):
            processor.validate([])


# Parametrized tests
@pytest.mark.parametrize("input_data,expected", [
    ([1, 2, 3], [1, 2, 3]),
    (["a", "b"], ["a", "b"]),
    ([None], [None]),
])
def test_process_data_parametrized(input_data, expected):
    """Parametrized test cases."""
    result = process_data(input_data)
    assert result == expected
'''
        
        content = f"""## 🧪 Test Suite

### Generated Tests

```python
{test_code}
```

### Test Coverage Plan
| Component | Unit Tests | Integration | E2E |
|-----------|------------|-------------|-----|
| Core Logic | ✅ | ⏳ | - |
| API Routes | ✅ | ✅ | ⏳ |
| Utils | ✅ | - | - |

### Test Categories
1. **Unit Tests:** Function-level testing
2. **Integration:** Component interaction
3. **Edge Cases:** Boundary conditions
4. **Error Cases:** Exception handling

### Running Tests
```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific test file
pytest tests/test_core.py -v
```"""
        
        return AgentResponse(
            agent_role=self.role,
            agent_name=self.name,
            content=content,
            artifacts=[{
                "type": "test",
                "name": "test_core.py",
                "content": test_code,
            }],
            suggestions=[
                "Add property-based tests with hypothesis",
                "Include performance benchmarks",
                "Add mutation testing",
            ],
            confidence=0.85,
        )
    
    async def _documenter_response(
        self,
        task: str,
        context: Dict
    ) -> AgentResponse:
        """Generate documentation."""
        readme = f'''# Project Name

> {task[:80]}

## Overview

This project provides [brief description based on task].

## Installation

```bash
# Clone the repository
git clone https://github.com/user/project.git
cd project

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

```python
from project import main_function

# Basic usage
result = main_function(data)
print(result)
```

## API Reference

### `main_function(data)`

Process the input data.

**Parameters:**
- `data` (list): Input data to process

**Returns:**
- `list`: Processed results

**Example:**
```python
>>> main_function([1, 2, 3])
[1, 2, 3]
```

## Configuration

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `debug` | bool | False | Enable debug mode |
| `timeout` | int | 30 | Request timeout |

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License - see LICENSE file.
'''
        
        content = f"""## 📝 Documentation

### README.md

```markdown
{readme}
```

### Documentation Checklist
- [x] Project overview
- [x] Installation instructions
- [x] Quick start guide
- [x] API reference
- [x] Configuration options
- [x] Contributing guidelines

### Additional Documentation
1. `docs/api.md` - Detailed API docs
2. `docs/architecture.md` - System design
3. `CHANGELOG.md` - Version history
4. `CONTRIBUTING.md` - Contribution guide"""
        
        return AgentResponse(
            agent_role=self.role,
            agent_name=self.name,
            content=content,
            artifacts=[{
                "type": "documentation",
                "name": "README.md",
                "content": readme,
            }],
            suggestions=[
                "Add API documentation with Sphinx",
                "Create usage examples",
                "Add troubleshooting section",
            ],
            confidence=0.90,
        )


class SwarmCoordinator:
    """
    Coordinates multiple agents in a coding swarm.
    
    Orchestrates the workflow:
    1. Architect designs the solution
    2. Implementer writes the code
    3. Reviewer checks quality
    4. Tester generates tests
    5. Documenter creates docs
    """
    
    def __init__(self):
        self.agents = {
            role: SwarmAgent(role)
            for role in SWARM_AGENTS.keys()
        }
        self._history: List[SwarmResult] = []
    
    async def execute(
        self,
        task: str,
        selected_agents: Optional[List[str]] = None
    ) -> SwarmResult:
        """
        Execute a coding task with the swarm.
        
        Args:
            task: The coding task description
            selected_agents: Specific agents to use (default: all)
            
        Returns:
            SwarmResult with all agent outputs
        """
        result = SwarmResult(task=task)
        context: Dict[str, Any] = {"task": task}
        
        # Determine which agents to use
        agent_order = selected_agents or [
            "architect",
            "implementer", 
            "reviewer",
            "tester",
            "documenter",
        ]
        
        # Execute agents in sequence
        for role in agent_order:
            if role not in self.agents:
                continue
            
            agent = self.agents[role]
            result.collaboration_log.append(
                f"🔄 {agent.icon} {agent.name} is working..."
            )
            
            response = await agent.process(task, context)
            result.responses.append(response)
            
            # Add to context for next agent
            context[role] = response
            
            result.collaboration_log.append(
                f"✅ {agent.icon} {agent.name} completed (confidence: {response.confidence:.0%})"
            )
        
        # Aggregate results
        result.final_code = self._extract_code(result.responses)
        result.tests = self._extract_tests(result.responses)
        result.documentation = self._extract_docs(result.responses)
        result.file_structure = self._build_file_structure(result.responses)
        
        self._history.append(result)
        
        return result
    
    def _extract_code(self, responses: List[AgentResponse]) -> str:
        """Extract main code from implementer response."""
        for r in responses:
            if r.agent_role == "implementer":
                for artifact in r.artifacts:
                    if artifact["type"] == "code":
                        return artifact["content"]
        return ""
    
    def _extract_tests(self, responses: List[AgentResponse]) -> List[str]:
        """Extract test code from tester response."""
        tests = []
        for r in responses:
            if r.agent_role == "tester":
                for artifact in r.artifacts:
                    if artifact["type"] == "test":
                        tests.append(artifact["content"])
        return tests
    
    def _extract_docs(self, responses: List[AgentResponse]) -> str:
        """Extract documentation from documenter response."""
        for r in responses:
            if r.agent_role == "documenter":
                for artifact in r.artifacts:
                    if artifact["type"] == "documentation":
                        return artifact["content"]
        return ""
    
    def _build_file_structure(
        self,
        responses: List[AgentResponse]
    ) -> Dict[str, str]:
        """Build file structure from all artifacts."""
        files = {}
        for r in responses:
            for artifact in r.artifacts:
                name = artifact.get("name", "unknown")
                content = artifact.get("content", "")
                files[name] = content
        return files
    
    def format_result(self, result: SwarmResult) -> str:
        """
        Format swarm result for display.
        
        Args:
            result: The swarm execution result
            
        Returns:
            Formatted markdown string
        """
        lines = [
            "# 🐝 Swarm Collaboration Result",
            "",
            f"**Task:** {result.task}",
            "",
            "## Collaboration Log",
            "",
        ]
        
        for log in result.collaboration_log:
            lines.append(f"- {log}")
        
        lines.extend([
            "",
            "## Agent Outputs",
            "",
        ])
        
        for response in result.responses:
            agent_info = SWARM_AGENTS.get(response.agent_role, {})
            icon = agent_info.get("icon", "🤖")
            lines.extend([
                f"### {icon} {response.agent_name}",
                "",
                response.content,
                "",
                "---",
                "",
            ])
        
        if result.file_structure:
            lines.extend([
                "## Generated Files",
                "",
            ])
            for name, content in result.file_structure.items():
                lines.append(f"- `{name}`")
        
        return '\n'.join(lines)


# Singleton instance
_coordinator: Optional[SwarmCoordinator] = None


def get_swarm_coordinator() -> SwarmCoordinator:
    """Get the singleton swarm coordinator instance."""
    global _coordinator
    if _coordinator is None:
        _coordinator = SwarmCoordinator()
    return _coordinator

