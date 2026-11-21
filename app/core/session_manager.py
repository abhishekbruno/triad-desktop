import uuid
from datetime import datetime, timezone
from typing import List, Optional
from PySide6.QtCore import QObject, Signal

from app.models.session import ReasoningMode, ReasoningSession, SessionState
from app.models.timeline_event import TimelineEvent, TimelineEventType
from app.storage.database import DatabaseManager
from app.storage.session_repository import SessionRepository
from app.utils.logging import get_logger

logger = get_logger("session_manager")


class SessionManager(QObject):
    """MOD-03: Reasoning Session Manager.

    Coordinates session creation, persistence, state transitions, and timeline logging.
    Emits Qt signals to keep UI components synchronised without coupling.
    """

    session_created = Signal(object)      # (ReasoningSession)
    session_loaded = Signal(object)       # (ReasoningSession)
    session_updated = Signal(object)      # (ReasoningSession)
    session_deleted = Signal(str)         # (session_id)
    timeline_event_added = Signal(object) # (TimelineEvent)
    mode_changed = Signal(str)            # (mode_value)

    def __init__(self, repository: Optional[SessionRepository] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.repo = repository or SessionRepository()
        self._current_session: Optional[ReasoningSession] = None

    @property
    def current_session(self) -> Optional[ReasoningSession]:
        return self._current_session

    def create_session(
        self,
        title: str,
        initial_question: str,
        mode: ReasoningMode = ReasoningMode.QUICK_CONSENSUS,
        max_rounds: int = 3,
    ) -> ReasoningSession:
        """Creates a new session, logs initial lifecycle events, and makes it active."""
        session = self.repo.create_session(
            title=title,
            initial_question=initial_question,
            mode=mode,
            max_rounds=max_rounds,
        )
        self._current_session = session

        # Add initial timeline event: session created
        ev_create = TimelineEvent(
            event_id=f"ev_{uuid.uuid4().hex[:8]}",
            session_id=session.session_id,
            event_type=TimelineEventType.SESSION_CREATED,
            content=f"Reasoning session created: '{session.title}'",
            status="logged",
        )
        self.repo.add_event(ev_create)

        # Add timeline event: mode selected
        ev_mode = TimelineEvent(
            event_id=f"ev_{uuid.uuid4().hex[:8]}",
            session_id=session.session_id,
            event_type=TimelineEventType.MODE_CHANGED,
            content=f"Reasoning mode configured: {mode.value.replace('_', ' ').title()} (Max rounds: {max_rounds})",
            status="logged",
        )
        self.repo.add_event(ev_mode)

        self.session_created.emit(session)
        self.timeline_event_added.emit(ev_create)
        self.timeline_event_added.emit(ev_mode)
        return session

    def load_session(self, session_id: str) -> Optional[ReasoningSession]:
        """Loads an existing session from storage and makes it active."""
        session = self.repo.get_session(session_id)
        if not session:
            logger.warning("Session %s not found", session_id)
            return None

        self._current_session = session

        # Log session reopened event
        ev_reopened = TimelineEvent(
            event_id=f"ev_{uuid.uuid4().hex[:8]}",
            session_id=session.session_id,
            event_type=TimelineEventType.SESSION_REOPENED,
            content=f"Session reopened in workspace: '{session.title}'",
            status="logged",
        )
        self.repo.add_event(ev_reopened)

        self.session_loaded.emit(session)
        self.timeline_event_added.emit(ev_reopened)
        return session

    def rename_session(self, session_id: str, new_title: str) -> bool:
        """Renames a session in storage and logs a timeline event."""
        cleaned = new_title.strip()
        if not cleaned:
            return False

        success = self.repo.rename_session(session_id, cleaned)
        if success:
            if self._current_session and self._current_session.session_id == session_id:
                self._current_session.title = cleaned

            ev_renamed = TimelineEvent(
                event_id=f"ev_{uuid.uuid4().hex[:8]}",
                session_id=session_id,
                event_type=TimelineEventType.SESSION_RENAMED,
                content=f"Session renamed to: '{cleaned}'",
                status="logged",
            )
            self.repo.add_event(ev_renamed)

            if self._current_session and self._current_session.session_id == session_id:
                self.session_updated.emit(self._current_session)
            self.timeline_event_added.emit(ev_renamed)
        return success

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session from storage."""
        success = self.repo.delete_session(session_id)
        if success:
            if self._current_session and self._current_session.session_id == session_id:
                self._current_session = None
            self.session_deleted.emit(session_id)
        return success

    def set_reasoning_mode(self, mode: ReasoningMode) -> bool:
        """Changes reasoning mode for the active session."""
        if not self._current_session:
            return False

        success = self.repo.update_mode(self._current_session.session_id, mode)
        if success:
            self._current_session.mode = mode
            ev_mode = TimelineEvent(
                event_id=f"ev_{uuid.uuid4().hex[:8]}",
                session_id=self._current_session.session_id,
                event_type=TimelineEventType.MODE_CHANGED,
                content=f"Reasoning mode updated to: {mode.value.replace('_', ' ').title()}",
                status="logged",
            )
            self.repo.add_event(ev_mode)
            self.mode_changed.emit(mode.value)
            self.session_updated.emit(self._current_session)
            self.timeline_event_added.emit(ev_mode)
        return success

    def set_max_rounds(self, max_rounds: int) -> bool:
        """Updates maximum rounds for active session."""
        if not self._current_session:
            return False

        success = self.repo.update_rounds(self._current_session.session_id, max_rounds)
        if success:
            self._current_session.max_rounds = max_rounds
            ev_cfg = TimelineEvent(
                event_id=f"ev_{uuid.uuid4().hex[:8]}",
                session_id=self._current_session.session_id,
                event_type=TimelineEventType.CONFIG_UPDATED,
                content=f"Maximum rounds updated to: {max_rounds}",
                status="logged",
            )
            self.repo.add_event(ev_cfg)
            self.session_updated.emit(self._current_session)
            self.timeline_event_added.emit(ev_cfg)
        return success

    def get_timeline_events(self, session_id: Optional[str] = None) -> List[TimelineEvent]:
        """Retrieves timeline events for active or specified session."""
        target_id = session_id or (self._current_session.session_id if self._current_session else None)
        if not target_id:
            return []
        return self.repo.get_events(target_id)

    def list_recent_sessions(self, limit: int = 50) -> List[ReasoningSession]:
        """Lists recent sessions."""
        return self.repo.list_sessions(limit=limit)

    def search_sessions(self, query: str, limit: int = 50) -> List[ReasoningSession]:
        """Searches sessions by title or question content."""
        return self.repo.search_sessions(query=query, limit=limit)
