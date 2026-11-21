import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.agent import SUPPORTED_AGENTS
from app.models.session import (
    AgentRoundStatus,
    ReasoningMode,
    ReasoningSession,
    SessionState,
)
from app.models.timeline_event import TimelineEvent, TimelineEventType
from app.storage.database import DatabaseManager
from app.utils.logging import get_logger

logger = get_logger("session_repository")


class SessionRepository:
    """Repository abstraction over SQLite database for session lifecycle and timeline persistence."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or DatabaseManager()

    def create_session(
        self,
        title: str,
        initial_question: str,
        mode: ReasoningMode = ReasoningMode.QUICK_CONSENSUS,
        max_rounds: int = 3,
    ) -> ReasoningSession:
        """Creates and stores a new ReasoningSession entity."""
        cleaned_title = title.strip()
        cleaned_question = initial_question.strip()
        if not cleaned_question:
            raise ValueError("Initial question cannot be empty.")
        if not cleaned_title:
            cleaned_title = cleaned_question[:45] + ("..." if len(cleaned_question) > 45 else "")

        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        session = ReasoningSession(
            session_id=session_id,
            title=cleaned_title,
            initial_question=cleaned_question,
            mode=mode,
            max_rounds=max_rounds,
            state=SessionState.DRAFT,
            current_round=1,
            participants=list(SUPPORTED_AGENTS.keys()),
            created_at=now,
            updated_at=now,
        )

        self.db.create_reasoning_session(
            session_id=session_id,
            title=cleaned_title,
            initial_question=cleaned_question,
            state=session.state.value,
            current_round=session.current_round,
            max_rounds=session.max_rounds,
            mode=session.mode.value,
        )
        logger.info("Created session %s: '%s'", session_id, cleaned_title)
        return session

    def get_session(self, session_id: str) -> Optional[ReasoningSession]:
        """Loads a ReasoningSession from storage by its ID."""
        row = self.db.get_reasoning_session(session_id)
        if not row:
            return None

        mode = ReasoningMode.QUICK_CONSENSUS
        try:
            mode = ReasoningMode(row["mode"])
        except (ValueError, KeyError):
            pass

        state = SessionState.DRAFT
        try:
            state = SessionState(row["state"])
        except (ValueError, KeyError):
            pass

        return ReasoningSession(
            session_id=row["session_id"],
            title=row["title"],
            initial_question=row["initial_question"],
            mode=mode,
            max_rounds=row["max_rounds"],
            state=state,
            current_round=row["current_round"],
            participants=list(SUPPORTED_AGENTS.keys()),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_sessions(self, limit: int = 50) -> List[ReasoningSession]:
        """Lists recent reasoning sessions ordered by last modification."""
        rows = self.db.list_reasoning_sessions(limit=limit)
        sessions: List[ReasoningSession] = []
        for r in rows:
            try:
                mode = ReasoningMode(r["mode"])
            except (ValueError, KeyError):
                mode = ReasoningMode.QUICK_CONSENSUS
            try:
                state = SessionState(r["state"])
            except (ValueError, KeyError):
                state = SessionState.DRAFT

            sessions.append(
                ReasoningSession(
                    session_id=r["session_id"],
                    title=r["title"],
                    initial_question=r["initial_question"],
                    mode=mode,
                    max_rounds=r["max_rounds"],
                    state=state,
                    current_round=r["current_round"],
                    participants=list(SUPPORTED_AGENTS.keys()),
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
            )
        return sessions

    def search_sessions(self, query: str, limit: int = 50) -> List[ReasoningSession]:
        """Searches sessions by title or question content."""
        rows = self.db.search_reasoning_sessions(query=query, limit=limit)
        sessions: List[ReasoningSession] = []
        for r in rows:
            try:
                mode = ReasoningMode(r["mode"])
            except (ValueError, KeyError):
                mode = ReasoningMode.QUICK_CONSENSUS
            try:
                state = SessionState(r["state"])
            except (ValueError, KeyError):
                state = SessionState.DRAFT

            sessions.append(
                ReasoningSession(
                    session_id=r["session_id"],
                    title=r["title"],
                    initial_question=r["initial_question"],
                    mode=mode,
                    max_rounds=r["max_rounds"],
                    state=state,
                    current_round=r["current_round"],
                    participants=list(SUPPORTED_AGENTS.keys()),
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                )
            )
        return sessions

    def rename_session(self, session_id: str, new_title: str) -> bool:
        """Renames a session."""
        return self.db.rename_reasoning_session(session_id, new_title)

    def delete_session(self, session_id: str) -> bool:
        """Deletes a session and associated records."""
        return self.db.delete_reasoning_session(session_id)

    def update_mode(self, session_id: str, mode: ReasoningMode) -> bool:
        """Updates reasoning mode for a session."""
        return self.db.update_reasoning_session_mode(session_id, mode.value)

    def update_rounds(self, session_id: str, max_rounds: int) -> bool:
        """Updates max rounds for a session."""
        return self.db.update_reasoning_session_rounds(session_id, max_rounds)

    def add_event(self, event: TimelineEvent) -> None:
        """Appends a timeline event to persistent history."""
        self.db.add_timeline_event(
            event_id=event.event_id,
            session_id=event.session_id,
            event_type=event.event_type.value if isinstance(event.event_type, TimelineEventType) else str(event.event_type),
            timestamp=event.timestamp,
            participant=event.participant,
            content=event.content,
            status=event.status,
        )

    def get_events(self, session_id: str) -> List[TimelineEvent]:
        """Loads all timeline events for a session sorted chronologically."""
        rows = self.db.get_timeline_events(session_id)
        events: List[TimelineEvent] = []
        for r in rows:
            try:
                ev_type = TimelineEventType(r["event_type"])
            except ValueError:
                ev_type = TimelineEventType.DISCUSSION_NOTE

            events.append(
                TimelineEvent(
                    event_id=r["event_id"],
                    session_id=r["session_id"],
                    event_type=ev_type,
                    timestamp=r["timestamp"],
                    participant=r["participant"],
                    content=r["content"],
                    status=r.get("status", "logged"),
                )
            )
        return events
