from typing import Dict, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.core.agent_registry import AgentRegistry
from app.core.message_bridge import MessageExchangeBridge
from app.core.session_manager import SessionManager
from app.core.window_manager import WindowManager
from app.models.agent import AgentStatus, SUPPORTED_AGENTS
from app.models.session import AgentRoundStatus, ReasoningMode, ReasoningSession
from app.models.timeline_event import TimelineEventType
from app.ui.response_import_dialog import ResponseImportDialog
from app.ui.workspace.agent_panel import AgentPanel
from app.ui.workspace.consensus_panel import ConsensusPanel
from app.ui.workspace.discussion_timeline import DiscussionTimeline
from app.ui.workspace.prompt_composer import PromptComposer


class WorkspacePage(QWidget):
    """Central unified reasoning workspace page.

    Integrates:
    - Top: PromptComposer
    - Sub-header: Current Round Indicator & Epistemic Isolation Notice
    - Middle: Three AI Participant Panels (ChatGPT, Claude, Gemini)
    - Bottom: Shared Discussion Timeline & Consensus Panel
    """

    session_created = Signal(object)  # (ReasoningSession)

    def __init__(
        self,
        registry: AgentRegistry,
        window_manager: WindowManager,
        session_manager: SessionManager,
        message_bridge: Optional[MessageExchangeBridge] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.registry = registry
        self.window_mgr = window_manager
        self.session_mgr = session_manager
        self.bridge = message_bridge
        self.agent_panels: Dict[str, AgentPanel] = {}

        self._build_ui()
        self._wire_signals()
        self._update_round_banner()

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

        # 2. Round Indicator Banner
        self.round_banner = QFrame()
        self.round_banner.setObjectName("RoundBannerFrame")
        self.round_banner.setStyleSheet(
            "QFrame#RoundBannerFrame { background-color: #111720; border: 1px solid #1D2633; "
            "border-radius: 6px; padding: 10px 14px; }"
        )
        banner_layout = QHBoxLayout(self.round_banner)
        banner_layout.setContentsMargins(12, 8, 12, 8)
        banner_layout.setSpacing(12)

        round_info_layout = QVBoxLayout()
        round_info_layout.setSpacing(2)

        self.round_title_lbl = QLabel("ROUND 1 — INDEPENDENT REASONING")
        self.round_title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #60A5FA; letter-spacing: 0.5px;")
        round_info_layout.addWidget(self.round_title_lbl)

        self.round_sub_lbl = QLabel(
            "Epistemic Isolation Active: Models analyze the question independently without seeing peer answers."
        )
        self.round_sub_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        round_info_layout.addWidget(self.round_sub_lbl)

        banner_layout.addLayout(round_info_layout, 1)

        self.round_counter_pill = QLabel("0/3 Responses Accepted")
        self.round_counter_pill.setStyleSheet(
            "background-color: #1D2633; border: 1px solid #2B3543; border-radius: 12px; "
            "color: #94A3B8; font-size: 11px; font-weight: 700; padding: 4px 14px;"
        )
        banner_layout.addWidget(self.round_counter_pill)

        canvas_layout.addWidget(self.round_banner)

        # 3. Middle Section: Three AI Participant Panels
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

        # 4. Bottom Section: Discussion Timeline & Consensus Panel
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

        # Agent panel message bridge actions
        for agent_id, panel in self.agent_panels.items():
            panel.copy_focus_requested.connect(self._handle_copy_focus)
            panel.import_requested.connect(self._handle_import)

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

    def _handle_copy_focus(self, agent_id: str) -> None:
        """Copies staged prompt to system clipboard and focuses target application window."""
        session = self.session_mgr.current_session
        panel = self.agent_panels.get(agent_id)
        if not session:
            if panel:
                panel.show_feedback("Create or open a session first before copying prompt.", is_error=True)
            return

        if not self.bridge:
            if panel:
                panel.show_feedback("Message exchange bridge not available.", is_error=True)
            return

        success, msg = self.bridge.copy_and_focus(
            session_id=session.session_id,
            round_number=session.current_round,
            agent_id=agent_id,
        )

        if success:
            if panel:
                panel.set_round_status(AgentRoundStatus.PROMPT_COPIED)
                panel.show_feedback("Prompt copied to clipboard!", is_error=False)
            session.agent_statuses[agent_id] = AgentRoundStatus.PROMPT_COPIED

            defn = SUPPORTED_AGENTS.get(agent_id)
            name = defn.display_name if defn else agent_id
            self.session_mgr.add_timeline_event(
                session_id=session.session_id,
                round_number=session.current_round,
                event_type=TimelineEventType.PROMPT_COPIED,
                agent_id=agent_id,
                description=f"Copied Round {session.current_round} staged prompt for {name} to clipboard.",
            )
        else:
            if panel:
                panel.show_feedback(msg, is_error=True)

    def _handle_import(self, agent_id: str) -> None:
        """Opens inspection dialog, verifies provenance via SHA-256, and imports response."""
        session = self.session_mgr.current_session
        panel = self.agent_panels.get(agent_id)
        if not session:
            if panel:
                panel.show_feedback("Create or open a session first before importing response.", is_error=True)
            return

        if not self.bridge:
            if panel:
                panel.show_feedback("Message exchange bridge not available.", is_error=True)
            return

        defn = SUPPORTED_AGENTS.get(agent_id)
        if not defn:
            return

        # Check existing response revision
        existing = self.session_mgr.repo.db.get_latest_response_for_agent(
            session.session_id, session.current_round, agent_id
        )
        existing_rev = existing["revision_number"] if existing else None

        dialog = ResponseImportDialog(
            definition=defn,
            existing_revision=existing_rev,
            parent=self,
        )
        if dialog.exec():
            raw_text = dialog.confirmed_text
            if not raw_text:
                return

            success, msg, response_obj = self.bridge.import_response(
                session_id=session.session_id,
                round_number=session.current_round,
                agent_id=agent_id,
                response_text=raw_text,
                confirm_revision=dialog.confirmed_revision,
            )

            if success and response_obj:
                session.responses[agent_id] = response_obj
                session.agent_statuses[agent_id] = AgentRoundStatus.RESPONSE_ACCEPTED
                if panel:
                    panel.set_response(response_obj)
                    panel.show_feedback(f"Imported (SHA: {response_obj.sha256_hash[:8]}...)", is_error=False)

                self.session_mgr.add_timeline_event(
                    session_id=session.session_id,
                    round_number=session.current_round,
                    event_type=TimelineEventType.RESPONSE_IMPORTED,
                    agent_id=agent_id,
                    description=f"Imported response from {defn.display_name} ({response_obj.word_count:,} words, SHA-256: {response_obj.sha256_hash[:12]}...).",
                    metadata={
                        "response_id": response_obj.response_id,
                        "sha256_hash": response_obj.sha256_hash,
                        "word_count": response_obj.word_count,
                        "char_count": response_obj.char_count,
                        "revision": response_obj.revision_number,
                    },
                )
                self._update_round_banner()
            else:
                if panel:
                    panel.show_feedback(msg, is_error=True)

    def _update_round_banner(self) -> None:
        """Updates round indicator banner and progress counter pill."""
        session = self.session_mgr.current_session
        if not session:
            self.round_title_lbl.setText("ROUND 1 — INDEPENDENT REASONING (DRAFT)")
            self.round_sub_lbl.setText("Compose a question and create a session to stage independent prompts.")
            self.round_counter_pill.setText("Awaiting Session")
            self.round_counter_pill.setStyleSheet(
                "background-color: #1D2633; border: 1px solid #2B3543; border-radius: 12px; "
                "color: #94A3B8; font-size: 11px; font-weight: 700; padding: 4px 14px;"
            )
            return

        accepted_count = sum(
            1 for status in session.agent_statuses.values()
            if status == AgentRoundStatus.RESPONSE_ACCEPTED
        )
        total_participants = len(SUPPORTED_AGENTS)

        self.round_title_lbl.setText(f"ROUND {session.current_round} — INDEPENDENT REASONING")
        self.round_sub_lbl.setText(
            "Epistemic Isolation Active: Models analyze the question independently without seeing peer answers."
        )

        if accepted_count == total_participants:
            self.round_counter_pill.setText(f"{accepted_count}/{total_participants} — Round {session.current_round} Complete")
            self.round_counter_pill.setStyleSheet(
                "background-color: #0F3324; border: 1px solid #065F46; border-radius: 12px; "
                "color: #34D399; font-size: 11px; font-weight: 700; padding: 4px 14px;"
            )
        else:
            self.round_counter_pill.setText(f"{accepted_count}/{total_participants} Responses Accepted")
            self.round_counter_pill.setStyleSheet(
                "background-color: #1D2633; border: 1px solid #2B3543; border-radius: 12px; "
                "color: #94A3B8; font-size: 11px; font-weight: 700; padding: 4px 14px;"
            )

    def _on_session_created(self, session: ReasoningSession) -> None:
        self.composer.set_active_session(session)
        self.timeline.clear_events()
        events = self.session_mgr.get_timeline_events(session.session_id)
        self.timeline.set_events(events)

        # Clear responses for new session and show prompt staged
        for agent_id, panel in self.agent_panels.items():
            panel.set_response(None)
            status = session.agent_statuses.get(agent_id, AgentRoundStatus.PROMPT_STAGED)
            panel.set_round_status(status)
            panel.show_feedback("")

        self._update_round_banner()

    def _on_session_loaded(self, session: ReasoningSession) -> None:
        self.composer.set_active_session(session)
        self.timeline.clear_events()
        events = self.session_mgr.get_timeline_events(session.session_id)
        self.timeline.set_events(events)

        # If session has responses, update panels
        for agent_id, panel in self.agent_panels.items():
            resp = session.responses.get(agent_id)
            panel.set_response(resp)
            if not resp:
                status = session.agent_statuses.get(agent_id, AgentRoundStatus.PENDING)
                panel.set_round_status(status)
            panel.show_feedback("")

        self._update_round_banner()

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
            panel.show_feedback("")
        self._update_round_banner()
