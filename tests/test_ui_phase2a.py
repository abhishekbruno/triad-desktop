import os
import tempfile
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.session_manager import SessionManager
from app.core.window_manager import WindowManager
from app.models.agent import AgentStatus, WindowCandidate
from app.models.session import ReasoningMode, SessionState
from app.storage.database import DatabaseManager
from app.storage.session_repository import SessionRepository
from app.ui.main_window import MainWindow


@pytest.fixture
def temp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
        tf.close()
    db = DatabaseManager(db_path=db_path)
    yield db
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass


@pytest.fixture
def main_window(qapp, temp_db):
    registry = AgentRegistry()
    discovery = AppDiscoveryService()
    window_mgr = WindowManager()
    session_repo = SessionRepository(db=temp_db)
    session_mgr = SessionManager(repository=session_repo)

    window = MainWindow(
        registry=registry,
        discovery_service=discovery,
        window_manager=window_mgr,
        database=temp_db,
        session_manager=session_mgr,
        start_monitor=False,
    )
    yield window
    if window.monitor:
        window.monitor.stop()
    window.close()


def test_1_main_workspace_initialization(main_window):
    """Test 1: Main workspace initialization."""
    assert "TRIAD" in main_window.windowTitle()
    assert main_window.sidebar is not None
    assert main_window.stack.count() == 5
    assert main_window.workspace_page is not None
    assert len(main_window.workspace_page.agent_panels) == 3
    assert "chatgpt" in main_window.workspace_page.agent_panels
    assert "claude" in main_window.workspace_page.agent_panels
    assert "gemini" in main_window.workspace_page.agent_panels


def test_2_sidebar_navigation_and_collapse(main_window):
    """Test 2: Sidebar navigation switches pages and collapses cleanly."""
    # Navigate to Sessions
    main_window.sidebar.page_selected.emit("sessions")
    assert main_window.stack.currentIndex() == 1

    # Navigate to Connections
    main_window.sidebar.page_selected.emit("connections")
    assert main_window.stack.currentIndex() == 2

    # Navigate to Disagreement Map
    main_window.sidebar.page_selected.emit("disagreement")
    assert main_window.stack.currentIndex() == 3

    # Navigate to Settings
    main_window.sidebar.page_selected.emit("settings")
    assert main_window.stack.currentIndex() == 4

    # Navigate back to Workspace
    main_window.sidebar.page_selected.emit("workspace")
    assert main_window.stack.currentIndex() == 0

    # Test Sidebar collapse toggle
    assert main_window.sidebar.is_collapsed is False
    assert main_window.sidebar.width() == 230
    main_window.sidebar.toggle_collapse()
    assert main_window.sidebar.is_collapsed is True
    assert main_window.sidebar.width() == 64
    main_window.sidebar.toggle_collapse()
    assert main_window.sidebar.is_collapsed is False
    assert main_window.sidebar.width() == 230


def test_3_4_session_creation_and_persistence(main_window):
    """Test 3 & 4: Session creation from composer persists to SQLite."""
    composer = main_window.workspace_page.composer
    composer.title_input.setText("Cache Coherence Design")
    composer.question_editor.setPlainText("Compare MESI protocol vs Directory-based cache coherence.")

    # Trigger creation
    composer.btn_create.click()

    session = main_window.session_mgr.current_session
    assert session is not None
    assert session.title == "Cache Coherence Design"
    assert "MESI" in session.initial_question

    # Check persistence in database
    saved = main_window.session_repo.get_session(session.session_id)
    assert saved is not None
    assert saved.title == "Cache Coherence Design"

    # Check that events were logged in timeline
    events = main_window.session_mgr.get_timeline_events(session.session_id)
    assert len(events) >= 2


def test_5_session_reopening(main_window):
    """Test 5: Reopening an existing session restores workspace and logs event."""
    session = main_window.session_mgr.create_session(
        title="Kernel Memory Allocation",
        initial_question="Analyze slab vs buddy allocator performance tradeoffs.",
        mode=ReasoningMode.CODE_REVIEW,
    )

    # Reset workspace to fresh draft
    main_window.workspace_page.start_new_discussion()
    assert main_window.workspace_page.composer.title_input.text() == ""

    # Load session
    loaded = main_window.session_mgr.load_session(session.session_id)
    assert loaded is not None
    assert main_window.workspace_page.composer.title_input.text() == "Kernel Memory Allocation"
    assert "slab" in main_window.workspace_page.composer.question_editor.toPlainText()

    # Timeline includes reopen event
    events = main_window.session_mgr.get_timeline_events(session.session_id)
    event_types = [ev.event_type.value for ev in events]
    assert "session_reopened" in event_types


