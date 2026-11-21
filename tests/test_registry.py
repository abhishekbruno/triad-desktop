import pytest
from app.core.agent_registry import AgentRegistry
from app.models.agent import AgentStatus, WindowCandidate


def test_registry_initialization():
    registry = AgentRegistry()
    conns = registry.get_all_connections()
    assert set(conns.keys()) == {"chatgpt", "claude", "gemini"}
    for conn in conns.values():
        assert conn.status == AgentStatus.MISSING
    assert registry.bound_count == 0
    assert registry.get_summary_text() == "0/3 applications bound"


def test_registry_binding_and_summary_transitions():
    registry = AgentRegistry()

    # Bind ChatGPT
    cand_gpt = WindowCandidate(
        hwnd=101, pid=501, title="ChatGPT", executable_name="chatgpt.exe"
    )
    registry.bind_candidate("chatgpt", cand_gpt)
    assert registry.bound_count == 1
    assert registry.get_summary_text() == "1/3 applications bound"
    assert registry.get_connection("chatgpt").status == AgentStatus.BOUND

    # Bind Claude
    cand_claude = WindowCandidate(
        hwnd=102, pid=502, title="Claude", executable_name="claude.exe"
    )
    registry.bind_candidate("claude", cand_claude)
    assert registry.bound_count == 2
    assert registry.get_summary_text() == "2/3 applications bound"

    # Bind Gemini
    cand_gemini = WindowCandidate(
        hwnd=103, pid=503, title="Gemini", executable_name="gemini.exe"
    )
    registry.bind_candidate("gemini", cand_gemini)
    assert registry.bound_count == 3
    assert registry.get_summary_text() == "3/3 Desktop Applications Bound — Phase 1 Ready"


def test_registry_disconnect_and_stale():
    registry = AgentRegistry()
    cand = WindowCandidate(hwnd=101, pid=501, title="ChatGPT", executable_name="chatgpt.exe")
    registry.bind_candidate("chatgpt", cand)
    assert registry.get_connection("chatgpt").status == AgentStatus.BOUND

    # Mark stale
    registry.mark_stale("chatgpt", reason="Window closed")
    assert registry.get_connection("chatgpt").status == AgentStatus.STALE
    assert registry.bound_count == 0

    # Disconnect
    registry.disconnect("chatgpt")
    assert registry.get_connection("chatgpt").status == AgentStatus.MISSING
    assert registry.get_connection("chatgpt").window_handle is None


def test_registry_subscription_listener():
    registry = AgentRegistry()
    notifications = []

    def on_change(agent_id, conn):
        notifications.append((agent_id, conn.status))

    registry.subscribe(on_change)
    cand = WindowCandidate(hwnd=201, pid=601, title="Claude", executable_name="claude.exe")
    registry.bind_candidate("claude", cand)

    assert len(notifications) == 1
    assert notifications[0] == ("claude", AgentStatus.BOUND)

