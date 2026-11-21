from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.models.timeline_event import TimelineEvent, TimelineEventType


class TimelineEventWidget(QFrame):
    """Component rendering an individual discussion timeline event."""

    BADGE_COLORS = {
        TimelineEventType.SESSION_CREATED: ("#1E3A5F", "#60A5FA", "CREATED"),
        TimelineEventType.MODE_CHANGED: ("#2D1F4F", "#C084FC", "MODE"),
        TimelineEventType.CONFIG_UPDATED: ("#3B2E14", "#FBBF24", "CONFIG"),
        TimelineEventType.PARTICIPANT_CONFIGURED: ("#0F3324", "#34D399", "AGENT"),
        TimelineEventType.SESSION_REOPENED: ("#1F2937", "#9CA3AF", "REOPENED"),
        TimelineEventType.SESSION_RENAMED: ("#362B17", "#F59E0B", "RENAMED"),
        TimelineEventType.PROMPT_STAGED: ("#172554", "#93C5FD", "STAGED"),
        TimelineEventType.PROMPT_COPIED: ("#2E2612", "#FCD34D", "COPIED"),
        TimelineEventType.RESPONSE_IMPORTED: ("#064E3B", "#34D399", "IMPORTED"),
        TimelineEventType.DISCUSSION_NOTE: ("#1E293B", "#CBD5E1", "NOTE"),
    }

    def __init__(self, event: TimelineEvent, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.timeline_event = event
        self.setStyleSheet(
            "QFrame { background-color: #111720; border: 1px solid #1D2633; border-radius: 6px; padding: 6px; }"
        )
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        # Event Type Badge
        bg, fg, label = self.BADGE_COLORS.get(
            self.timeline_event.event_type, ("#1E293B", "#94A3B8", self.timeline_event.event_type.value.upper())
        )
        badge = QLabel(label)
        badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; font-size: 10px; font-weight: 700; "
            f"padding: 2px 6px; border-radius: 4px; border: 1px solid {fg}40;"
        )
        header_row.addWidget(badge)

        # Participant label if applicable
        if self.timeline_event.participant:
            part_lbl = QLabel(f"[{self.timeline_event.participant.upper()}]")
            part_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #EDF2F7;")
            header_row.addWidget(part_lbl)

        header_row.addStretch()

        # Timestamp
        ts_str = self.timeline_event.timestamp[:19].replace("T", " ")
        ts_lbl = QLabel(ts_str)
        ts_lbl.setStyleSheet("font-size: 10px; color: #64748B; font-family: monospace;")
        header_row.addWidget(ts_lbl)

        layout.addLayout(header_row)

        # Event Content
        if self.timeline_event.content:
            content_lbl = QLabel(self.timeline_event.content)
            content_lbl.setWordWrap(True)
            content_lbl.setStyleSheet("font-size: 11px; color: #CBD5E1;")
            layout.addWidget(content_lbl)


class DiscussionTimeline(QFrame):
    """Permanent discussion timeline displaying genuine local session events."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("DiscussionTimeline")
        self.setProperty("class", "surface-card")

        self.events: List[TimelineEvent] = []
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # Header
        header_row = QHBoxLayout()
        title_lbl = QLabel("SHARED DISCUSSION TIMELINE")
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #4285F4; letter-spacing: 0.8px;")
        header_row.addWidget(title_lbl)

        header_row.addStretch()

        self.count_badge = QLabel("0 events")
        self.count_badge.setStyleSheet(
            "background-color: #1D2633; border: 1px solid #2B3543; border-radius: 10px; "
            "padding: 2px 8px; font-size: 10px; color: #94A3B8;"
        )
        header_row.addWidget(self.count_badge)
        layout.addLayout(header_row)

        # Scrollable events container
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setStyleSheet("background-color: transparent;")

        self.container = QWidget()
        self.container.setStyleSheet("background-color: transparent;")
        self.events_layout = QVBoxLayout(self.container)
        self.events_layout.setContentsMargins(0, 0, 0, 0)
        self.events_layout.setSpacing(6)

        # Empty state label
        self.empty_label = QLabel(
            "No discussion events recorded yet.\nCreate or open a session to start tracking reasoning events."
        )
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("color: #64748B; font-size: 11px; padding: 30px;")
        self.events_layout.addWidget(self.empty_label)

        self.events_layout.addStretch()
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, 1)

    def set_events(self, events: List[TimelineEvent]) -> None:
        """Populates the timeline with a list of events."""
        self.clear_events()
        for ev in events:
            self.add_event(ev)

    def add_event(self, event: TimelineEvent) -> None:
        """Appends a new timeline event and updates count."""
        if self.empty_label.isVisible():
            self.empty_label.setVisible(False)

        widget = TimelineEventWidget(event, self.container)
        # Insert before stretch item at end
        count = self.events_layout.count()
        self.events_layout.insertWidget(max(0, count - 1), widget)
        self.events.append(event)
        self.count_badge.setText(f"{len(self.events)} events")

    def clear_events(self) -> None:
        """Removes all event widgets from the timeline."""
        self.events.clear()
        self.count_badge.setText("0 events")

        # Remove all widgets except empty_label and stretch
        while self.events_layout.count() > 2:
            item = self.events_layout.takeAt(1)
            if item.widget() and item.widget() != self.empty_label:
                item.widget().deleteLater()

        self.empty_label.setVisible(True)
