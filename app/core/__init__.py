"""TRIAD Core Engine Components."""
from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.connection_monitor import ConnectionMonitor
from app.core.window_manager import WindowManager

__all__ = [
    "AgentRegistry",
    "AppDiscoveryService",
    "ConnectionMonitor",
    "WindowManager",
]