def test_6_session_renaming(main_window):
    """Test 6: Renaming a session updates storage and timeline."""
    session = main_window.session_mgr.create_session("Old Name", "Question")
    ok = main_window.session_mgr.rename_session(session.session_id, "New Architectural Review")
    assert ok is True
    assert main_window.session_mgr.current_session.title == "New Architectural Review"

    saved = main_window.session_repo.get_session(session.session_id)
    assert saved.title == "New Architectural Review"


def test_7_session_deletion(main_window):
    """Test 7: Deleting session removes record and clears current."""
    session = main_window.session_mgr.create_session("To Delete", "Delete question")
    sess_id = session.session_id
    assert main_window.session_mgr.current_session is not None

    ok = main_window.session_mgr.delete_session(sess_id)
    assert ok is True
    assert main_window.session_mgr.current_session is None
    assert main_window.session_repo.get_session(sess_id) is None


def test_8_session_search(main_window):
    """Test 8: Search sessions by title and question."""
    main_window.session_mgr.create_session("Paxos Protocol", "Explain Paxos leader election")
    main_window.session_mgr.create_session("Raft Consensus", "Explain log replication in Raft")

    # Search in sessions page
    main_window.sessions_page.search_input.setText("Paxos")
    assert len(main_window.sessions_page.sessions) == 1
    assert "Paxos" in main_window.sessions_page.sessions[0].title

    main_window.sessions_page.search_input.setText("replication")
    assert len(main_window.sessions_page.sessions) == 1
    assert "Raft" in main_window.sessions_page.sessions[0].title

    main_window.sessions_page.search_input.setText("")
    assert len(main_window.sessions_page.sessions) >= 2


def test_9_reasoning_mode_configuration(main_window):
    """Test 9: Reasoning mode configuration via sidebar and composer."""
    session = main_window.session_mgr.create_session("Test Mode Config", "Question", ReasoningMode.QUICK_CONSENSUS)
    assert session.mode == ReasoningMode.QUICK_CONSENSUS

    # Change mode via sidebar signal
    main_window.sidebar.mode_selected.emit("deep_debate")
    assert main_window.session_mgr.current_session.mode == ReasoningMode.DEEP_DEBATE
    assert "DEEP DEBATE" in main_window.header_mode_badge.text()


def test_10_agent_connection_status_binding(main_window):
    """Test 10: Agent connection status binding."""
    chatgpt_panel = main_window.workspace_page.agent_panels["chatgpt"]
    assert chatgpt_panel.conn_pill.text() == "MISSING"

    # Simulate discovery candidate and binding
    candidate = WindowCandidate(
        hwnd=0x12345,
        pid=9999,
        executable_name="ChatGPT.exe",
        title="ChatGPT - Architecture Chat",
        confidence=0.95,
        is_visible=True,
    )
    main_window.registry.bind_candidate("chatgpt", candidate)
    main_window.workspace_page.sync_agent_panels()

    assert chatgpt_panel.conn_pill.text() == "BOUND"
    assert "PID 9999" in chatgpt_panel.lbl_proc.text()
    assert chatgpt_panel.btn_focus.isEnabled() is True


def test_11_focus_button_behavior(main_window, monkeypatch):
    """Test 11: Focus button calls WindowManager.focus_window."""
    chatgpt_panel = main_window.workspace_page.agent_panels["chatgpt"]
    focused_handles = []

    def mock_focus(hwnd):
        focused_handles.append(hwnd)
        return True

    monkeypatch.setattr(main_window.window_mgr, "focus_window", mock_focus)

    candidate = WindowCandidate(hwnd=0x9999, pid=123, executable_name="ChatGPT.exe", title="Chat")
    chatgpt_panel.set_connection_status(AgentStatus.BOUND, candidate)

    chatgpt_panel.btn_focus.click()
    assert 0x9999 in focused_handles


