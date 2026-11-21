import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.agent import SUPPORTED_AGENTS
from app.models.session import (
    AgentRoundStatus,
    ModelResponse,
    OutboundPrompt,
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

        # Stage independent Round 1 prompts for all three AI participants
        for agent_id, defn in SUPPORTED_AGENTS.items():
            prompt_text = (
                f"<<<TRIAD_REASONING_COUNCIL: ROUND 1 (INDEPENDENT)>>>\n"
                f"Participant: {defn.display_name}\n"
                f"Topic: {cleaned_title}\n\n"
                f"Problem Statement / Question:\n"
                f"{cleaned_question}\n\n"
                f"Instructions:\n"
                f"1. Formulate your independent analysis and detailed recommendation.\n"
                f"2. Explicitly outline any core assumptions, technical tradeoffs, or constraints.\n"
                f"3. Note: This is an isolated round; you have not been provided with peer answers. "
                f"Please focus solely on the provided problem statement.\n"
                f"<<<END_PROMPT>>>"
            )
            prompt_id = f"p_{session_id}_1_{agent_id}"
            outbound = OutboundPrompt(
                prompt_id=prompt_id,
                session_id=session_id,
                round_number=1,
                agent_id=agent_id,
                prompt_text=prompt_text,
                staged_at=now,
            )
            session.prompts[agent_id] = outbound
            session.agent_statuses[agent_id] = AgentRoundStatus.PROMPT_STAGED

            self.db.save_outbound_prompt(
                prompt_id=prompt_id,
                session_id=session_id,
                round_number=1,
                agent_id=agent_id,
                prompt_text=prompt_text,
            )

        logger.info("Created session %s: '%s' with staged prompts", session_id, cleaned_title)
        return session

    def get_session(self, session_id: str) -> Optional[ReasoningSession]:
        """Loads a ReasoningSession from storage by its ID, restoring staged prompts and accepted responses."""
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

        session = ReasoningSession(
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

        # Load staged prompts for current round
        prompts = self.db.get_outbound_prompts(session_id, session.current_round)
        for p in prompts:
            agent_id = p["agent_id"]
            session.prompts[agent_id] = OutboundPrompt(
                prompt_id=p["prompt_id"],
                session_id=session_id,
                round_number=p["round_number"],
                agent_id=agent_id,
                prompt_text=p["prompt_text"],
                staged_at=p["staged_at"],
                copied_at=p.get("copied_at"),
            )
            if p.get("copied_at"):
                session.agent_statuses[agent_id] = AgentRoundStatus.PROMPT_COPIED
            else:
                session.agent_statuses[agent_id] = AgentRoundStatus.PROMPT_STAGED

        # Load accepted responses for current round
        responses = self.db.get_session_responses(session_id, session.current_round)
        for r in responses:
            agent_id = r["agent_id"]
            session.responses[agent_id] = ModelResponse(
                response_id=r["response_id"],
                session_id=session_id,
                round_number=r["round_number"],
                agent_id=agent_id,
                prompt_sent="",
                raw_response=r["response_text"],
                sha256_hash=r["sha256_hash"],
                word_count=r["word_count"],
                char_count=r["char_count"],
                source_type=r.get("source_type", "manual_import"),
                revision_number=r.get("revision_number", 1),
                timestamp=r["imported_at"],
            )
            session.agent_statuses[agent_id] = AgentRoundStatus.RESPONSE_ACCEPTED

        return session

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
