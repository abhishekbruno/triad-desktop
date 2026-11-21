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
