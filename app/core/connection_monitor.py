import threading
import time
from typing import Callable, Optional
import psutil

from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.window_manager import WindowManager
from app.models.agent import AgentStatus
from app.storage.database import DatabaseManager
from app.utils.logging import get_logger

logger = get_logger("monitor")


class ConnectionMonitor:
    """Monitors running applications and bound windows.

    Responsibilities:
    - Detect when a bound application closes or its process terminates
    - Detect when an HWND becomes invalid
    - Detect application restarts with new PID/HWND
    - Update AgentRegistry and SQLite audit log
    - Runs bounded, efficient background polling (never high-frequency busy wait)
    """

    def __init__(
        self,
        registry: AgentRegistry,
        discovery_service: AppDiscoveryService,
        window_manager: WindowManager,
        database_manager: Optional[DatabaseManager] = None,
        poll_interval_sec: float = 1.5,
    ):
        self.registry = registry
        self.discovery = discovery_service
        self.window_mgr = window_manager
        self.db = database_manager
        self.poll_interval = poll_interval_sec

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._on_tick_callback: Optional[Callable[[], None]] = None

    def set_tick_callback(self, callback: Callable[[], None]) -> None:
        """Sets an optional callback invoked at the end of each monitor cycle."""
        self._on_tick_callback = callback

    def check_connections_once(self) -> None:
        """Performs a single evaluation pass across all agents."""
        connections = self.registry.get_all_connections()

        for agent_id, conn in connections.items():
            if conn.status == AgentStatus.BOUND:
                # 1. Validate Window Handle
                is_valid_hwnd = self.window_mgr.is_window_valid(conn.window_handle)
                if not is_valid_hwnd:
                    self.registry.mark_stale(
                        agent_id,
                        reason=f"Window handle {conn.window_handle} no longer valid",
                    )
                    if self.db:
                        self.db.log_discovery_event(
                            agent_id=agent_id,
                            event_type="WINDOW_INVALID",
                            executable_name=conn.executable_path,
                            details=f"HWND {conn.window_handle} invalidated",
                        )
                    continue

                # 2. Validate Process
                if conn.process_id:
                    if not psutil.pid_exists(conn.process_id):
                        self.registry.mark_stale(
                            agent_id,
                            reason=f"Process PID {conn.process_id} terminated",
                        )
                        if self.db:
                            self.db.log_discovery_event(
                                agent_id=agent_id,
                                event_type="PROCESS_TERMINATED",
                                details=f"PID {conn.process_id} terminated",
                            )
                        continue

            elif conn.status in (AgentStatus.MISSING, AgentStatus.STALE):
                # Lightweight check to see if an application became available
                # (handled during global scan or periodic check)
                pass

        if self._on_tick_callback:
            try:
                self._on_tick_callback()
            except Exception as e:
                logger.error("Error in monitor tick callback: %s", e)

    def start(self) -> None:
        """Starts the background monitoring thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop,
                name="TRIAD-ConnectionMonitor",
                daemon=True,
            )
            self._thread.start()
            logger.info("ConnectionMonitor thread started (interval: %.1fs)", self.poll_interval)

    def stop(self) -> None:
        """Stops the monitoring thread."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
            logger.info("ConnectionMonitor thread stopped")

    def _run_loop(self) -> None:
        while self._running:
            try:
                self.check_connections_once()
            except Exception as e:
                logger.error("Error in monitoring cycle: %s", e)
            time.sleep(self.poll_interval)

