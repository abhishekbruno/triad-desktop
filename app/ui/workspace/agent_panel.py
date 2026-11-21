from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.window_manager import WindowManager
from app.models.agent import AgentAppDefinition, AgentConnection, AgentStatus, WindowCandidate
from app.models.session import AgentRoundStatus, ModelResponse


class AgentPanel(QFrame):
    """Reusable participant panel for an AI application (ChatGPT, Claude, Gemini).

    Displays:
    - Accent bar, Agent name
    - Phase 1 desktop connection status (Missing, Detected, Bound, Stale)
    - Bound window details (PID, HWND, Title)
    - 'Focus Application' button connected to WindowManager
    - Response status (Not Requested, Awaiting Import, Imported, Error)
    - Response text area (read-only)
    - Expand / Collapse toggle
    """

    focus_requested = Signal(str)           # (agent_id)
    copy_focus_requested = Signal(str)      # (agent_id) — extension for Phase 2B
    import_requested = Signal(str)          # (agent_id) — extension for Phase 2B

    def __init__(
        self,
        definition: AgentAppDefinition,
        window_manager: Optional[WindowManager] = None,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.definition = definition
        self.agent_id = definition.agent_id
        self.window_mgr = window_manager
        self.current_candidate: Optional[WindowCandidate] = None
        self.current_connection: Optional[AgentConnection] = None
        self.current_response: Optional[ModelResponse] = None
        self.is_expanded = True

        self.setObjectName(f"AgentPanel_{self.agent_id}")
        self.setProperty("class", "surface-card")

        self._build_ui()
        self.set_connection_status(AgentStatus.MISSING)
        self.set_response_status("Not Requested", "missing")

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(8)

        # 1. Header (Accent line + Name + Status Pills + Collapse)
        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setFixedHeight(22)
        accent.setStyleSheet(f"background-color: {self.definition.accent_color}; border-radius: 2px;")
        header_row.addWidget(accent)

        self.name_lbl = QLabel(self.definition.display_name)
        self.name_lbl.setStyleSheet("font-size: 14px; font-weight: 700; color: #EDF2F7;")
        header_row.addWidget(self.name_lbl)

        header_row.addStretch()

        # Connection status pill
        self.conn_pill = QLabel("MISSING")
        self.conn_pill.setProperty("class", "status-pill")
        self.conn_pill.setProperty("status", "missing")
        header_row.addWidget(self.conn_pill)

        # Response status pill
        self.resp_pill = QLabel("NOT REQUESTED")
        self.resp_pill.setProperty("class", "status-pill")
        self.resp_pill.setProperty("status", "missing")
        header_row.addWidget(self.resp_pill)

        # Collapse / Expand button
        self.btn_toggle_expand = QPushButton("▼")
        self.btn_toggle_expand.setFixedSize(22, 22)
        self.btn_toggle_expand.setStyleSheet(
            "QPushButton { background: transparent; border: none; color: #94A3B8; font-size: 10px; } "
            "QPushButton:hover { color: #EDF2F7; }"
        )
        self.btn_toggle_expand.setToolTip("Expand / Collapse response panel")
        self.btn_toggle_expand.clicked.connect(self.toggle_expand)
        header_row.addWidget(self.btn_toggle_expand)

        layout.addLayout(header_row)

        # 2. Window Telemetry Row
        self.telemetry_frame = QFrame()
        self.telemetry_frame.setStyleSheet("background-color: #111720; border: 1px solid #1D2633; border-radius: 4px; padding: 6px;")
        telem_layout = QVBoxLayout(self.telemetry_frame)
        telem_layout.setContentsMargins(8, 6, 8, 6)
        telem_layout.setSpacing(4)

        self.lbl_proc = QLabel("Process: Not detected")
        self.lbl_proc.setStyleSheet("font-size: 11px; color: #94A3B8; font-family: monospace;")
        telem_layout.addWidget(self.lbl_proc)

        self.lbl_win = QLabel("Window: No window bound")
        self.lbl_win.setStyleSheet("font-size: 11px; color: #64748B; font-family: monospace;")
        telem_layout.addWidget(self.lbl_win)

        layout.addWidget(self.telemetry_frame)

        # 3. Action Row (Copy & Focus, Import Response, Focus buttons)
        actions_row = QHBoxLayout()
        actions_row.setSpacing(6)

        self.btn_copy_focus = QPushButton("Copy & Focus")
        self.btn_copy_focus.setToolTip("Copy staged prompt to clipboard and switch focus to this window")
        self.btn_copy_focus.setStyleSheet(
            "QPushButton { background-color: #18202F; border: 1px solid #2D3B55; "
            "border-radius: 4px; color: #E2E8F0; font-size: 11px; font-weight: 600; padding: 5px 8px; } "
            "QPushButton:hover { background-color: #243042; border-color: #4285F4; } "
            "QPushButton:disabled { background-color: #111720; color: #64748B; border-color: #1D2633; }"
        )
        self.btn_copy_focus.clicked.connect(lambda: self.copy_focus_requested.emit(self.agent_id))
        actions_row.addWidget(self.btn_copy_focus, 3)

        self.btn_import = QPushButton("Import Response")
        self.btn_import.setToolTip("Inspect, verify provenance, and import response copied from this application")
        self.btn_import.setStyleSheet(
            "QPushButton { background-color: #172420; border: 1px solid #1F3D33; "
            "border-radius: 4px; color: #34D399; font-size: 11px; font-weight: 600; padding: 5px 8px; } "
            "QPushButton:hover { background-color: #1F362C; border-color: #10B981; } "
            "QPushButton:disabled { background-color: #111720; color: #64748B; border-color: #1D2633; }"
        )
        self.btn_import.clicked.connect(lambda: self.import_requested.emit(self.agent_id))
        actions_row.addWidget(self.btn_import, 3)

        self.btn_focus = QPushButton("Focus")
        self.btn_focus.setToolTip("Bring this application's window to foreground")
        self.btn_focus.setStyleSheet(
            "QPushButton { background-color: #1D2633; border: 1px solid #2B3543; "
            "border-radius: 4px; color: #94A3B8; font-size: 11px; font-weight: 600; padding: 5px 8px; } "
            "QPushButton:hover { background-color: #243042; border-color: #425268; color: #EDF2F7; } "
            "QPushButton:disabled { background-color: #111720; color: #64748B; border-color: #1D2633; }"
        )
        self.btn_focus.clicked.connect(self._on_focus_clicked)
        actions_row.addWidget(self.btn_focus, 2)

        layout.addLayout(actions_row)

        # Inline focus feedback message (e.g. error if window invalid)
        self.feedback_lbl = QLabel("")
        self.feedback_lbl.setStyleSheet("font-size: 10px; color: #F87171; font-weight: 500;")
        self.feedback_lbl.setVisible(False)
        layout.addWidget(self.feedback_lbl)

        # 4. Response Container
        self.response_container = QWidget()
        resp_layout = QVBoxLayout(self.response_container)
        resp_layout.setContentsMargins(0, 0, 0, 0)
        resp_layout.setSpacing(6)

        self.response_text = QTextEdit()
        self.response_text.setReadOnly(True)
        self.response_text.setPlaceholderText("No response imported yet. Prepare question and initiate discussion to receive responses.")
        self.response_text.setMinimumHeight(140)
        self.response_text.setStyleSheet(
            "background-color: #0B0F14; border: 1px solid #1D2633; border-radius: 6px; "
            "color: #CBD5E1; font-size: 11px; padding: 8px; font-family: 'Consolas', monospace;"
        )
        resp_layout.addWidget(self.response_text)

        self.telemetry_lbl = QLabel("Awaiting response import...")
        self.telemetry_lbl.setStyleSheet("font-size: 10px; color: #64748B; font-family: monospace;")
        resp_layout.addWidget(self.telemetry_lbl)

        layout.addWidget(self.response_container)

    def toggle_expand(self) -> None:
        """Toggles response container visibility."""
        self.is_expanded = not self.is_expanded
        self.response_container.setVisible(self.is_expanded)
        self.btn_toggle_expand.setText("▼" if self.is_expanded else "▲")

    def set_connection(self, connection: AgentConnection) -> None:
        """Applies an active or updated connection record."""
        self.current_connection = connection
        self.set_connection_status(connection.status)
        if connection.status == AgentStatus.BOUND:
            self.lbl_proc.setText(f"Process: PID {connection.process_id}")
            self.lbl_win.setText(f"Window: HWND {hex(connection.window_handle or 0)} [Bound]")
            self.btn_focus.setEnabled(True)
        elif connection.status == AgentStatus.STALE:
            self.lbl_win.setText("Window: Invalid or Terminated")
            self.btn_focus.setEnabled(False)
        elif connection.status == AgentStatus.DETECTED:
            if connection.process_id:
                self.lbl_proc.setText(f"Process: PID {connection.process_id}")
            if connection.window_handle:
                self.lbl_win.setText(f"Window: HWND {hex(connection.window_handle)}")
            self.btn_focus.setEnabled(False)
        else:
            self.lbl_proc.setText("Process: Not detected")
            self.lbl_win.setText("Window: No window bound")
            self.btn_focus.setEnabled(False)

    def set_connection_status(self, status: AgentStatus, candidate: Optional[WindowCandidate] = None) -> None:
        """Updates the desktop application connection pill and telemetry details."""
        status_name = status.value.upper()
        self.conn_pill.setText(status_name)
        self.conn_pill.setProperty("status", status.value)

        # Refresh styling
        self.conn_pill.style().unpolish(self.conn_pill)
        self.conn_pill.style().polish(self.conn_pill)

        if candidate:
            self.current_candidate = candidate
            self.lbl_proc.setText(f"Process: {candidate.executable_name} (PID: {candidate.pid})")
            win_title = candidate.title if len(candidate.title) <= 30 else candidate.title[:28] + "..."
            self.lbl_win.setText(f"Window: '{win_title}' ({hex(candidate.hwnd)})")
            self.btn_focus.setEnabled(True)
        else:
            if status == AgentStatus.MISSING:
                self.current_candidate = None
                self.lbl_proc.setText("Process: Not detected")
                self.lbl_win.setText("Window: No window bound")
                self.btn_focus.setEnabled(False)

    def show_feedback(self, text: str, is_error: bool = False) -> None:
        """Displays inline feedback message below action row."""
        if not text:
            self.feedback_lbl.setText("")
            self.feedback_lbl.setVisible(False)
            return

        color = "#F87171" if is_error else "#34D399"
        self.feedback_lbl.setStyleSheet(f"font-size: 10px; color: {color}; font-weight: 500;")
        self.feedback_lbl.setText(text)
        self.feedback_lbl.setVisible(True)

    def set_round_status(self, status: AgentRoundStatus) -> None:
        """Updates the response status pill according to session round status."""
        if status == AgentRoundStatus.RESPONSE_ACCEPTED:
            self.set_response_status("ACCEPTED", "bound")
        elif status == AgentRoundStatus.PROMPT_COPIED:
            self.set_response_status("COPIED", "detected")
        elif status == AgentRoundStatus.PROMPT_STAGED:
            self.set_response_status("STAGED", "missing")
        else:
            self.set_response_status("PENDING", "missing")

    def set_response_status(self, status_text: str, status_type: str = "missing") -> None:
        """Updates the response status pill."""
        self.resp_pill.setText(status_text.upper())
        self.resp_pill.setProperty("status", status_type)
        self.resp_pill.style().unpolish(self.resp_pill)
        self.resp_pill.style().polish(self.resp_pill)

    def set_response(self, response: Optional[ModelResponse]) -> None:
        """Displays real imported response data with provenance verification."""
        self.current_response = response
        if response:
            self.response_text.setPlainText(response.raw_response)
            self.set_round_status(AgentRoundStatus.RESPONSE_ACCEPTED)
            rev_text = f"Rev {response.revision_number}"
            self.telemetry_lbl.setText(
                f"Words: {response.word_count:,} | Chars: {response.char_count:,} | {rev_text} | SHA-256: {response.sha256_hash[:12]}..."
            )
        else:
            self.response_text.clear()
            self.set_round_status(AgentRoundStatus.PENDING)
            self.telemetry_lbl.setText("Awaiting response import...")

    def _on_focus_clicked(self) -> None:
        """Handles click on Focus Application button using WindowManager."""
        self.feedback_lbl.setVisible(False)
        self.focus_requested.emit(self.agent_id)

        hwnd = None
        if self.current_connection and self.current_connection.window_handle:
            hwnd = self.current_connection.window_handle
        elif self.current_candidate:
            hwnd = self.current_candidate.hwnd

        if not self.window_mgr or not hwnd:
            self.feedback_lbl.setText("Error: No active window registered to focus.")
            self.feedback_lbl.setVisible(True)
            return

        success = self.window_mgr.focus_window(hwnd)
        if not success:
            self.feedback_lbl.setText(f"Focus failed: Window handle {hex(hwnd)} is invalid or minimized.")
            self.feedback_lbl.setVisible(True)
