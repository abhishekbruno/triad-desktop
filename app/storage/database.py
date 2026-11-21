import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional
from app.utils.logging import get_logger

logger = get_logger("storage")


class DatabaseManager:
    """Manages persistent local configuration and audit logs in SQLite.

    CRITICAL RULES:
    - Never persists transient runtime IDs (HWND, PID) as permanent identities across reboots.
    - Never stores credentials, tokens, cookies, chat histories, or private payloads.
    - Preserves user identity preferences, discovery timestamps, and UI configuration.
    """

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = Path(os.environ.get("LOCALAPPDATA", ".")) / "TRIAD"
            base_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = str(base_dir / "triad_workspace.db")
        else:
            self.db_path = db_path
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        self._init_db()

    @contextmanager
    def _get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Initializes tables for preferences and discovery audits."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # User preferences for agent discovery and binding
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_preferences (
                    agent_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    preferred_executable TEXT,
                    preferred_title_keyword TEXT,
                    auto_connect INTEGER DEFAULT 1,
                    last_updated TIMESTAMP NOT NULL
                )
                """
            )

            # Application UI and system settings
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ui_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )

            # Discovery event audit log
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS discovery_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    agent_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    executable_name TEXT,
                    details TEXT
                )
                """
            )

            # Schema versioning
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    applied_at TIMESTAMP NOT NULL,
                    description TEXT NOT NULL
                )
                """
            )

            # Phase 2: Reasoning sessions
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS reasoning_sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    initial_question TEXT NOT NULL,
                    state TEXT NOT NULL,
                    current_round INTEGER DEFAULT 1,
                    max_rounds INTEGER DEFAULT 3,
                    mode TEXT DEFAULT 'quick_consensus',
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
                """
            )

            # Phase 2: Staged outbound prompts
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session_prompts (
                    prompt_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES reasoning_sessions(session_id) ON DELETE CASCADE,
                    round_number INTEGER NOT NULL,
                    agent_id TEXT NOT NULL,
                    prompt_text TEXT NOT NULL,
                    staged_at TIMESTAMP NOT NULL,
                    copied_at TIMESTAMP
                )
                """
            )

            # Phase 2: User-imported model responses with SHA-256 integrity hash
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS session_responses (
                    response_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES reasoning_sessions(session_id) ON DELETE CASCADE,
                    round_number INTEGER NOT NULL,
                    agent_id TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    sha256_hash TEXT NOT NULL,
                    word_count INTEGER NOT NULL,
                    char_count INTEGER NOT NULL,
                    source_type TEXT NOT NULL DEFAULT 'manual_import',
                    user_confirmed INTEGER DEFAULT 1,
                    revision_number INTEGER DEFAULT 1,
                    imported_at TIMESTAMP NOT NULL,
                    UNIQUE(session_id, round_number, agent_id, revision_number)
                )
                """
            )

            # Record migration version 2
            cursor.execute(
                """
                INSERT OR IGNORE INTO schema_migrations (version, applied_at, description)
                VALUES (2, ?, 'Phase 2: reasoning_sessions, session_prompts, session_responses')
                """,
                (datetime.now(timezone.utc).isoformat(),),
            )
            conn.commit()
            logger.info("Database initialized at %s", self.db_path)

    def set_agent_preference(
        self,
        agent_id: str,
        display_name: str,
        preferred_executable: Optional[str] = None,
        preferred_title_keyword: Optional[str] = None,
        auto_connect: bool = True,
    ) -> None:
        """Saves user-selected preference for identifying an application."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO agent_preferences (
                    agent_id, display_name, preferred_executable,
                    preferred_title_keyword, auto_connect, last_updated
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    preferred_executable=excluded.preferred_executable,
                    preferred_title_keyword=excluded.preferred_title_keyword,
                    auto_connect=excluded.auto_connect,
                    last_updated=excluded.last_updated
                """,
                (
                    agent_id,
                    display_name,
                    preferred_executable,
                    preferred_title_keyword,
                    1 if auto_connect else 0,
                    now,
                ),
            )
            conn.commit()

    def get_agent_preference(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves user preference for a specific agent."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM agent_preferences WHERE agent_id = ?",
                (agent_id,),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def set_setting(self, key: str, value: str) -> None:
        """Stores a UI configuration string."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO ui_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at
                """,
                (key, value, now),
            )
            conn.commit()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieves a UI configuration string."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM ui_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return row["value"]
            return default

    def log_discovery_event(
        self,
        agent_id: str,
        event_type: str,
        executable_name: Optional[str] = None,
        details: Optional[str] = None,
    ) -> None:
        """Logs a non-sensitive discovery transition."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO discovery_audit_log (timestamp, agent_id, event_type, executable_name, details)
                VALUES (?, ?, ?, ?, ?)
                """,
                (now, agent_id, event_type, executable_name, details),
            )
            conn.commit()

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent discovery audit entries."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM discovery_audit_log ORDER BY id DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    # -------------------------------------------------------------------------
    # Phase 2: Reasoning Sessions, Staged Prompts, and Imported Responses
    # -------------------------------------------------------------------------

    def create_reasoning_session(
        self,
        session_id: str,
        title: str,
        initial_question: str,
        state: str = "round_1_ready",
        current_round: int = 1,
        max_rounds: int = 3,
        mode: str = "quick_consensus",
    ) -> Dict[str, Any]:
        """Creates and stores a new reasoning session."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO reasoning_sessions (
                    session_id, title, initial_question, state, current_round,
                    max_rounds, mode, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    title,
                    initial_question,
                    state,
                    current_round,
                    max_rounds,
                    mode,
                    now,
                    now,
                ),
            )
            conn.commit()
        return {
            "session_id": session_id,
            "title": title,
            "initial_question": initial_question,
            "state": state,
            "current_round": current_round,
            "max_rounds": max_rounds,
            "mode": mode,
            "created_at": now,
            "updated_at": now,
        }

    def get_reasoning_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a reasoning session by its ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reasoning_sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def update_reasoning_session_state(self, session_id: str, state: str) -> None:
        """Updates the status of an existing session."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE reasoning_sessions
                SET state = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (state, now, session_id),
            )
            conn.commit()

    def list_reasoning_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Lists recent reasoning sessions ordered by last update."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM reasoning_sessions ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
            return [dict(row) for row in cursor.fetchall()]

    def save_outbound_prompt(
        self,
        prompt_id: str,
        session_id: str,
        round_number: int,
        agent_id: str,
        prompt_text: str,
    ) -> None:
        """Stores a staged prompt for clipboard transfer."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO session_prompts (
                    prompt_id, session_id, round_number, agent_id, prompt_text, staged_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(prompt_id) DO UPDATE SET
                    prompt_text = excluded.prompt_text,
                    staged_at = excluded.staged_at
                """,
                (prompt_id, session_id, round_number, agent_id, prompt_text, now),
            )
            conn.commit()

    def mark_prompt_copied(self, session_id: str, round_number: int, agent_id: str) -> None:
        """Records timestamp when prompt was copied to clipboard."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE session_prompts
                SET copied_at = ?
                WHERE session_id = ? AND round_number = ? AND agent_id = ?
                """,
                (now, session_id, round_number, agent_id),
            )
            conn.commit()

    def get_outbound_prompts(self, session_id: str, round_number: int) -> List[Dict[str, Any]]:
        """Retrieves all staged prompts for a specific round."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM session_prompts
                WHERE session_id = ? AND round_number = ?
                ORDER BY agent_id ASC
                """,
                (session_id, round_number),
            )
            return [dict(row) for row in cursor.fetchall()]

    def save_session_response(
        self,
        response_id: str,
        session_id: str,
        round_number: int,
        agent_id: str,
        response_text: str,
        sha256_hash: str,
        word_count: int,
        char_count: int,
        source_type: str = "manual_import",
        user_confirmed: bool = True,
        revision_number: int = 1,
    ) -> None:
        """Persists a verified and accepted model response with integrity hash."""
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO session_responses (
                    response_id, session_id, round_number, agent_id, response_text,
                    sha256_hash, word_count, char_count, source_type, user_confirmed,
                    revision_number, imported_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    response_id,
                    session_id,
                    round_number,
                    agent_id,
                    response_text,
                    sha256_hash,
                    word_count,
                    char_count,
                    source_type,
                    1 if user_confirmed else 0,
                    revision_number,
                    now,
                ),
            )
            conn.commit()

    def get_session_responses(self, session_id: str, round_number: int) -> List[Dict[str, Any]]:
        """Retrieves accepted responses for a round, taking latest revision per agent."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM session_responses
                WHERE session_id = ? AND round_number = ?
                ORDER BY imported_at ASC
                """,
                (session_id, round_number),
            )
            rows = [dict(r) for r in cursor.fetchall()]

        # Filter to highest revision per agent
        latest_by_agent: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            agent = r["agent_id"]
            if agent not in latest_by_agent or r["revision_number"] > latest_by_agent[agent]["revision_number"]:
                latest_by_agent[agent] = r
        return list(latest_by_agent.values())

    def get_latest_response_for_agent(
        self, session_id: str, round_number: int, agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieves the latest accepted response for a specific agent in a round."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM session_responses
                WHERE session_id = ? AND round_number = ? AND agent_id = ?
                ORDER BY revision_number DESC LIMIT 1
                """,
                (session_id, round_number, agent_id),
            )
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
