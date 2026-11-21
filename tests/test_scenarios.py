"""Comprehensive Scenario Tests validating the 10 core requirements:
1. All three applications detected
2. Only ChatGPT running
3. No applications running
4. Multiple candidate windows
5. Application closes after registration
6. Application restarts
7. Invalid saved connection
8. Window focus failure
9. Unrelated process with misleading title
10. Configuration persists across restarts
"""

import tempfile
import os
import pytest

from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.connection_monitor import ConnectionMonitor
from app.core.window_manager import WindowManager
from app.models.agent import AgentStatus, WindowCandidate
from app.storage.database import DatabaseManager


# Scenario 1: All three applications detected
def test_scenario_1_all_three_detected(mocker):
    service = AppDiscoveryService()
    candidates = [
        WindowCandidate(101, 1001, "ChatGPT", "chatgpt.exe", is_visible=True),
        WindowCandidate(102, 1002, "Claude", "claude.exe", is_visible=True),
        WindowCandidate(103, 1003, "Gemini", "chrome.exe", is_visible=True),
    ]
    mocker.patch.object(service, "scan_desktop_windows", return_value=candidates)
    mocker.patch.object(
        service,
        "_get_process_cmdline",
        side_effect=lambda pid: ["--app=https://gemini.google.com"] if pid == 1003 else [],
    )

    grouped = service.discover_candidates()
    assert len(grouped["chatgpt"]) >= 1
    assert len(grouped["claude"]) >= 1
    assert len(grouped["gemini"]) >= 1


# Scenario 2: Only ChatGPT running
def test_scenario_2_only_chatgpt_running(mocker):
    service = AppDiscoveryService()
    candidates = [
        WindowCandidate(101, 1001, "ChatGPT", "chatgpt.exe", is_visible=True),
        WindowCandidate(901, 9001, "File Explorer", "explorer.exe", is_visible=True),
    ]
    mocker.patch.object(service, "scan_desktop_windows", return_value=candidates)

    grouped = service.discover_candidates()
    assert len(grouped["chatgpt"]) == 1
    assert len(grouped["claude"]) == 0
    assert len(grouped["gemini"]) == 0


# Scenario 3: No applications running
def test_scenario_3_no_applications_running(mocker):
    service = AppDiscoveryService()
    candidates = [
        WindowCandidate(901, 9001, "Notepad", "notepad.exe", is_visible=True),
        WindowCandidate(902, 9002, "Calculator", "CalculatorApp.exe", is_visible=True),
    ]
    mocker.patch.object(service, "scan_desktop_windows", return_value=candidates)

    grouped = service.discover_candidates()
    assert len(grouped["chatgpt"]) == 0
    assert len(grouped["claude"]) == 0
    assert len(grouped["gemini"]) == 0


# Scenario 4: Multiple candidate windows for one application
def test_scenario_4_multiple_candidate_windows(mocker):
    service = AppDiscoveryService()
    candidates = [
        WindowCandidate(101, 1001, "ChatGPT - Project Discussion", "chatgpt.exe", is_visible=True),
        WindowCandidate(102, 1001, "ChatGPT - Settings", "chatgpt.exe", is_visible=True),
    ]
    mocker.patch.object(service, "scan_desktop_windows", return_value=candidates)

    grouped = service.discover_candidates()
    assert len(grouped["chatgpt"]) == 2
    # Verify user can bind either window specifically
    registry = AgentRegistry()
    registry.bind_candidate("chatgpt", grouped["chatgpt"][0])
    assert registry.get_connection("chatgpt").window_handle == 101


# Scenario 5: Application closes after registration
def test_scenario_5_app_closes_after_registration(mocker):
    registry = AgentRegistry()
    win_mgr = WindowManager()
    monitor = ConnectionMonitor(registry, AppDiscoveryService(), win_mgr)

    cand = WindowCandidate(101, 1001, "ChatGPT", "chatgpt.exe")
    registry.bind_candidate("chatgpt", cand)
    assert registry.get_connection("chatgpt").status == AgentStatus.BOUND

    # App closes: window becomes invalid
    mocker.patch.object(win_mgr, "is_window_valid", return_value=False)
    monitor.check_connections_once()

    assert registry.get_connection("chatgpt").status == AgentStatus.STALE


# Scenario 6: Application restarts with new PID and HWND
def test_scenario_6_app_restarts(mocker):
    registry = AgentRegistry()
    win_mgr = WindowManager()
    service = AppDiscoveryService()
    monitor = ConnectionMonitor(registry, service, win_mgr)

    # Initial bind
    registry.bind_candidate("claude", WindowCandidate(201, 2001, "Claude", "claude.exe"))
    assert registry.get_connection("claude").status == AgentStatus.BOUND

    # Claude terminates
    mocker.patch.object(win_mgr, "is_window_valid", return_value=False)
    monitor.check_connections_once()
    assert registry.get_connection("claude").status == AgentStatus.STALE

    # Claude restarts with new PID 3001 and HWND 301
    new_cand = WindowCandidate(301, 3001, "Claude", "claude.exe")
    registry.bind_candidate("claude", new_cand)
    assert registry.get_connection("claude").status == AgentStatus.BOUND
    assert registry.get_connection("claude").process_id == 3001
    assert registry.get_connection("claude").window_handle == 301


# Scenario 7: Invalid saved connection (reboot / stale state)
def test_scenario_7_invalid_saved_connection():
    registry = AgentRegistry()
    # A fresh registry initializes all agents as MISSING, never blindly trusting stale handles
    conns = registry.get_all_connections()
    for agent_id, conn in conns.items():
        assert conn.status == AgentStatus.MISSING
        assert conn.window_handle is None
        assert conn.process_id is None


# Scenario 8: Window focus failure gracefully reported
def test_scenario_8_window_focus_failure(mocker):
    mocker.patch("app.core.window_manager.HAS_WIN32", True)
    mock_gui = mocker.patch("app.core.window_manager.win32gui")
    mock_gui.IsWindow.return_value = True
    mock_gui.SetForegroundWindow.side_effect = RuntimeError("Access Denied")

    success, msg = WindowManager.focus_window(999)
    assert not success
    assert "Access Denied" in msg


# Scenario 9: Unrelated process with misleading title
def test_scenario_9_unrelated_process_misleading_title():
    service = AppDiscoveryService()
    misleading_cand = WindowCandidate(
        hwnd=555,
        pid=5555,
        title="Search for ChatGPT, Claude, and Gemini Prompts",
        executable_name="chrome.exe",
        is_visible=True,
    )
    agent_id, conf, reason = service.classify_window(misleading_cand)
    assert agent_id is None
    assert conf == 0.0


# Scenario 10: Configuration persists across restarts
def test_scenario_10_config_persists_across_restarts():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
        tf.close()

    try:
        # Session 1: User binds ChatGPT preference
        db1 = DatabaseManager(db_path=db_path)
        db1.set_agent_preference(
            agent_id="chatgpt",
            display_name="ChatGPT Desktop",
            preferred_executable="ChatGPT.exe",
        )
        db1.set_setting("workspace_version", "1.0")

        # Session 2: Fresh launch with new DatabaseManager instance
        db2 = DatabaseManager(db_path=db_path)
        pref = db2.get_agent_preference("chatgpt")
        assert pref is not None
        assert pref["preferred_executable"] == "ChatGPT.exe"
        assert db2.get_setting("workspace_version") == "1.0"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
