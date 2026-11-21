"""TRIAD Data Models."""
from app.models.agent import (
    AgentConnection,
    AgentStatus,
    WindowCandidate,
    AgentAppDefinition,
    SUPPORTED_AGENTS,
)

__all__ = [
    "AgentConnection",
    "AgentStatus",
    "WindowCandidate",
    "AgentAppDefinition",
    "SUPPORTED_AGENTS",
]

