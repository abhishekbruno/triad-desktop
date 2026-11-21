from typing import Callable, Dict, List, Optional
from app.models.agent import (
    AgentAppDefinition,
    AgentConnection,
    AgentStatus,
    SUPPORTED_AGENTS,
    WindowCandidate,
)
from app.utils.logging import get_logger

logger = get_logger("agent_registry")


class AgentRegistry:
    """Manages the registration and connection state of the three target desktop AI applications.

    Maintains:
    - chatgpt (ChatGPT Desktop)
    - claude (Claude Desktop)
    - gemini (Gemini Desktop)

    Lifecycle states:
    - MISSING: Application not running / not found
    - DETECTED: Process and window candidate discovered
    - BOUND: Window actively registered and focusable by TRIAD
    - STALE: Previously bound window is invalid or process terminated
    """

    def __init__(self, agent_definitions: Optional[Dict[str, AgentAppDefinition]] = None):
        self.definitions = agent_definitions or SUPPORTED_AGENTS
        self._connections: Dict[str, AgentConnection] = {}
        self._listeners: List[Callable[[str, AgentConnection], None]] = []

        # Initialize all supported agents with MISSING status
        for agent_id, defn in self.definitions.items():
            self._connections[agent_id] = AgentConnection(
                agent_id=agent_id,
                display_name=defn.display_name,
                process_id=None,
                window_handle=None,
                executable_path=None,
                status=AgentStatus.MISSING,
            )

    def subscribe(self, callback: Callable[[str, AgentConnection], None]) -> None:
        """Registers a listener callback invoked whenever an agent state changes."""
        self._listeners.append(callback)

    def _notify(self, agent_id: str) -> None:
        conn = self._connections[agent_id]
        for cb in self._listeners:
            try:
                cb(agent_id, conn)
            except Exception as e:
                logger.error("Error invoking registry listener: %s", e)

    def get_connection(self, agent_id: str) -> Optional[AgentConnection]:
        """Returns the current connection object for an agent."""
        return self._connections.get(agent_id)

    def get_all_connections(self) -> Dict[str, AgentConnection]:
        """Returns all connection records."""
        return dict(self._connections)

    def set_detected(
        self,
        agent_id: str,
        pid: Optional[int] = None,
        hwnd: Optional[int] = None,
        exec_path: Optional[str] = None,
    ) -> AgentConnection:
        """Marks an agent as detected but not yet bound."""
        conn = self._connections[agent_id]
        # Only transition to DETECTED if not already BOUND
        if conn.status != AgentStatus.BOUND:
            conn.status = AgentStatus.DETECTED
            conn.process_id = pid
            conn.window_handle = hwnd
            conn.executable_path = exec_path
            logger.info("Agent '%s' status updated to DETECTED", agent_id)
            self._notify(agent_id)
        return conn

    def bind_candidate(self, agent_id: str, candidate: WindowCandidate) -> AgentConnection:
        """Binds an agent to a specific validated WindowCandidate."""
        if agent_id not in self._connections:
            raise ValueError(f"Unknown agent id: {agent_id}")

        conn = self._connections[agent_id]
        conn.process_id = candidate.pid
        conn.window_handle = candidate.hwnd
        conn.executable_path = candidate.executable_path
        conn.status = AgentStatus.BOUND
        logger.info(
            "Agent '%s' BOUND to PID %s, HWND %s (window: '%s')",
            agent_id,
            candidate.pid,
            candidate.hwnd,
            candidate.title,
        )
        self._notify(agent_id)
        return conn

    def bind_manual(
        self,
        agent_id: str,
        pid: int,
        hwnd: int,
        exec_path: Optional[str] = None,
    ) -> AgentConnection:
        """Directly binds an agent to specific runtime parameters."""
        if agent_id not in self._connections:
            raise ValueError(f"Unknown agent id: {agent_id}")

        conn = self._connections[agent_id]
        conn.process_id = pid
        conn.window_handle = hwnd
        conn.executable_path = exec_path
        conn.status = AgentStatus.BOUND
        logger.info("Agent '%s' manually BOUND to PID %s, HWND %s", agent_id, pid, hwnd)
        self._notify(agent_id)
        return conn

    def mark_stale(self, agent_id: str, reason: str = "") -> AgentConnection:
        """Marks a previously bound agent as stale when its window or process disappears."""
        conn = self._connections[agent_id]
        if conn.status == AgentStatus.BOUND:
            conn.status = AgentStatus.STALE
            logger.warning("Agent '%s' marked STALE. Reason: %s", agent_id, reason)
            self._notify(agent_id)
        return conn

    def mark_missing(self, agent_id: str) -> AgentConnection:
        """Marks an agent as missing (not running / not found)."""
        conn = self._connections[agent_id]
        conn.status = AgentStatus.MISSING
        conn.process_id = None
        conn.window_handle = None
        conn.executable_path = None
        logger.info("Agent '%s' marked MISSING", agent_id)
        self._notify(agent_id)
        return conn

    def disconnect(self, agent_id: str) -> AgentConnection:
        """Unbinds and disconnects an agent."""
        if agent_id not in self._connections:
            raise ValueError(f"Unknown agent id: {agent_id}")

        conn = self._connections[agent_id]
        conn.status = AgentStatus.MISSING
        conn.process_id = None
        conn.window_handle = None
        conn.executable_path = None
        logger.info("Agent '%s' disconnected", agent_id)
        self._notify(agent_id)
        return conn

    def disconnect_all(self) -> None:
        """Disconnects all agents."""
        for agent_id in list(self._connections.keys()):
            self.disconnect(agent_id)

    @property
    def bound_count(self) -> int:
        """Returns the number of currently bound applications."""
        return sum(1 for c in self._connections.values() if c.status == AgentStatus.BOUND)

    @property
    def total_count(self) -> int:
        """Total number of registered agent slots (3)."""
        return len(self._connections)

    def get_summary_text(self) -> str:
        """Formats the Phase 1 workspace status summary."""
        count = self.bound_count
        total = self.total_count
        if count == total:
            return f"{count}/{total} Desktop Applications Bound — Phase 1 Ready"
        return f"{count}/{total} applications bound"

