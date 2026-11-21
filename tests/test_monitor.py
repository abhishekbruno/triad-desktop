import pytest
from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.connection_monitor import ConnectionMonitor
from app.core.window_manager import WindowManager
from app.models.agent import AgentStatus, WindowCandidate


def test_monitor_detects_closed_window(mocker):
    registry = AgentRegistry()
    discovery = AppDiscoveryService()
    win_mgr = WindowManager()

    monitor = ConnectionMonitor(
        registry=registry,
        discovery_service=discovery,
        window_manager=win_mgr,
        poll_interval_sec=0.1,
    )

    # Bind an agent to HWND 999
    cand = WindowCandidate(hwnd=999, pid=4000, title="ChatGPT", executable_name="chatgpt.exe")
    registry.bind_candidate("chatgpt", cand)
    assert registry.get_connection("chatgpt").status == AgentStatus.BOUND

    # Mock window validity returning False (window was closed)
    mocker.patch.object(win_mgr, "is_window_valid", return_value=False)

    monitor.check_connections_once()

    conn = registry.get_connection("chatgpt")
    assert conn.status == AgentStatus.STALE


def test_monitor_detects_terminated_process(mocker):
    registry = AgentRegistry()
    discovery = AppDiscoveryService()
    win_mgr = WindowManager()

    monitor = ConnectionMonitor(
        registry=registry,
        discovery_service=discovery,
        window_manager=win_mgr,
        poll_interval_sec=0.1,
    )

    cand = WindowCandidate(hwnd=888, pid=99999, title="Claude", executable_name="claude.exe")
    registry.bind_candidate("claude", cand)

    # Window is valid, but process does not exist
    mocker.patch.object(win_mgr, "is_window_valid", return_value=True)
    mocker.patch("psutil.pid_exists", return_value=False)

    monitor.check_connections_once()

    conn = registry.get_connection("claude")
    assert conn.status == AgentStatus.STALE

