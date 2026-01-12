"""
Automation Deployer - Deploys automations as Docker containers.

Generates Dockerfiles and manages container lifecycle.
"""

import asyncio
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from .automation_store import (
    Automation, AutomationStatus,
    get_automation_store
)


DOCKERFILE_TEMPLATE = '''# Auto-generated Dockerfile for {name}
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir websockets httpx aiofiles

# Copy the automation script
COPY automation.py /app/automation.py

# Create data directory
RUN mkdir -p /app/data

# Run the automation
CMD ["python", "-u", "automation.py"]
'''

DOCKER_COMPOSE_TEMPLATE = '''# Auto-generated docker-compose for {name}
version: '3.8'

services:
  {service_name}:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: chatos-automation-{automation_id}
    restart: unless-stopped
    volumes:
      - {data_dir}:/app/data
    environment:
      - PYTHONUNBUFFERED=1
    networks:
      - chatos-automations

networks:
  chatos-automations:
    name: chatos-automations
    external: true
'''


class AutomationDeployer:
    """Manages Docker deployment of automations."""
    
    def __init__(self):
        self._store = get_automation_store()
        self._deploy_dir = Path.home() / "ChatOS-v2.0" / "sandbox-ui" / "data" / "automations" / "deployments"
        self._deploy_dir.mkdir(parents=True, exist_ok=True)
    
    async def deploy(self, automation_id: str) -> Dict:
        """Deploy an automation as a Docker container."""
        automation = self._store.get(automation_id)
        if not automation:
            return {"success": False, "error": "Automation not found"}
        
        if not automation.generated_code:
            return {"success": False, "error": "No generated code to deploy"}
        
        # Create deployment directory
        deploy_path = self._deploy_dir / automation_id
        deploy_path.mkdir(exist_ok=True)
        
        # Data output directory
        data_dir = Path.home() / "ChatOS-v2.0" / "sandbox-ui" / "data" / "automations" / automation_id
        data_dir.mkdir(parents=True, exist_ok=True)
        
        # Write automation code
        code_file = deploy_path / "automation.py"
        code_file.write_text(automation.generated_code)
        
        # Generate Dockerfile
        dockerfile = deploy_path / "Dockerfile"
        dockerfile.write_text(DOCKERFILE_TEMPLATE.format(name=automation.name))
        
        # Generate docker-compose
        service_name = automation.name.lower().replace(" ", "-").replace("_", "-")[:20]
        compose_file = deploy_path / "docker-compose.yml"
        compose_file.write_text(DOCKER_COMPOSE_TEMPLATE.format(
            name=automation.name,
            service_name=service_name,
            automation_id=automation_id,
            data_dir=str(data_dir)
        ))
        
        try:
            # Ensure network exists
            await self._ensure_network()
            
            # Build image
            self._store.add_log(automation_id, "Building Docker image...")
            build_result = await self._run_docker_command(
                ["docker", "build", "-t", f"chatos-automation-{automation_id}", "."],
                cwd=str(deploy_path)
            )
            
            if build_result["returncode"] != 0:
                error = build_result.get("stderr", "Build failed")
                self._store.set_status(automation_id, AutomationStatus.ERROR, error)
                return {"success": False, "error": error}
            
            # Run container
            self._store.add_log(automation_id, "Starting container...")
            container_name = f"chatos-automation-{automation_id}"
            
            # Stop existing container if any
            await self._run_docker_command(["docker", "rm", "-f", container_name])
            
            # Start new container
            run_result = await self._run_docker_command([
                "docker", "run", "-d",
                "--name", container_name,
                "--restart", "unless-stopped",
                "-v", f"{data_dir}:/app/data",
                "--network", "chatos-automations",
                f"chatos-automation-{automation_id}"
            ])
            
            if run_result["returncode"] != 0:
                error = run_result.get("stderr", "Failed to start container")
                self._store.set_status(automation_id, AutomationStatus.ERROR, error)
                return {"success": False, "error": error}
            
            container_id = run_result.get("stdout", "").strip()
            
            # Update automation
            self._store.update(automation_id, {
                "docker_image": f"chatos-automation-{automation_id}",
                "container_id": container_id,
                "status": AutomationStatus.DEPLOYED
            })
            self._store.add_log(automation_id, f"Deployed successfully (container: {container_id[:12]})")
            
            return {
                "success": True,
                "container_id": container_id,
                "image": f"chatos-automation-{automation_id}",
                "data_dir": str(data_dir)
            }
            
        except Exception as e:
            self._store.set_status(automation_id, AutomationStatus.ERROR, str(e))
            return {"success": False, "error": str(e)}
    
    async def undeploy(self, automation_id: str) -> Dict:
        """Stop and remove a deployed automation."""
        automation = self._store.get(automation_id)
        if not automation:
            return {"success": False, "error": "Automation not found"}
        
        container_name = f"chatos-automation-{automation_id}"
        
        try:
            # Stop and remove container
            await self._run_docker_command(["docker", "stop", container_name])
            await self._run_docker_command(["docker", "rm", container_name])
            
            # Update status
            self._store.update(automation_id, {
                "container_id": None,
                "status": AutomationStatus.STOPPED
            })
            self._store.add_log(automation_id, "Container stopped and removed")
            
            return {"success": True}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_container_status(self, automation_id: str) -> Dict:
        """Get status of a deployed container."""
        container_name = f"chatos-automation-{automation_id}"
        
        result = await self._run_docker_command([
            "docker", "inspect", container_name,
            "--format", "{{.State.Status}}"
        ])
        
        if result["returncode"] != 0:
            return {"running": False, "status": "not_found"}
        
        status = result.get("stdout", "").strip()
        return {
            "running": status == "running",
            "status": status,
            "container_name": container_name
        }
    
    async def get_container_logs(self, automation_id: str, lines: int = 100) -> str:
        """Get logs from a deployed container."""
        container_name = f"chatos-automation-{automation_id}"
        
        result = await self._run_docker_command([
            "docker", "logs", "--tail", str(lines), container_name
        ])
        
        return result.get("stdout", "") + result.get("stderr", "")
    
    async def restart_container(self, automation_id: str) -> Dict:
        """Restart a deployed container."""
        container_name = f"chatos-automation-{automation_id}"
        
        result = await self._run_docker_command(["docker", "restart", container_name])
        
        if result["returncode"] == 0:
            self._store.add_log(automation_id, "Container restarted")
            return {"success": True}
        
        return {"success": False, "error": result.get("stderr", "Restart failed")}
    
    async def _ensure_network(self):
        """Ensure the automation network exists."""
        await self._run_docker_command([
            "docker", "network", "create", "chatos-automations"
        ])
    
    async def _run_docker_command(self, cmd: list, cwd: str = None) -> Dict:
        """Run a docker command asynchronously."""
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd
            )
            stdout, stderr = await process.communicate()
            
            return {
                "returncode": process.returncode,
                "stdout": stdout.decode() if stdout else "",
                "stderr": stderr.decode() if stderr else ""
            }
        except Exception as e:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": str(e)
            }


# Singleton
_deployer: Optional[AutomationDeployer] = None

def get_automation_deployer() -> AutomationDeployer:
    global _deployer
    if _deployer is None:
        _deployer = AutomationDeployer()
    return _deployer

