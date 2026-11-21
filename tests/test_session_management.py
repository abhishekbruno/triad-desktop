import os
import tempfile
import pytest

from app.core.session_manager import SessionManager
from app.models.session import ReasoningMode, SessionState
from app.models.timeline_event import TimelineEvent, TimelineEventType
from app.storage.database import DatabaseManager
from app.storage.session_repository import SessionRepository


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


def test_session_repository_create_and_get(temp_db):
    repo = SessionRepository(db=temp_db)
    session = repo.create_session(
        title="Distributed Consensus Engine",
        initial_question="How should Raft be implemented in Python?",
        mode=ReasoningMode.DEEP_DEBATE,
        max_rounds=4,
    )

    assert session.session_id.startswith("sess_")
    assert session.title == "Distributed Consensus Engine"
    assert session.initial_question == "How should Raft be implemented in Python?"
    assert session.mode == ReasoningMode.DEEP_DEBATE
    assert session.max_rounds == 4
    assert session.state == SessionState.DRAFT

    # Retrieve from DB
    loaded = repo.get_session(session.session_id)
    assert loaded is not None
    assert loaded.session_id == session.session_id
    assert loaded.title == session.title
    assert loaded.mode == ReasoningMode.DEEP_DEBATE
    assert loaded.max_rounds == 4


def test_session_repository_list_and_search(temp_db):
    repo = SessionRepository(db=temp_db)
    s1 = repo.create_session("Microservices Architecture", "Compare gRPC vs REST", ReasoningMode.QUICK_CONSENSUS)
    s2 = repo.create_session("Database Indexing Strategy", "B-Tree vs LSM Trees in high-write workloads", ReasoningMode.RESEARCH_COUNCIL)
    s3 = repo.create_session("Frontend State Management", "Signals vs Redux pattern in React", ReasoningMode.CODE_REVIEW)

    all_sessions = repo.list_sessions()
    assert len(all_sessions) == 3

    # Search by title
    res_title = repo.search_sessions("Indexing")
    assert len(res_title) == 1
    assert res_title[0].session_id == s2.session_id

    # Search by question content
    res_q = repo.search_sessions("gRPC")
    assert len(res_q) == 1
    assert res_q[0].session_id == s1.session_id

    # Search non-existent
    res_none = repo.search_sessions("Quantum Computing")
    assert len(res_none) == 0


def test_session_repository_rename_and_delete(temp_db):
    repo = SessionRepository(db=temp_db)
    session = repo.create_session("Original Title", "Question text", ReasoningMode.QUICK_CONSENSUS)

    # Rename
    ok = repo.rename_session(session.session_id, "Renamed Title")
    assert ok is True
    updated = repo.get_session(session.session_id)
    assert updated.title == "Renamed Title"

    # Delete
    deleted = repo.delete_session(session.session_id)
    assert deleted is True
    assert repo.get_session(session.session_id) is None


def test_session_repository_timeline_events(temp_db):
    repo = SessionRepository(db=temp_db)
    session = repo.create_session("Session with Events", "Testing timeline persistence")

    ev1 = TimelineEvent(
        event_id="ev_1",
        session_id=session.session_id,
        event_type=TimelineEventType.SESSION_CREATED,
        content="Session initiated",
    )
    ev2 = TimelineEvent(
        event_id="ev_2",
        session_id=session.session_id,
        event_type=TimelineEventType.MODE_CHANGED,
        content="Mode switched to Deep Debate",
    )
    repo.add_event(ev1)
    repo.add_event(ev2)

    events = repo.get_events(session.session_id)
    assert len(events) == 2
    assert events[0].event_type == TimelineEventType.SESSION_CREATED
    assert events[1].event_type == TimelineEventType.MODE_CHANGED


def test_session_manager_lifecycle_and_signals(temp_db):
    repo = SessionRepository(db=temp_db)
    mgr = SessionManager(repository=repo)

    created_signal = []
    mgr.session_created.connect(lambda s: created_signal.append(s))

    event_signals = []
    mgr.timeline_event_added.connect(lambda ev: event_signals.append(ev))

    # 1. Create session
    session = mgr.create_session(
        title="Autonomous Agent Consensus",
        initial_question="Design multi-agent consensus protocol",
        mode=ReasoningMode.RESEARCH_COUNCIL,
        max_rounds=5,
    )
    assert len(created_signal) == 1
    assert created_signal[0].session_id == session.session_id
    assert mgr.current_session is not None
    assert mgr.current_session.session_id == session.session_id
    assert len(event_signals) == 2  # SESSION_CREATED and MODE_CHANGED

    # 2. Rename session
    updated_signal = []
    mgr.session_updated.connect(lambda s: updated_signal.append(s))
    ok = mgr.rename_session(session.session_id, "Updated Consensus Architecture")
    assert ok is True
    assert mgr.current_session.title == "Updated Consensus Architecture"
    assert len(updated_signal) == 1

    # 3. Update Mode
    mode_signals = []
    mgr.mode_changed.connect(lambda m: mode_signals.append(m))
    mgr.set_reasoning_mode(ReasoningMode.CODE_REVIEW)
    assert mgr.current_session.mode == ReasoningMode.CODE_REVIEW
    assert len(mode_signals) == 1
    assert mode_signals[0] == "code_review"

    # 4. Update Max Rounds
    mgr.set_max_rounds(7)
    assert mgr.current_session.max_rounds == 7

    # 5. Delete session
    deleted_signals = []
    mgr.session_deleted.connect(lambda s_id: deleted_signals.append(s_id))
    mgr.delete_session(session.session_id)
    assert len(deleted_signals) == 1
    assert deleted_signals[0] == session.session_id
    assert mgr.current_session is None


def test_database_migration_v3(temp_db):
    """Verifies that migration version 3 was applied and session_timeline_events table exists."""
    with temp_db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT version, description FROM schema_migrations WHERE version = 3")
        row = cursor.fetchone()
        assert row is not None
        assert "session_timeline_events" in row["description"]

        # Verify table columns
        cursor.execute("PRAGMA table_info(session_timeline_events)")
        cols = [c["name"] for c in cursor.fetchall()]
        assert "event_id" in cols
        assert "session_id" in cols
        assert "event_type" in cols
        assert "timestamp" in cols
        assert "content" in cols
