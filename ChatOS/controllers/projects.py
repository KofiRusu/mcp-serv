"""
projects.py - Project scaffolding and management.

Handles full project lifecycle:
- Create new project directories with templates
- Generate virtual environments
- Install dependencies
- Run projects
- Project-specific memory and context
"""

import asyncio
import json
import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ChatOS.config import SANDBOX_DIR


# =============================================================================
# Project Templates
# =============================================================================

PROJECT_TEMPLATES = {
    "python-basic": {
        "name": "Python Basic",
        "description": "Simple Python project with main.py",
        "files": {
            "main.py": '''"""
{project_name} - Main entry point
"""

def main():
    print("Hello from {project_name}!")

if __name__ == "__main__":
    main()
''',
            "requirements.txt": "# Add your dependencies here\n",
            "README.md": "# {project_name}\n\n{description}\n",
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\nvenv/\n.env\n",
        },
    },
    "fastapi": {
        "name": "FastAPI API",
        "description": "REST API with FastAPI",
        "files": {
            "app/__init__.py": "",
            "app/main.py": '''"""
{project_name} - FastAPI Application
"""

from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI(title="{project_name}")


class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None


items_db: List[Item] = []


@app.get("/")
async def root():
    return {{"message": "Welcome to {project_name}"}}


@app.get("/items", response_model=List[Item])
async def list_items():
    return items_db


@app.post("/items", response_model=Item)
async def create_item(item: Item):
    item.id = len(items_db) + 1
    items_db.append(item)
    return item
''',
            "requirements.txt": "fastapi>=0.109.0\nuvicorn[standard]>=0.27.0\npydantic>=2.5.0\n",
            "README.md": '''# {project_name}

{description}

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for API documentation.
''',
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\nvenv/\n.env\n",
            "run.sh": "#!/bin/bash\nsource .venv/bin/activate\nuvicorn app.main:app --reload\n",
        },
    },
    "cli-tool": {
        "name": "CLI Tool",
        "description": "Command-line application with Click",
        "files": {
            "cli.py": '''"""
{project_name} - CLI Tool
"""

import click


@click.group()
def cli():
    """{{project_name}} - A CLI tool."""
    pass


@cli.command()
@click.argument("name", default="World")
def hello(name):
    """Say hello to NAME."""
    click.echo(f"Hello, {{name}}!")


@cli.command()
@click.option("--count", default=1, help="Number of times to repeat.")
def repeat(count):
    """Repeat a message COUNT times."""
    for i in range(count):
        click.echo(f"Message {{i + 1}}")


if __name__ == "__main__":
    cli()
''',
            "requirements.txt": "click>=8.1.0\n",
            "README.md": '''# {project_name}

{description}

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python cli.py hello World
python cli.py repeat --count 5
```
''',
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\nvenv/\n.env\n",
        },
    },
    "flask-web": {
        "name": "Flask Web App",
        "description": "Web application with Flask",
        "files": {
            "app.py": '''"""
{project_name} - Flask Web Application
"""

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", title="{project_name}")


@app.route("/api/data")
def get_data():
    return jsonify({{"message": "Hello from {project_name}!"}})


if __name__ == "__main__":
    app.run(debug=True)
''',
            "templates/index.html": '''<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
    </style>
</head>
<body>
    <h1>Welcome to {{ title }}</h1>
    <p>Your Flask application is running!</p>
</body>
</html>
''',
            "requirements.txt": "flask>=3.0.0\n",
            "README.md": '''# {project_name}

{description}

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Open http://localhost:5000
''',
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\nvenv/\n.env\n",
        },
    },
    "empty": {
        "name": "Empty Project",
        "description": "Blank project with just essentials",
        "files": {
            "README.md": "# {project_name}\n\n{description}\n",
            "requirements.txt": "# Add your dependencies here\n",
            ".gitignore": "__pycache__/\n*.pyc\n.venv/\nvenv/\n.env\n",
        },
    },
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ProjectConfig:
    """Configuration for a project."""
    
    id: str
    name: str
    path: Path
    template: str
    description: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    python_version: str = "3"
    has_venv: bool = False
    dependencies_installed: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "path": str(self.path),
            "template": self.template,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "python_version": self.python_version,
            "has_venv": self.has_venv,
            "dependencies_installed": self.dependencies_installed,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectConfig":
        data["path"] = Path(data["path"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


@dataclass
class ProjectStatus:
    """Current status of a project."""
    
    exists: bool
    has_venv: bool = False
    venv_path: Optional[str] = None
    has_requirements: bool = False
    dependencies_installed: bool = False
    is_running: bool = False
    process_pid: Optional[int] = None
    last_run: Optional[datetime] = None
    files_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "exists": self.exists,
            "has_venv": self.has_venv,
            "venv_path": self.venv_path,
            "has_requirements": self.has_requirements,
            "dependencies_installed": self.dependencies_installed,
            "is_running": self.is_running,
            "process_pid": self.process_pid,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "files_count": self.files_count,
        }


@dataclass
class RunResult:
    """Result of running a project."""
    
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time: float = 0.0
    command: str = ""


# =============================================================================
# Project Manager
# =============================================================================

class ProjectManager:
    """
    Manages coding projects with full lifecycle support.
    
    Features:
    - Create projects from templates
    - Virtual environment management
    - Dependency installation
    - Project execution
    - Status tracking
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = base_dir or SANDBOX_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Projects registry
        self.projects_file = self.base_dir / ".chatos_projects.json"
        self.projects: Dict[str, ProjectConfig] = {}
        self._load_projects()
        
        # Running processes
        self._running_processes: Dict[str, subprocess.Popen] = {}
    
    def _load_projects(self) -> None:
        """Load projects registry from disk."""
        if self.projects_file.exists():
            try:
                data = json.loads(self.projects_file.read_text())
                for proj_data in data.get("projects", []):
                    proj = ProjectConfig.from_dict(proj_data)
                    self.projects[proj.id] = proj
            except Exception:
                pass
    
    def _save_projects(self) -> None:
        """Save projects registry to disk."""
        data = {
            "projects": [p.to_dict() for p in self.projects.values()]
        }
        self.projects_file.write_text(json.dumps(data, indent=2))
    
    # =========================================================================
    # Project Creation
    # =========================================================================
    
    async def create_project(
        self,
        name: str,
        template: str = "python-basic",
        description: str = "",
        auto_setup: bool = True,
    ) -> ProjectConfig:
        """
        Create a new project from a template.
        
        Args:
            name: Project name (used for directory)
            template: Template to use
            description: Project description
            auto_setup: Automatically create venv and install deps
            
        Returns:
            ProjectConfig for the new project
        """
        # Sanitize name for directory
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in name)
        project_dir = self.base_dir / safe_name
        
        # Check if exists
        if project_dir.exists():
            raise FileExistsError(f"Project directory already exists: {safe_name}")
        
        # Get template
        if template not in PROJECT_TEMPLATES:
            template = "python-basic"
        
        template_config = PROJECT_TEMPLATES[template]
        
        # Create project config
        project = ProjectConfig(
            id=str(uuid.uuid4())[:8],
            name=name,
            path=project_dir,
            template=template,
            description=description or template_config["description"],
        )
        
        # Create directory and files
        project_dir.mkdir(parents=True)
        
        for file_path, content in template_config["files"].items():
            file_full_path = project_dir / file_path
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Replace placeholders
            formatted_content = content.format(
                project_name=name,
                description=project.description,
            )
            file_full_path.write_text(formatted_content)
        
        # Make shell scripts executable
        for file_path in template_config["files"]:
            if file_path.endswith(".sh"):
                (project_dir / file_path).chmod(0o755)
        
        # Register project
        self.projects[project.id] = project
        self._save_projects()
        
        # Auto-setup if requested
        if auto_setup:
            await self.setup_venv(project.id)
            await self.install_dependencies(project.id)
        
        return project
    
    # =========================================================================
    # Virtual Environment
    # =========================================================================
    
    async def setup_venv(self, project_id: str) -> bool:
        """
        Create a virtual environment for a project.
        
        Args:
            project_id: Project ID
            
        Returns:
            True if successful
        """
        project = self.projects.get(project_id)
        if not project:
            raise ValueError(f"Project not found: {project_id}")
        
        venv_path = project.path / ".venv"
        
        if venv_path.exists():
            return True  # Already exists
        
        # Create venv
        result = await asyncio.create_subprocess_exec(
            "python3", "-m", "venv", str(venv_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await result.communicate()
        
        if result.returncode == 0:
            project.has_venv = True
            self._save_projects()
            return True
        
        return False
    
    def get_venv_python(self, project_id: str) -> Optional[Path]:
        """Get the Python executable path for a project's venv."""
        project = self.projects.get(project_id)
        if not project:
            return None
        
        venv_python = project.path / ".venv" / "bin" / "python"
        if venv_python.exists():
            return venv_python
        
        return None
    
    # =========================================================================
    # Dependencies
    # =========================================================================
    
    async def install_dependencies(
        self,
        project_id: str,
        extra_packages: Optional[List[str]] = None,
    ) -> RunResult:
        """
        Install dependencies from requirements.txt.
        
        Args:
            project_id: Project ID
            extra_packages: Additional packages to install
            
        Returns:
            RunResult with installation output
        """
        import time
        start_time = time.time()
        
        project = self.projects.get(project_id)
        if not project:
            return RunResult(
                success=False,
                stderr=f"Project not found: {project_id}",
                exit_code=1,
            )
        
        # Ensure venv exists
        python_path = self.get_venv_python(project_id)
        if not python_path:
            await self.setup_venv(project_id)
            python_path = self.get_venv_python(project_id)
        
        if not python_path:
            return RunResult(
                success=False,
                stderr="Failed to create virtual environment",
                exit_code=1,
            )
        
        # Install from requirements.txt
        requirements_file = project.path / "requirements.txt"
        
        commands = []
        if requirements_file.exists():
            commands.append([str(python_path), "-m", "pip", "install", "-r", "requirements.txt"])
        
        # Add extra packages
        if extra_packages:
            commands.append([str(python_path), "-m", "pip", "install"] + extra_packages)
        
        all_stdout = []
        all_stderr = []
        final_exit_code = 0
        
        for cmd in commands:
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(project.path),
            )
            stdout, stderr = await result.communicate()
            
            all_stdout.append(stdout.decode())
            all_stderr.append(stderr.decode())
            
            if result.returncode != 0:
                final_exit_code = result.returncode
        
        if final_exit_code == 0:
            project.dependencies_installed = True
            self._save_projects()
        
        return RunResult(
            success=final_exit_code == 0,
            stdout="\n".join(all_stdout),
            stderr="\n".join(all_stderr),
            exit_code=final_exit_code,
            execution_time=time.time() - start_time,
            command=" && ".join([" ".join(c) for c in commands]),
        )
    
    # =========================================================================
    # Running Projects
    # =========================================================================
    
    async def run_project(
        self,
        project_id: str,
        command: Optional[str] = None,
        background: bool = False,
        timeout: int = 60,
    ) -> RunResult:
        """
        Run a project.
        
        Args:
            project_id: Project ID
            command: Custom command (default: auto-detect)
            background: Run in background
            timeout: Execution timeout (ignored if background)
            
        Returns:
            RunResult with output
        """
        import time
        start_time = time.time()
        
        project = self.projects.get(project_id)
        if not project:
            return RunResult(
                success=False,
                stderr=f"Project not found: {project_id}",
                exit_code=1,
            )
        
        # Get Python path
        python_path = self.get_venv_python(project_id)
        if not python_path:
            python_path = Path("python3")
        
        # Auto-detect run command
        if not command:
            command = self._detect_run_command(project, python_path)
        
        if not command:
            return RunResult(
                success=False,
                stderr="Could not detect how to run this project",
                exit_code=1,
            )
        
        # Run the command
        env = os.environ.copy()
        env["VIRTUAL_ENV"] = str(project.path / ".venv")
        env["PATH"] = f"{project.path / '.venv' / 'bin'}:{env.get('PATH', '')}"
        
        try:
            if background:
                # Run in background
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(project.path),
                    env=env,
                )
                self._running_processes[project_id] = process
                
                return RunResult(
                    success=True,
                    stdout=f"Started in background (PID: {process.pid})",
                    exit_code=0,
                    execution_time=0,
                    command=command,
                )
            else:
                # Run with timeout
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(project.path),
                    env=env,
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=timeout,
                    )
                    
                    return RunResult(
                        success=process.returncode == 0,
                        stdout=stdout.decode(),
                        stderr=stderr.decode(),
                        exit_code=process.returncode or 0,
                        execution_time=time.time() - start_time,
                        command=command,
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    return RunResult(
                        success=False,
                        stderr=f"Execution timed out after {timeout}s",
                        exit_code=-1,
                        execution_time=timeout,
                        command=command,
                    )
                    
        except Exception as e:
            return RunResult(
                success=False,
                stderr=str(e),
                exit_code=-1,
                execution_time=time.time() - start_time,
                command=command,
            )
    
    def _detect_run_command(
        self,
        project: ProjectConfig,
        python_path: Path,
    ) -> Optional[str]:
        """Auto-detect the run command for a project."""
        
        # Check for run.sh
        run_sh = project.path / "run.sh"
        if run_sh.exists():
            return "./run.sh"
        
        # Check template-specific patterns
        if project.template == "fastapi":
            return f"{python_path} -m uvicorn app.main:app --reload"
        
        if project.template == "flask-web":
            return f"{python_path} app.py"
        
        if project.template == "cli-tool":
            return f"{python_path} cli.py --help"
        
        # Check for main.py
        main_py = project.path / "main.py"
        if main_py.exists():
            return f"{python_path} main.py"
        
        # Check for app.py
        app_py = project.path / "app.py"
        if app_py.exists():
            return f"{python_path} app.py"
        
        return None
    
    async def stop_project(self, project_id: str) -> bool:
        """Stop a running project."""
        process = self._running_processes.get(project_id)
        if process:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=5)
            except asyncio.TimeoutError:
                process.kill()
            
            del self._running_processes[project_id]
            return True
        
        return False
    
    # =========================================================================
    # Status & Info
    # =========================================================================
    
    def get_status(self, project_id: str) -> ProjectStatus:
        """Get the current status of a project."""
        project = self.projects.get(project_id)
        
        if not project or not project.path.exists():
            return ProjectStatus(exists=False)
        
        venv_path = project.path / ".venv"
        requirements_file = project.path / "requirements.txt"
        
        # Count files
        files_count = sum(1 for _ in project.path.rglob("*") if _.is_file())
        
        # Check if running
        is_running = project_id in self._running_processes
        process_pid = None
        if is_running:
            proc = self._running_processes[project_id]
            process_pid = proc.pid
        
        return ProjectStatus(
            exists=True,
            has_venv=venv_path.exists(),
            venv_path=str(venv_path) if venv_path.exists() else None,
            has_requirements=requirements_file.exists(),
            dependencies_installed=project.dependencies_installed,
            is_running=is_running,
            process_pid=process_pid,
            files_count=files_count,
        )
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all registered projects."""
        result = []
        for project in self.projects.values():
            status = self.get_status(project.id)
            result.append({
                **project.to_dict(),
                "status": status.to_dict(),
            })
        return result
    
    def get_templates(self) -> List[Dict[str, str]]:
        """List available project templates."""
        return [
            {
                "id": template_id,
                "name": template["name"],
                "description": template["description"],
            }
            for template_id, template in PROJECT_TEMPLATES.items()
        ]
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project and its files."""
        project = self.projects.get(project_id)
        if not project:
            return False
        
        # Stop if running
        await self.stop_project(project_id)
        
        # Remove directory
        if project.path.exists():
            shutil.rmtree(project.path)
        
        # Unregister
        del self.projects[project_id]
        self._save_projects()
        
        return True


# =============================================================================
# Singleton
# =============================================================================

_manager: Optional[ProjectManager] = None


def get_project_manager() -> ProjectManager:
    """Get the singleton project manager instance."""
    global _manager
    if _manager is None:
        _manager = ProjectManager()
    return _manager

