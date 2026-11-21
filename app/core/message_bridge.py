import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple

from app.core.agent_registry import AgentRegistry
from app.core.window_manager import WindowManager
from app.models.agent import AgentStatus, SUPPORTED_AGENTS
from app.models.session import (
    AgentRoundStatus,
    ModelResponse,
    OutboundPrompt,
    ReasoningMode,
    ReasoningSession,
    SessionState,
)
from app.storage.database import DatabaseManager
from app.utils.logging import get_logger

logger = get_logger("message_bridge")


class MessageExchangeBridge:
    """MOD-02: User-Controlled Message Exchange Bridge.

    Responsibilities:
    - Formulates isolated, independent first-round prompts for each target AI participant.
    - Manages explicit, user-authorized clipboard staging.
    - Activates target application window via WindowManager.
    - Ingests user-imported model responses with SHA-256 integrity verification.
    - Enforces epistemic isolation during Round 1 (never exposing peer outputs in prompts).
    - Preserves local responses and updates session state machine.
    """

    def __init__(
        self,
        registry: AgentRegistry,
        window_manager: WindowManager,
        database: DatabaseManager,
    ):
        self.registry = registry
        self.window_mgr = window_manager
        self.db = database
        self.active_session: Optional[ReasoningSession] = None

    def create_session(
        self,
        title: str,
        initial_question: str,
        mode: ReasoningMode = ReasoningMode.QUICK_CONSENSUS,
        max_rounds: int = 3,
    ) -> ReasoningSession:
        """Initializes a new reasoning session with staged independent prompts."""
        cleaned_title = title.strip()
        cleaned_question = initial_question.strip()
        if not cleaned_question:
            raise ValueError("Initial question cannot be empty.")
        if not cleaned_title:
            cleaned_title = cleaned_question[:40] + ("..." if len(cleaned_question) > 40 else "")

        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()

        # Initialize session entity
        session = ReasoningSession(
            session_id=session_id,
            title=cleaned_title,
            initial_question=cleaned_question,
            mode=mode,
            max_rounds=max_rounds,
            state=SessionState.ROUND_1_READY,
            current_round=1,
            participants=list(SUPPORTED_AGENTS.keys()),
            created_at=now,
            updated_at=now,
        )

        # Persist session
        self.db.create_reasoning_session(
            session_id=session_id,
            title=cleaned_title,
            initial_question=cleaned_question,
            state=SessionState.ROUND_1_READY.value,
            current_round=1,
            max_rounds=max_rounds,
            mode=mode.value,
        )

        # Stage independent Round 1 prompts for each participant
        for agent_id in session.participants:
            defn = SUPPORTED_AGENTS[agent_id]
            prompt_text = self._format_round1_prompt(
                agent_display_name=defn.display_name,
                title=cleaned_title,
                question=cleaned_question,
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

        self.active_session = session
        logger.info("Session %s created with 3 staged Round 1 prompts", session_id)
        return session

    def _format_round1_prompt(
        self, agent_display_name: str, title: str, question: str
    ) -> str:
        """Constructs an isolated, independent Round 1 prompt.

        CRITICAL RULE:
        Never include any other model's response or ideas in Round 1 prompts.
        """
        return (
            f"<<<TRIAD_REASONING_COUNCIL: ROUND 1 (INDEPENDENT)>>>\n"
            f"Participant: {agent_display_name}\n"
            f"Topic: {title}\n\n"
            f"Problem Statement / Question:\n"
            f"{question}\n\n"
            f"Instructions:\n"
            f"1. Formulate your independent analysis and detailed recommendation.\n"
            f"2. Explicitly outline any core assumptions, technical tradeoffs, or constraints.\n"
            f"3. Note: This is an isolated round; you have not been provided with peer answers. "
            f"Please focus solely on the provided problem statement.\n"
            f"<<<END_PROMPT>>>"
        )

    def get_staged_prompt(
        self, session_id: str, round_number: int, agent_id: str
    ) -> Optional[str]:
        """Retrieves staged prompt text for a specific agent in a round."""
        prompts = self.db.get_outbound_prompts(session_id, round_number)
        for p in prompts:
            if p["agent_id"] == agent_id:
                return p["prompt_text"]
        return None

    def copy_and_focus(
        self,
        session_id: str,
        round_number: int,
        agent_id: str,
        clipboard_fn: Optional[Callable[[str], bool]] = None,
    ) -> Tuple[bool, str]:
        """Copies staged prompt to system clipboard and focuses the registered window.

        Guarantees:
        - Never overwrites clipboard without an explicit user invocation.
        - Does not switch to another application if target window is stale or missing.
        """
        prompt_text = self.get_staged_prompt(session_id, round_number, agent_id)
        if not prompt_text:
            return False, f"No staged prompt found for agent '{agent_id}' in round {round_number}."

        display_name = SUPPORTED_AGENTS.get(agent_id, None)
        agent_name = display_name.display_name if display_name else agent_id

        # 1. Copy to Clipboard
        copied = False
        if clipboard_fn:
            try:
                copied = clipboard_fn(prompt_text)
            except Exception as e:
                logger.error("Custom clipboard function failed: %s", e)
                copied = False

        if not copied:
            # Fallback using PySide6 clipboard if available
            try:
                from PySide6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    app.clipboard().setText(prompt_text)
                    copied = True
            except Exception as clip_err:
                logger.debug("PySide6 clipboard fallback notice: %s", clip_err)

        if not copied:
            return False, "Failed to write prompt to system clipboard. Please check clipboard access."

        # Mark prompt as copied in database
        self.db.mark_prompt_copied(session_id, round_number, agent_id)
        if self.active_session and self.active_session.session_id == session_id:
            self.active_session.agent_statuses[agent_id] = AgentRoundStatus.PROMPT_COPIED
            if self.active_session.state == SessionState.ROUND_1_READY:
                self.active_session.state = SessionState.AWAITING_RESPONSES
                self.db.update_reasoning_session_state(session_id, SessionState.AWAITING_RESPONSES.value)

        # 2. Focus Registered Window
        conn = self.registry.get_connection(agent_id)
        if not conn or conn.status != AgentStatus.BOUND or not conn.window_handle:
            return (
                True,
                f"Prompt for {agent_name} copied to clipboard, but window is not currently bound.",
            )

        focused, focus_msg = self.window_mgr.focus_window(conn.window_handle)
        if focused:
            return True, f"Prompt copied to clipboard. Focused {agent_name} window."
        return True, f"Prompt copied to clipboard. (Notice focusing {agent_name}: {focus_msg})"

    @staticmethod
    def validate_inbound_response(raw_text: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Validates incoming text payload, calculating word count and SHA-256 hash.

        Enforces security limits:
        - Rejects empty or whitespace-only inputs.
        - Flags oversized inputs (> 1,000,000 characters).
        """
        if raw_text is None:
            return False, "Response payload is null.", {}

        cleaned = raw_text.strip()
        if not cleaned:
            return False, "Response is empty or contains only whitespace.", {}

        if len(cleaned) > 1_000_000:
            return (
                False,
                f"Response exceeds maximum allowed size (size: {len(cleaned):,} characters).",
                {},
            )

        sha256_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
        word_count = len(cleaned.split())
        char_count = len(cleaned)

        return True, "Valid response payload.", {
            "sha256_hash": sha256_hash,
            "word_count": word_count,
            "char_count": char_count,
        }

    def import_response(
        self,
        session_id: str,
        round_number: int,
        agent_id: str,
        response_text: str,
        confirm_revision: bool = False,
    ) -> Tuple[bool, str, Optional[ModelResponse]]:
        """Imports, attributes, verifies, and persists an accepted model response."""
        is_valid, err_msg, meta = self.validate_inbound_response(response_text)
        if not is_valid:
            return False, err_msg, None

        cleaned = response_text.strip()

        # Check existing responses for duplicate rejection
        existing = self.db.get_latest_response_for_agent(session_id, round_number, agent_id)
        revision_num = 1
        if existing:
            if not confirm_revision:
                return (
                    False,
                    f"A response from {agent_id} has already been accepted for Round {round_number}. "
                    "Confirm revision to submit an updated response.",
                    None,
                )
            revision_num = existing["revision_number"] + 1

        response_id = f"resp_{session_id}_{round_number}_{agent_id}_r{revision_num}"
        now = datetime.now(timezone.utc).isoformat()

        # Save to database
        self.db.save_session_response(
            response_id=response_id,
            session_id=session_id,
            round_number=round_number,
            agent_id=agent_id,
            response_text=cleaned,
            sha256_hash=meta["sha256_hash"],
            word_count=meta["word_count"],
            char_count=meta["char_count"],
            source_type="manual_import",
            user_confirmed=True,
            revision_number=revision_num,
        )

        response_obj = ModelResponse(
            response_id=response_id,
            session_id=session_id,
            round_number=round_number,
            agent_id=agent_id,
            prompt_sent=self.get_staged_prompt(session_id, round_number, agent_id) or "",
            raw_response=cleaned,
            sha256_hash=meta["sha256_hash"],
            word_count=meta["word_count"],
            char_count=meta["char_count"],
            source_type="manual_import",
            user_confirmed=True,
            revision_number=revision_num,
            timestamp=now,
        )

        # Update session memory
        if self.active_session and self.active_session.session_id == session_id:
            self.active_session.responses[agent_id] = response_obj
            self.active_session.agent_statuses[agent_id] = AgentRoundStatus.RESPONSE_ACCEPTED
            self._update_session_progress(session_id, round_number)

        logger.info(
            "Response accepted for %s in session %s (Rev %d, words: %d, sha: %s...)",
            agent_id,
            session_id,
            revision_num,
            meta["word_count"],
            meta["sha256_hash"][:10],
        )

        return True, f"Response accepted for {agent_id} (Revision {revision_num}).", response_obj

    def _update_session_progress(self, session_id: str, round_number: int) -> None:
        """Evaluates whether all required participants have completed Round 1."""
        progress = self.get_round_progress(session_id, round_number)
        if progress["is_complete"]:
            if self.active_session and self.active_session.session_id == session_id:
                self.active_session.state = SessionState.ROUND_1_COMPLETE
            self.db.update_reasoning_session_state(session_id, SessionState.ROUND_1_COMPLETE.value)
            logger.info("Session %s: Round %d completed with 3/3 responses", session_id, round_number)

    def get_round_progress(
        self, session_id: str, round_number: int = 1
    ) -> Dict[str, Any]:
        """Calculates accepted responses count and round completion status."""
        responses = self.db.get_session_responses(session_id, round_number)
        accepted_agents = {r["agent_id"] for r in responses}
        required_agents = set(SUPPORTED_AGENTS.keys())

        count = len(accepted_agents)
        total = len(required_agents)
        is_complete = accepted_agents == required_agents

        if is_complete:
            summary = (
                f"{count}/{total} Responses Collected — "
                "Independent Round Complete — Ready for Cross-Model Discussion"
            )
        else:
            summary = f"{count}/{total} Responses Collected"

        return {
            "accepted_count": count,
            "total_required": total,
            "completed_agents": list(accepted_agents),
            "pending_agents": list(required_agents - accepted_agents),
            "is_complete": is_complete,
            "summary_text": summary,
        }

    def restore_session(self, session_id: str) -> Optional[ReasoningSession]:
        """Loads an existing session and all associated prompts and responses from SQLite."""
        session_row = self.db.get_reasoning_session(session_id)
        if not session_row:
            return None

        session = ReasoningSession(
            session_id=session_row["session_id"],
            title=session_row["title"],
            initial_question=session_row["initial_question"],
            mode=ReasoningMode(session_row.get("mode", "quick_consensus")),
            max_rounds=session_row.get("max_rounds", 3),
            state=SessionState(session_row["state"]),
            current_round=session_row.get("current_round", 1),
            participants=list(SUPPORTED_AGENTS.keys()),
            created_at=session_row["created_at"],
            updated_at=session_row["updated_at"],
        )

        # Restore prompts
        prompts = self.db.get_outbound_prompts(session_id, session.current_round)
        for p in prompts:
            session.prompts[p["agent_id"]] = OutboundPrompt(
                prompt_id=p["prompt_id"],
                session_id=session_id,
                round_number=p["round_number"],
                agent_id=p["agent_id"],
                prompt_text=p["prompt_text"],
                staged_at=p["staged_at"],
                copied_at=p.get("copied_at"),
            )
            session.agent_statuses[p["agent_id"]] = (
                AgentRoundStatus.PROMPT_COPIED if p.get("copied_at") else AgentRoundStatus.PROMPT_STAGED
            )

        # Restore responses
        responses = self.db.get_session_responses(session_id, session.current_round)
        for r in responses:
            agent = r["agent_id"]
            session.responses[agent] = ModelResponse(
                response_id=r["response_id"],
                session_id=session_id,
                round_number=r["round_number"],
                agent_id=agent,
                prompt_sent=self.get_staged_prompt(session_id, r["round_number"], agent) or "",
                raw_response=r["response_text"],
                sha256_hash=r["sha256_hash"],
                word_count=r["word_count"],
                char_count=r["char_count"],
                source_type=r["source_type"],
                user_confirmed=bool(r["user_confirmed"]),
                revision_number=r["revision_number"],
                timestamp=r["imported_at"],
            )
            session.agent_statuses[agent] = AgentRoundStatus.RESPONSE_ACCEPTED

        self.active_session = session
        return session