def test_12_missing_application_handling(main_window):
    """Test 12: Missing application handling (e.g. Gemini)."""
    gemini_panel = main_window.workspace_page.agent_panels["gemini"]
    main_window.registry.mark_missing("gemini")
    gemini_panel.set_connection_status(AgentStatus.MISSING)

    assert gemini_panel.conn_pill.text() == "MISSING"
    assert gemini_panel.btn_focus.isEnabled() is False
    assert "Not detected" in gemini_panel.lbl_proc.text()


def test_13_timeline_event_ordering(main_window):
    """Test 13: Timeline event ordering is strictly chronological."""
    session = main_window.session_mgr.create_session("Timeline Test", "Question")
    timeline = main_window.workspace_page.timeline

    events = main_window.session_mgr.get_timeline_events(session.session_id)
    assert len(events) >= 2
    for i in range(len(events) - 1):
        assert events[i].timestamp <= events[i + 1].timestamp


def test_14_empty_discussion_states(main_window):
    """Test 14: Empty discussion states."""
    timeline = main_window.workspace_page.timeline
    timeline.clear_events()
    assert not timeline.empty_label.isHidden()
    assert "No discussion events" in timeline.empty_label.text()


def test_15_disabled_future_consensus_actions(main_window):
    """Test 15: Disabled future consensus actions."""
    consensus = main_window.workspace_page.consensus
    assert consensus.btn_cast_ballots.isEnabled() is False
    assert consensus.btn_view_report.isEnabled() is False
    assert "Phase 4" in consensus.btn_cast_ballots.text()


def test_16_ui_responsiveness_during_scans(main_window, monkeypatch):
    """Test 16: UI responsiveness during desktop application scans."""
    scan_called = []

    def mock_scan():
        scan_called.append(True)
        return {"chatgpt": [], "claude": [], "gemini": []}

    monkeypatch.setattr(main_window.discovery, "discover_candidates", mock_scan)
    main_window.connections_page.scan_applications()
    assert main_window.connections_page.btn_scan.isEnabled() is False


def test_17_existing_database_migration(temp_db):
    """Test 17: Database schema migration succeeds and creates expected tables."""
    with temp_db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r["name"] for r in cursor.fetchall()]
        assert "reasoning_sessions" in tables
        assert "session_timeline_events" in tables
        assert "schema_migrations" in tables


def test_18_application_restart(temp_db, qapp):
    """Test 18: Application restart retains saved sessions and preferences."""
    # 1. First run: create session
    repo1 = SessionRepository(db=temp_db)
    mgr1 = SessionManager(repository=repo1)
    s = mgr1.create_session("Persisted Across Restart", "Persistent prompt text")
    sess_id = s.session_id

    # 2. Simulate restart: instantiate new repository and manager with same db
    repo2 = SessionRepository(db=temp_db)
    mgr2 = SessionManager(repository=repo2)
    restored = mgr2.load_session(sess_id)

    assert restored is not None
    assert restored.title == "Persisted Across Restart"
    assert restored.initial_question == "Persistent prompt text"


def test_19_invalid_stored_session_handling(main_window):
    """Test 19: Handling non-existent or invalid session ID gracefully."""
    loaded = main_window.session_mgr.load_session("non_existent_session_id")
    assert loaded is None


def test_20_phase_1_regression_coverage(main_window):
    """Test 20: Phase 1 window manager checks, discovery classifications, and registry states remain valid."""
    assert main_window.window_mgr.is_window_valid(0) is False
    assert main_window.window_mgr.is_window_valid(-1) is False
    conn = main_window.registry.get_connection("chatgpt")
    assert conn is not None
    assert conn.status in [
        AgentStatus.MISSING, AgentStatus.DETECTED, AgentStatus.BOUND, AgentStatus.STALE
    ]


def test_21_agent_panel_actions_and_feedback(main_window):
    """Test 21: AgentPanel has Copy & Focus, Import, and Focus buttons with feedback."""
    panel = main_window.workspace_page.agent_panels["chatgpt"]
    assert panel.btn_copy_focus is not None
    assert panel.btn_import is not None
    assert panel.btn_focus is not None

    # Test feedback display (using isHidden() since window is not shown)
    panel.show_feedback("Test error", is_error=True)
    assert not panel.feedback_lbl.isHidden()
    assert panel.feedback_lbl.text() == "Test error"

    panel.show_feedback("Test success", is_error=False)
    assert not panel.feedback_lbl.isHidden()
    assert panel.feedback_lbl.text() == "Test success"

    panel.show_feedback("")
    assert panel.feedback_lbl.isHidden()


