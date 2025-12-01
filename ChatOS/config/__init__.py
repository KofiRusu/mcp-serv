"""ChatOS configuration module."""

# Import settings from new settings module
from .settings import settings, Settings

# Re-export all constants from the legacy config.py for backwards compatibility
from pathlib import Path

# Get the parent directory (ChatOS) and import from config.py
_config_module_path = Path(__file__).parent.parent / "config.py"
if _config_module_path.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("_legacy_config", _config_module_path)
    _legacy_config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_legacy_config)
    
    # Re-export ALL constants from legacy config
    API_PREFIX = _legacy_config.API_PREFIX
    COMMAND_MODES = _legacy_config.COMMAND_MODES
    COUNCIL_STRATEGY = _legacy_config.COUNCIL_STRATEGY
    DATA_DIR = _legacy_config.DATA_DIR
    DEEPTHINKING_ITERATIONS = _legacy_config.DEEPTHINKING_ITERATIONS
    DEEPTHINKING_PROMPTS = _legacy_config.DEEPTHINKING_PROMPTS
    DEFAULT_HOST = _legacy_config.DEFAULT_HOST
    DEFAULT_PORT = _legacy_config.DEFAULT_PORT
    MEMORY_MAX_TURNS = _legacy_config.MEMORY_MAX_TURNS
    MODEL_BEHAVIORS = _legacy_config.MODEL_BEHAVIORS
    NUM_COUNCIL_MODELS = _legacy_config.NUM_COUNCIL_MODELS
    PACKAGE_DIR = _legacy_config.PACKAGE_DIR
    RAG_FILE_EXTENSIONS = _legacy_config.RAG_FILE_EXTENSIONS
    RAG_MIN_QUERY_LENGTH = _legacy_config.RAG_MIN_QUERY_LENGTH
    RAG_SNIPPET_MAX_LENGTH = _legacy_config.RAG_SNIPPET_MAX_LENGTH
    RESEARCH_DOMAINS = _legacy_config.RESEARCH_DOMAINS
    RESEARCH_MAX_SOURCES = _legacy_config.RESEARCH_MAX_SOURCES
    RESEARCH_SNIPPET_LENGTH = _legacy_config.RESEARCH_SNIPPET_LENGTH
    SANDBOX_ALLOWED_EXTENSIONS = _legacy_config.SANDBOX_ALLOWED_EXTENSIONS
    SANDBOX_DIR = _legacy_config.SANDBOX_DIR
    SANDBOX_MAX_FILE_SIZE = _legacy_config.SANDBOX_MAX_FILE_SIZE
    STATIC_DIR = _legacy_config.STATIC_DIR
    SWARM_AGENTS = _legacy_config.SWARM_AGENTS
    TEMPLATES_DIR = _legacy_config.TEMPLATES_DIR
    
    # VSCode Sandbox configuration
    SANDBOX_PROJECT_ROOTS = _legacy_config.SANDBOX_PROJECT_ROOTS
    CODE_SERVER_PORT = _legacy_config.CODE_SERVER_PORT
    CODE_SERVER_HOST = _legacy_config.CODE_SERVER_HOST
    CODE_SERVER_AUTH = _legacy_config.CODE_SERVER_AUTH
    SANDBOX_ALLOWED_COMMANDS = _legacy_config.SANDBOX_ALLOWED_COMMANDS
    SANDBOX_COMMAND_TIMEOUT = _legacy_config.SANDBOX_COMMAND_TIMEOUT
    SANDBOX_MAX_OUTPUT_SIZE = _legacy_config.SANDBOX_MAX_OUTPUT_SIZE

__all__ = [
    "settings",
    "Settings",
    "API_PREFIX",
    "COMMAND_MODES",
    "COUNCIL_STRATEGY",
    "DATA_DIR",
    "DEEPTHINKING_ITERATIONS",
    "DEEPTHINKING_PROMPTS",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "MEMORY_MAX_TURNS",
    "MODEL_BEHAVIORS",
    "NUM_COUNCIL_MODELS",
    "PACKAGE_DIR",
    "RAG_FILE_EXTENSIONS",
    "RAG_MIN_QUERY_LENGTH",
    "RAG_SNIPPET_MAX_LENGTH",
    "RESEARCH_DOMAINS",
    "RESEARCH_MAX_SOURCES",
    "RESEARCH_SNIPPET_LENGTH",
    "SANDBOX_ALLOWED_EXTENSIONS",
    "SANDBOX_DIR",
    "SANDBOX_MAX_FILE_SIZE",
    "STATIC_DIR",
    "SWARM_AGENTS",
    "TEMPLATES_DIR",
    # VSCode Sandbox
    "SANDBOX_PROJECT_ROOTS",
    "CODE_SERVER_PORT",
    "CODE_SERVER_HOST",
    "CODE_SERVER_AUTH",
    "SANDBOX_ALLOWED_COMMANDS",
    "SANDBOX_COMMAND_TIMEOUT",
    "SANDBOX_MAX_OUTPUT_SIZE",
]
