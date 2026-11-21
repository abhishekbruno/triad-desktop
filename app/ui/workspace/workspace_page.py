from typing import Dict, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.agent_registry import AgentRegistry
from app.core.session_manager import SessionManager
from app.core.window_manager import WindowManager
from app.models.agent import AgentStatus, SUPPORTED_AGENTS
from app.models.session import ReasoningMode, ReasoningSession
from app.ui.workspace.agent_panel import AgentPanel
from app.ui.workspace.consensus_panel import ConsensusPanel
from app.ui.workspace.discussion_timeline import DiscussionTimeline
from app.ui.workspace.prompt_composer import PromptComposer


class WorkspacePage(QWidget):
    """Central unified reasoning workspace page.

    Integrates:
    - Top: PromptComposer
    - Middle: Three AI Participant Panels (ChatGPT, Claude, Gemini)
    - Bottom: Shared Discussion Timeline & Consensus Panel
    """

    session_created = Signal(object)  # (ReasoningSession)

    def __init__(
        self,
        registry: AgentRegistry,
        window_manager: WindowManager,
        session_manager: SessionManager,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.registry = registry
        self.window_mgr = window_manager
        self.session_mgr = session_manager
        self.agent_panels: Dict[str, AgentPanel] = {}

        self._build_ui()
        self._wire_signals()

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Main scrollable canvas so nothing gets clipped on smaller resolutions
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        canvas = QWidget()
        canvas_layout = QVBoxLayout(canvas)
        canvas_layout.setContentsMargins(18, 16, 18, 16)
        canvas_layout.setSpacing(14)

        # 1. Top Section: Prompt Composer
        self.composer = PromptComposer(canvas)
        canvas_layout.addWidget(self.composer)

        # 2. Middle Section: Three AI Participant Panels
        participants_frame = QFrame()
        participants_layout = QHBoxLayout(participants_frame)
        participants_layout.setContentsMargins(0, 0, 0, 0)
        participants_layout.setSpacing(12)

        for agent_id, defn in SUPPORTED_AGENTS.items():
            panel = AgentPanel(definition=defn, window_manager=self.window_mgr, parent=participants_frame)
            panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            self.agent_panels[agent_id] = panel
            participants_layout.addWidget(panel)

        canvas_layout.addWidget(participants_frame)

        # 3. Bottom Section: Discussion Timeline & Consensus Panel
        bottom_frame = QFrame()
        bottom_layout = QHBoxLayout(bottom_frame)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(12)

        self.timeline = DiscussionTimeline(bottom_frame)
        self.timeline.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bottom_layout.addWidget(self.timeline, 3)

        self.consensus = ConsensusPanel(bottom_frame)
        self.consensus.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bottom_layout.addWidget(self.consensus, 2)

        canvas_layout.addWidget(bottom_frame)

        scroll.setWidget(canvas)
        root_layout.addWidget(scroll)

    def _wire_signals(self) -> None:
        # PromptComposer creates session via SessionManager
        self.composer.create_session_requested.connect(self._handle_create_session)

        # SessionManager signals
        self.session_mgr.session_created.connect(self._on_session_created)
        self.session_mgr.session_loaded.connect(self._on_session_loaded)
        self.session_mgr.timeline_event_added.connect(self.timeline.add_event)

        # Initial registry synchronization
        self.sync_agent_panels()

    def _handle_create_session(self, title: str, question: str, mode_key: str, max_rounds: int) -> None:
        try:
            mode = ReasoningMode(mode_key)
        except ValueError:
            mode = ReasoningMode.QUICK_CONSENSUS

        session = self.session_mgr.create_session(
            title=title,
            initial_question=question,
            mode=mode,
            max_rounds=max_rounds,
        )
        self.session_created.emit(session)

    def _on_session_created(self, session: ReasoningSession) -> None:
        self.composer.set_active_session(session)
        self.timeline.clear_events()
        events = self.session_mgr.get_timeline_events(session.session_id)
        self.timeline.set_events(events)

        # Clear responses for new session
        for panel in self.agent_panels.values():
            panel.set_response(None)

    def _on_session_loaded(self, session: ReasoningSession) -> None:
        self.composer.set_active_session(session)
        self.timeline.clear_events()
        events = self.session_mgr.get_timeline_events(session.session_id)
        self.timeline.set_events(events)

        # If session has responses, update panels
        for agent_id, panel in self.agent_panels.items():
            resp = session.responses.get(agent_id)
            panel.set_response(resp)

    def sync_agent_panels(self) -> None:
        """Updates each AgentPanel with live connection status from AgentRegistry."""
        for agent_id, panel in self.agent_panels.items():
            conn = self.registry.get_connection(agent_id)
            if conn:
                panel.set_connection(conn)
            else:
                panel.set_connection_status(AgentStatus.MISSING)

    def set_reasoning_mode(self, mode_value: str) -> None:
        """Sets mode from sidebar selection."""
        self.composer.set_reasoning_mode(mode_value)
        if self.session_mgr.current_session:
            try:
                self.session_mgr.set_reasoning_mode(ReasoningMode(mode_value))
            except ValueError:
                pass

    def start_new_discussion(self) -> None:
        """Resets composer for a new discussion."""
        self.composer.start_new_draft()
        self.timeline.clear_events()
        for panel in self.agent_panels.values():
            panel.set_response(None)
