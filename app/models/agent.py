from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class AgentStatus(str, Enum):
    """Lifecycle status of a desktop agent application."""
    MISSING = "missing"      # Not running / not found on machine
    DETECTED = "detected"    # Process and candidate window identified
    BOUND = "bound"          # Actively registered and bound to TRIAD
    STALE = "stale"          # Previously bound, but window or process is gone


@dataclass
class AgentConnection:
    """Connection information for a registered agent application."""
    agent_id: str
    display_name: str
    process_id: Optional[int]
    window_handle: Optional[int]
    executable_path: Optional[str]
    status: AgentStatus


@dataclass
class WindowCandidate:
    """Non-sensitive metadata of an identified candidate window."""
    hwnd: int
    pid: int
    title: str
    executable_name: str
    executable_path: Optional[str] = None
    package_name: Optional[str] = None
    is_visible: bool = True
    is_minimized: bool = False
    confidence: float = 0.0
    match_reason: str = ""


@dataclass
class AgentAppDefinition:
    """Static configuration profile for discovering supported desktop applications."""
    agent_id: str
    display_name: str
    accent_color: str
    known_executables: List[str]
    known_title_signatures: List[str]
    package_family_names: List[str] = field(default_factory=list)
    pwa_app_patterns: List[str] = field(default_factory=list)


# Static profiles for the three target desktop AI applications
SUPPORTED_AGENTS: Dict[str, AgentAppDefinition] = {
    "chatgpt": AgentAppDefinition(
        agent_id="chatgpt",
        display_name="ChatGPT Desktop",
        accent_color="#10a37f",
        known_executables=["chatgpt.exe", "chatgpt desktop.exe"],
        known_title_signatures=["ChatGPT", "OpenAI ChatGPT"],
        package_family_names=["OpenAI.ChatGPT-Desktop", "OpenAI.ChatGPT"],
        pwa_app_patterns=["chatgpt.com", "chat.openai.com"],
    ),
    "claude": AgentAppDefinition(
        agent_id="claude",
        display_name="Claude Desktop",
        accent_color="#d97706",
        known_executables=["claude.exe"],
        known_title_signatures=["Claude", "Claude Desktop"],
        package_family_names=["Anthropic.Claude"],
        pwa_app_patterns=["claude.ai"],
    ),
    "gemini": AgentAppDefinition(
        agent_id="gemini",
        display_name="Gemini Desktop",
        accent_color="#1a73e8",
        known_executables=["gemini.exe", "google gemini.exe"],
        known_title_signatures=["Gemini", "Google Gemini"],
        package_family_names=[],
        pwa_app_patterns=["gemini.google.com"],
    ),
}

