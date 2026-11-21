import os
import tempfile
import pytest
from app.storage.database import DatabaseManager


def test_database_initialization_and_schema():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
        tf.close()

    try:
        db = DatabaseManager(db_path=db_path)
        events = db.get_recent_events()
        assert isinstance(events, list)
        assert len(events) == 0
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_agent_preferences_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
        tf.close()

    try:
        db = DatabaseManager(db_path=db_path)
        db.set_agent_preference(
            agent_id="chatgpt",
            display_name="ChatGPT Desktop",
            preferred_executable="ChatGPT.exe",
            preferred_title_keyword="ChatGPT",
        )

        pref = db.get_agent_preference("chatgpt")
        assert pref is not None
        assert pref["agent_id"] == "chatgpt"
        assert pref["preferred_executable"] == "ChatGPT.exe"

        # Update preference
        db.set_agent_preference(
            agent_id="chatgpt",
            display_name="ChatGPT Desktop",
            preferred_executable="ChatGPT_v2.exe",
            preferred_title_keyword="ChatGPT",
        )
        pref_updated = db.get_agent_preference("chatgpt")
        assert pref_updated["preferred_executable"] == "ChatGPT_v2.exe"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_ui_settings_storage():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
        tf.close()

    try:
        db = DatabaseManager(db_path=db_path)
        db.set_setting("theme", "dark")
        db.set_setting("poll_interval", "1.5")

        assert db.get_setting("theme") == "dark"
        assert db.get_setting("poll_interval") == "1.5"
        assert db.get_setting("non_existent", default="def") == "def"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_discovery_audit_logging():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        db_path = tf.name
        tf.close()

    try:
        db = DatabaseManager(db_path=db_path)
        db.log_discovery_event("claude", "BOUND", "claude.exe", "HWND: 0x1234")
        db.log_discovery_event("gemini", "DETECTED", "chrome.exe", "PWA Mode")

        events = db.get_recent_events(limit=10)
        assert len(events) == 2
        assert events[0]["agent_id"] == "gemini"
        assert events[1]["agent_id"] == "claude"
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
