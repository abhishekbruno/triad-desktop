import hashlib
import os
import tempfile
import pytest

from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.message_bridge import MessageExchangeBridge
from app.core.window_manager import WindowManager
from app.models.agent import AgentStatus, WindowCandidate
from app.models.session import AgentRoundStatus, ReasoningMode, SessionState
from app.storage.database import DatabaseManager


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
        except Exception:
            pass


@pytest.fixture
def bridge_setup(temp_db):
    registry = AgentRegistry()
    win_mgr = WindowManager()
    bridge = MessageExchangeBridge(
        registry=registry,
        window_manager=win_mgr,
        database=temp_db,
    )
    return bridge, registry, win_mgr, temp_db


# 1. Create new session
def test_1_create_new_session(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(
        title="Microservice Consensus",
        initial_question="Should we adopt gRPC or REST for internal APIs?",
        mode=ReasoningMode.DEEP_DEBATE,
    )
    assert session is not None
    assert session.session_id.startswith("sess_")
    assert session.title == "Microservice Consensus"
    assert session.state == SessionState.ROUND_1_READY
    assert len(session.prompts) == 3


# 2. Generate independent prompts
def test_2_generate_independent_prompts(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(
        title="Database Migration",
        initial_question="How to migrate PostgreSQL to AlloyDB with zero downtime?",
    )
    for agent_id in ["chatgpt", "claude", "gemini"]:
        prompt = bridge.get_staged_prompt(session.session_id, 1, agent_id)
        assert prompt is not None
        assert "ROUND 1 (INDEPENDENT)" in prompt
        assert "How to migrate PostgreSQL to AlloyDB" in prompt
        assert agent_id not in prompt.lower() or SUPPORTED_AGENTS[agent_id].display_name in prompt


# 3. Copy prompt to clipboard
def test_3_copy_prompt_to_clipboard(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T3", initial_question="Question 3")
    clipboard_box = []

    def fake_clipboard(text: str) -> bool:
        clipboard_box.append(text)
        return True

    success, msg = bridge.copy_and_focus(
        session.session_id, 1, "chatgpt", clipboard_fn=fake_clipboard
    )
    assert success
    assert len(clipboard_box) == 1
    assert "Question 3" in clipboard_box[0]


# 4. Focus existing application
def test_4_focus_existing_application(bridge_setup, mocker):
    bridge, registry, win_mgr, _ = bridge_setup
    session = bridge.create_session(title="T4", initial_question="Question 4")

    # Bind Claude to HWND 5555
    registry.bind_manual("claude", pid=4000, hwnd=5555)
    mocker.patch.object(win_mgr, "focus_window", return_value=(True, "Focused successfully."))

    success, msg = bridge.copy_and_focus(
        session.session_id, 1, "claude", clipboard_fn=lambda t: True
    )
    assert success
    assert "Focused Claude Desktop window" in msg


# 5. Invalid application handle
def test_5_invalid_application_handle(bridge_setup, mocker):
    bridge, registry, win_mgr, _ = bridge_setup
    session = bridge.create_session(title="T5", initial_question="Question 5")

    # Bind Gemini to an invalid HWND 9999
    registry.bind_manual("gemini", pid=4001, hwnd=9999)
    mocker.patch.object(win_mgr, "focus_window", return_value=(False, "Window handle is invalid."))

    success, msg = bridge.copy_and_focus(
        session.session_id, 1, "gemini", clipboard_fn=lambda t: True
    )
    # Clipboard copy succeeds, but notice describes focus failure
    assert success
    assert "Window handle is invalid" in msg


# 6. Clipboard unavailable
def test_6_clipboard_unavailable(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T6", initial_question="Question 6")

    # Force clipboard failure
    def failing_clipboard(text: str) -> bool:
        return False

    success, msg = bridge.copy_and_focus(
        session.session_id, 1, "chatgpt", clipboard_fn=failing_clipboard
    )
    assert not success
    assert "Failed to write prompt to system clipboard" in msg


# 7. Import ChatGPT response
def test_7_import_chatgpt_response(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T7", initial_question="Question 7")
    resp_text = "ChatGPT recommends using an asynchronous queue with idempotent consumers."

    success, msg, resp_obj = bridge.import_response(
        session.session_id, 1, "chatgpt", resp_text
    )
    assert success
    assert resp_obj is not None
    assert resp_obj.agent_id == "chatgpt"
    assert resp_obj.word_count == 9
    assert resp_obj.sha256_hash == hashlib.sha256(resp_text.encode("utf-8")).hexdigest()


# 8. Import Claude response
def test_8_import_claude_response(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T8", initial_question="Question 8")
    resp_text = "Claude suggests transactional outbox pattern to guarantee consistency."

    success, msg, resp_obj = bridge.import_response(
        session.session_id, 1, "claude", resp_text
    )
    assert success
    assert resp_obj.agent_id == "claude"
    assert resp_obj.word_count == 8


# 9. Import Gemini response
def test_9_import_gemini_response(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T9", initial_question="Question 9")
    resp_text = "Gemini advises circuit breakers with graceful fallback states."

    success, msg, resp_obj = bridge.import_response(
        session.session_id, 1, "gemini", resp_text
    )
    assert success
    assert resp_obj.agent_id == "gemini"


# 10. Reject empty response
def test_10_reject_empty_response(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T10", initial_question="Question 10")

    success, msg, resp_obj = bridge.import_response(
        session.session_id, 1, "chatgpt", "   \n   \t  "
    )
    assert not success
    assert "empty" in msg.lower()
    assert resp_obj is None


# 11. Reject duplicate submission unless explicitly revised
def test_11_reject_duplicate_submission_unless_revised(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T11", initial_question="Question 11")

    # Initial submission
    success1, _, _ = bridge.import_response(
        session.session_id, 1, "claude", "Initial Claude answer."
    )
    assert success1

    # Unconfirmed duplicate rejection
    success2, msg2, _ = bridge.import_response(
        session.session_id, 1, "claude", "Second attempt without revision flag.", confirm_revision=False
    )
    assert not success2
    assert "Confirm revision" in msg2

    # Confirmed revision acceptance
    success3, msg3, resp3 = bridge.import_response(
        session.session_id, 1, "claude", "Updated Claude answer with corrections.", confirm_revision=True
    )
    assert success3
    assert resp3.revision_number == 2
    assert "Revision 2" in msg3


# 12. Verify stored SHA-256 hash
def test_12_verify_stored_sha256_hash(bridge_setup, temp_db):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T12", initial_question="Question 12")
    payload = "Deterministic payload for cryptographic integrity check."
    expected_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    bridge.import_response(session.session_id, 1, "gemini", payload)

    stored = temp_db.get_latest_response_for_agent(session.session_id, 1, "gemini")
    assert stored is not None
    assert stored["sha256_hash"] == expected_hash


# 13. Restore an existing session
def test_13_restore_existing_session(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T13 Session", initial_question="Persisted question")
    bridge.import_response(session.session_id, 1, "chatgpt", "Persisted ChatGPT response.")

    # Restore from new bridge instance
    new_bridge = MessageExchangeBridge(bridge.registry, bridge.window_mgr, bridge.db)
    restored = new_bridge.restore_session(session.session_id)

    assert restored is not None
    assert restored.session_id == session.session_id
    assert restored.title == "T13 Session"
    assert restored.initial_question == "Persisted question"
    assert "chatgpt" in restored.responses
    assert restored.responses["chatgpt"].raw_response == "Persisted ChatGPT response."


# 14. Handle missing participant
def test_14_handle_missing_participant(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T14", initial_question="Question 14")

    # Only ChatGPT and Claude submit; Gemini is missing
    bridge.import_response(session.session_id, 1, "chatgpt", "ChatGPT response.")
    bridge.import_response(session.session_id, 1, "claude", "Claude response.")

    progress = bridge.get_round_progress(session.session_id, 1)
    assert progress["accepted_count"] == 2
    assert not progress["is_complete"]
    assert progress["pending_agents"] == ["gemini"]
    assert "2/3 Responses Collected" in progress["summary_text"]


# 15. Enforce Round 1 isolation
def test_15_enforce_round_1_isolation(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T15", initial_question="Original question")

    # ChatGPT submits response containing controversial thesis
    bridge.import_response(session.session_id, 1, "chatgpt", "SECRET_THESIS_ALPHA: Use Paxos!")

    # Verify that Claude's staged prompt does NOT contain ChatGPT's secret thesis
    claude_prompt = bridge.get_staged_prompt(session.session_id, 1, "claude")
    assert "SECRET_THESIS_ALPHA" not in claude_prompt
    assert "Use Paxos" not in claude_prompt


# 16. Mark round complete only after required responses are accepted
def test_16_mark_round_complete_only_after_all_accepted(bridge_setup):
    bridge, _, _, _ = bridge_setup
    session = bridge.create_session(title="T16", initial_question="Question 16")

    assert session.state == SessionState.ROUND_1_READY

    bridge.import_response(session.session_id, 1, "chatgpt", "Answer 1")
    assert bridge.active_session.state == SessionState.ROUND_1_READY or bridge.active_session.state == SessionState.AWAITING_RESPONSES

    bridge.import_response(session.session_id, 1, "claude", "Answer 2")
    assert not bridge.get_round_progress(session.session_id, 1)["is_complete"]

    # 3rd participant submits
    bridge.import_response(session.session_id, 1, "gemini", "Answer 3")
    progress = bridge.get_round_progress(session.session_id, 1)

    assert progress["is_complete"]
    assert progress["accepted_count"] == 3
    assert bridge.active_session.state == SessionState.ROUND_1_COMPLETE
    assert "Independent Round Complete — Ready for Cross-Model Discussion" in progress["summary_text"]


# 17. Preserve Phase 1 functionality
def test_17_preserve_phase_1_functionality(bridge_setup):
    bridge, registry, win_mgr, db = bridge_setup
    # Verify Phase 1 registry methods still function identically
    conns = registry.get_all_connections()
    assert len(conns) == 3
    assert registry.bound_count == 0

    cand = WindowCandidate(101, 1001, "ChatGPT", "chatgpt.exe")
    registry.bind_candidate("chatgpt", cand)
    assert registry.bound_count == 1
    assert registry.get_summary_text() == "1/3 applications bound"

    registry.disconnect_all()
    assert registry.bound_count == 0


from app.models.agent import SUPPORTED_AGENTS

