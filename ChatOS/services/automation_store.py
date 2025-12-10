"""
Automation Store - Persistent storage for user-created automations.

Stores automation configs, generated code, and deployment status.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


class AutomationType(str, Enum):
    # Data Collection
    SCRAPER = "scraper"
    
    # Trading & Execution
    TRADING_BOT = "trading_bot"
    STRATEGY = "strategy"
    
    # Analysis & Signals
    SIGNAL = "signal"
    INDICATOR = "indicator"
    ANALYTICS = "analytics"
    
    # Risk & Monitoring
    RISK = "risk"
    ALERT = "alert"
    
    # Testing
    BACKTEST = "backtest"


class AutomationStatus(str, Enum):
    DRAFT = "draft"
    TESTING = "testing"
    RUNNING = "running"
    DEPLOYED = "deployed"
    STOPPED = "stopped"
    ERROR = "error"
    PAUSED = "paused"


class BlockType(str, Enum):
    # Data blocks
    SOURCE = "source"
    TRANSFORM = "transform"
    OUTPUT = "output"
    
    # Logic blocks
    CONDITION = "condition"
    LOOP = "loop"
    
    # Trading blocks
    ENTRY = "entry"
    EXIT = "exit"
    ORDER = "order"
    POSITION = "position"
    
    # Analysis blocks
    INDICATOR = "indicator"
    SIGNAL = "signal"
    FILTER = "filter"
    AGGREGATE = "aggregate"
    
    # Alert blocks
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"
    
    # Risk blocks
    RISK_CHECK = "risk_check"
    POSITION_SIZE = "position_size"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class DeploymentType(str, Enum):
    """How the automation is deployed/executed."""
    DOCKER = "docker"           # Runs in Docker container
    PROCESS = "process"         # Runs as local subprocess
    SCHEDULED = "scheduled"     # Runs on schedule (cron)
    WEBHOOK_TRIGGER = "webhook" # Triggered by webhook
    REALTIME = "realtime"       # Runs continuously with real-time data


class AutomationBlock(BaseModel):
    """A single block in the automation flow."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: BlockType
    name: str
    config: Dict[str, Any] = Field(default_factory=dict)
    position: Dict[str, float] = Field(default_factory=lambda: {"x": 0, "y": 0})
    connections: List[str] = Field(default_factory=list)  # IDs of connected blocks


class Automation(BaseModel):
    """Full automation definition."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str = ""
    type: AutomationType = AutomationType.SCRAPER
    status: AutomationStatus = AutomationStatus.DRAFT
    deployment_type: DeploymentType = DeploymentType.DOCKER
    
    # Visual flow
    blocks: List[AutomationBlock] = Field(default_factory=list)
    
    # Generated artifacts
    generated_code: Optional[str] = None
    docker_image: Optional[str] = None
    container_id: Optional[str] = None
    process_id: Optional[int] = None  # For subprocess deployments
    
    # Config for quick access
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Trading-specific
    paper_trading: bool = True  # Safety default
    exchange: Optional[str] = None
    symbols: List[str] = Field(default_factory=list)
    
    # Schedule (for scheduled deployments)
    schedule_cron: Optional[str] = None  # e.g., "*/5 * * * *" for every 5 min
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_run: Optional[datetime] = None
    run_count: int = 0
    error_message: Optional[str] = None
    
    # Performance tracking
    total_pnl: float = 0.0
    win_rate: Optional[float] = None
    total_trades: int = 0
    
    # Logs
    logs: List[str] = Field(default_factory=list)


class AutomationStore:
    """Manages persistent storage of automations."""
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / "ChatOS-v2.0" / "sandbox-ui" / "data" / "automations"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.automations_file = self.data_dir / "automations.json"
        self._automations: Dict[str, Automation] = {}
        self._load()
    
    def _load(self):
        """Load automations from disk."""
        if self.automations_file.exists():
            try:
                data = json.loads(self.automations_file.read_text())
                for item in data:
                    automation = Automation(**item)
                    self._automations[automation.id] = automation
            except Exception as e:
                print(f"Error loading automations: {e}")
                self._automations = {}
    
    def _save(self):
        """Save automations to disk."""
        data = [a.model_dump(mode="json") for a in self._automations.values()]
        self.automations_file.write_text(json.dumps(data, indent=2, default=str))
    
    def create(self, automation: Automation) -> Automation:
        """Create a new automation."""
        automation.id = str(uuid.uuid4())
        automation.created_at = datetime.utcnow()
        automation.updated_at = datetime.utcnow()
        self._automations[automation.id] = automation
        self._save()
        return automation
    
    def get(self, automation_id: str) -> Optional[Automation]:
        """Get an automation by ID."""
        return self._automations.get(automation_id)
    
    def list_all(self, type_filter: Optional[AutomationType] = None) -> List[Automation]:
        """List all automations, optionally filtered by type."""
        automations = list(self._automations.values())
        if type_filter:
            automations = [a for a in automations if a.type == type_filter]
        return sorted(automations, key=lambda a: a.updated_at, reverse=True)
    
    def update(self, automation_id: str, updates: Dict[str, Any]) -> Optional[Automation]:
        """Update an existing automation."""
        if automation_id not in self._automations:
            return None
        
        automation = self._automations[automation_id]
        for key, value in updates.items():
            if hasattr(automation, key):
                setattr(automation, key, value)
        automation.updated_at = datetime.utcnow()
        self._save()
        return automation
    
    def delete(self, automation_id: str) -> bool:
        """Delete an automation."""
        if automation_id in self._automations:
            del self._automations[automation_id]
            self._save()
            return True
        return False
    
    def add_log(self, automation_id: str, log_message: str) -> bool:
        """Add a log entry to an automation."""
        if automation_id in self._automations:
            timestamp = datetime.utcnow().isoformat()
            self._automations[automation_id].logs.append(f"[{timestamp}] {log_message}")
            # Keep only last 100 logs
            self._automations[automation_id].logs = self._automations[automation_id].logs[-100:]
            self._save()
            return True
        return False
    
    def set_status(self, automation_id: str, status: AutomationStatus, error: Optional[str] = None) -> bool:
        """Update automation status."""
        if automation_id in self._automations:
            self._automations[automation_id].status = status
            self._automations[automation_id].error_message = error
            self._automations[automation_id].updated_at = datetime.utcnow()
            self._save()
            return True
        return False


# Singleton instance
_store: Optional[AutomationStore] = None

def get_automation_store() -> AutomationStore:
    """Get the singleton automation store instance."""
    global _store
    if _store is None:
        _store = AutomationStore()
    return _store

