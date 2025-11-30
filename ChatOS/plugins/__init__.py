"""
ChatOS Plugins Module.

Contains plugin integrations for external systems.
"""

from .persrm_bridge import PersRMBridge, get_persrm_reasoning

__all__ = ["PersRMBridge", "get_persrm_reasoning"]