def test_22_round_indicator_banner_and_progress(main_window):
    """Test 22: Workspace round indicator banner updates dynamically as responses are accepted."""
    wp = main_window.workspace_page
    assert wp.round_banner is not None
    assert "ROUND 1" in wp.round_title_lbl.text()
    assert "Awaiting Session" in wp.round_counter_pill.text()

    # Create session
    session = main_window.session_mgr.create_session("Round Banner Test", "Test prompt question")
    assert "0/3 Responses Accepted" in wp.round_counter_pill.text()

    # Simulate importing response 1
    main_window.bridge.import_response(session.session_id, 1, "chatgpt", "ChatGPT response text here.")
    session.agent_statuses["chatgpt"] = session.agent_statuses["chatgpt"].RESPONSE_ACCEPTED
    wp._update_round_banner()
    assert "1/3 Responses Accepted" in wp.round_counter_pill.text()

    # Simulate importing response 2
    main_window.bridge.import_response(session.session_id, 1, "claude", "Claude response text here.")
    session.agent_statuses["claude"] = session.agent_statuses["claude"].RESPONSE_ACCEPTED
    wp._update_round_banner()
    assert "2/3 Responses Accepted" in wp.round_counter_pill.text()

    # Simulate importing response 3
    main_window.bridge.import_response(session.session_id, 1, "gemini", "Gemini response text here.")
    session.agent_statuses["gemini"] = session.agent_statuses["gemini"].RESPONSE_ACCEPTED
    wp._update_round_banner()
    assert "3/3 — Round 1 Complete" in wp.round_counter_pill.text()


def test_23_copy_focus_and_response_import_integration(main_window, monkeypatch):
    """Test 23: Copy & Focus and Response Import flows update panel text and timeline events."""
    session = main_window.session_mgr.create_session("Integration Test", "Question on consensus")
    wp = main_window.workspace_page
    panel = wp.agent_panels["claude"]

    # Mock clipboard write
    copied_agents = []

    def mock_copy_and_focus(session_id, round_number, agent_id, **kwargs):
        copied_agents.append(agent_id)
        return True, "Copied!"

    monkeypatch.setattr(main_window.bridge, "copy_and_focus", mock_copy_and_focus)

    # Trigger copy focus
    panel.btn_copy_focus.click()
    assert "claude" in copied_agents
    assert "COPIED" in panel.resp_pill.text()

    # Mock dialog exec to import response directly
    from app.ui.response_import_dialog import ResponseImportDialog

    def mock_exec(dialog_self):
        dialog_self.confirmed_text = "Claude's verified response for architecture."
        dialog_self.confirmed_revision = False
        return 1

    monkeypatch.setattr(ResponseImportDialog, "exec", mock_exec)

    panel.btn_import.click()
    assert "Claude's verified response" in panel.response_text.toPlainText()
    assert "ACCEPTED" in panel.resp_pill.text()
    assert "SHA-256" in panel.telemetry_lbl.text()


def test_24_consensus_panel_three_placeholders(main_window):
    """Test 24: Consensus panel contains three distinct placeholders for Voting, Disagreement, and Minority Report."""
    cp = main_window.workspace_page.consensus
    assert cp.btn_cast_ballots is not None
    assert cp.btn_view_disagreement is not None
    assert cp.btn_view_report is not None

    assert cp.btn_cast_ballots.isEnabled() is False
    assert cp.btn_view_disagreement.isEnabled() is False
    assert cp.btn_view_report.isEnabled() is False


def test_25_sidebar_navigation_labels(main_window):
    """Test 25: Sidebar navigation exposes required buttons."""
    sb = main_window.sidebar
    btn_texts = [b.text() for b in sb.buttons.values()]
    assert "New Discussion" in btn_texts
    assert "Saved Sessions" in btn_texts
    assert "Session Search" in btn_texts
    assert "Agent Connections" in btn_texts
    assert "Settings" in btn_texts

    mode_texts = [m.text() for m in sb.mode_buttons.values()]
    assert "Quick Consensus" in mode_texts
    assert "Deep Debate" in mode_texts
    assert "Research Council" in mode_texts
    assert "Code Review Council" in mode_texts
    assert "Creative Council" in mode_texts

