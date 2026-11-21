from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class TimelineEventType(str, Enum):
    """Categorization of discussion timeline events."""
    SESSION_CREATED = "session_created"
    MODE_CHANGED = "mode_changed"
    CONFIG_UPDATED = "config_updated"
    PARTICIPANT_CONFIGURED = "participant_configured"
    SESSION_REOPENED = "session_reopened"
    SESSION_RENAMED = "session_renamed"
    PROMPT_STAGED = "prompt_staged"
    PROMPT_COPIED = "prompt_copied"
    RESPONSE_IMPORTED = "response_imported"
    DISCUSSION_NOTE = "discussion_note"


@dataclass
class TimelineEvent:
    """An immutable, timestamped event in a session's discussion lifecycle."""
    event_id: str
    session_id: str
    event_type: TimelineEventType
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    participant: Optional[str] = None
    content: Optional[str] = None
    status: str = "logged"
