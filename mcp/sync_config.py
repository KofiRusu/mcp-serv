"""
Sync Configuration Management
Handles loading and validating sync configuration from JSON
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class SyncConfig:
    """Manages sync daemon configuration"""
    
    DEFAULT_CONFIG_PATH = Path.home() / ".cursor" / "sync_config.json"
    
    # Default configurations for each machine
    MACOS_CONFIG = {
        "machine_id": "macos-kofirusu",
        "remote_host": "kr@192.168.18.40",
        "remote_db_path": "/home/kr/Desktop/cursor-mcp/data/mcp/memories.db",
        "local_db_path": "/Users/kofirusu/Desktop/Aux./linux mcp-server/cursor-mcp/data/mcp/memories.db",
        "sync_interval_seconds": 2
    }
    
    LINUX_CONFIG = {
        "machine_id": "linux-kr",
        "remote_host": "kofirusu@192.168.1.100",  # Will need to be set
        "remote_db_path": "/Users/kofirusu/Desktop/Aux./linux mcp-server/cursor-mcp/data/mcp/memories.db",
        "local_db_path": "/home/kr/Desktop/cursor-mcp/data/mcp/memories.db",
        "sync_interval_seconds": 2
    }
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize configuration"""
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self.config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> bool:
        """Load configuration from file"""
        try:
            if self.config_path.exists():
                with open(self.config_path) as f:
                    self.config = json.load(f)
                logger.info(f"Loaded config from {self.config_path}")
                return True
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return False
    
    def save(self) -> bool:
        """Save configuration to file"""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved config to {self.config_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value"""
        self.config[key] = value
    
    def validate(self) -> tuple[bool, str]:
        """Validate configuration"""
        required_keys = [
            "machine_id",
            "remote_host",
            "remote_db_path",
            "local_db_path",
            "sync_interval_seconds"
        ]
        
        missing_keys = [key for key in required_keys if key not in self.config]
        if missing_keys:
            return False, f"Missing required config keys: {missing_keys}"
        
        # Validate machine_id
        machine_id = self.config["machine_id"]
        if not machine_id or len(machine_id) == 0:
            return False, "machine_id cannot be empty"
        
        # Validate sync interval
        try:
            interval = int(self.config["sync_interval_seconds"])
            if interval < 1 or interval > 300:
                return False, "sync_interval_seconds must be between 1 and 300"
        except (ValueError, TypeError):
            return False, "sync_interval_seconds must be an integer"
        
        return True, "Configuration is valid"
    
    def __repr__(self) -> str:
        """String representation"""
        return f"SyncConfig(machine_id={self.config.get('machine_id')}, path={self.config_path})"


def create_default_config(machine_type: str = "macos") -> SyncConfig:
    """Create default configuration for a machine type"""
    config = SyncConfig()
    
    if machine_type.lower() == "macos":
        config.config = SyncConfig.MACOS_CONFIG.copy()
    elif machine_type.lower() == "linux":
        config.config = SyncConfig.LINUX_CONFIG.copy()
    else:
        raise ValueError(f"Unknown machine type: {machine_type}")
    
    return config


def get_or_create_config(config_path: Optional[str] = None) -> tuple[SyncConfig, bool]:
    """
    Get existing config or create default
    
    Returns:
        (config, is_new) tuple
    """
    config = SyncConfig(config_path)
    
    if config.config:
        logger.info("Existing config found")
        return config, False
    else:
        # Create default based on machine type
        logger.warning("No config found, creating default")
        # Default to macOS
        config.config = SyncConfig.MACOS_CONFIG.copy()
        config.save()
        return config, True
