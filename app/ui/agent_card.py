from typing import Callable, List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.models.agent import (
    AgentAppDefinition,
    AgentConnection,
    AgentStatus,
    WindowCandidate,
)
from app.ui.window_picker_dialog import WindowPickerDialog


class AgentCard(QFrame):
    """UI Card displaying detected identity, status, and controls for an AI desktop application."""

    connect_requested = Signal(str, object)   # (agent_id, WindowCandidate)
    focus_requested = Signal(str)             # (agent_id)
    disconnect_requested = Signal(str)        # (agent_id)

    def __init__(self, definition: AgentAppDefinition, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.definition = definition
        self.agent_id = definition.agent_id
        self.current_connection: Optional[AgentConnection] = None
        self.available_candidates: List[WindowCandidate] = []

        self.setObjectName("AgentCard")
        self.setProperty("class", "agent-card")

        self._build_ui()
        self.update_status(AgentStatus.MISSING)

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header (Accent line + Name + Status Pill)
        header_widget = QWidget()
        header_widget.setObjectName("CardHeader")
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 14, 16, 12)

        # Accent color bar
        accent_bar = QFrame()
        accent_bar.setObjectName("AccentIndicator")
        accent_bar.setFixedWidth(5)
        accent_bar.setFixedHeight(22)
        accent_bar.setStyleSheet(f"background-color: {self.definition.accent_color}; border-radius: 2px;")
        header_layout.addWidget(accent_bar)

        # Name
        self.title_label = QLabel(self.definition.display_name)
        self.title_label.setObjectName("AgentNameLabel")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        # Status Pill
        self.status_pill = QLabel("MISSING")
        self.status_pill.setProperty("class", "status-pill")
        self.status_pill.setProperty("status", "missing")
        header_layout.addWidget(self.status_pill)

        main_layout.addWidget(header_widget)

        # 2. Details Panel
        details_widget = QWidget()
        details_widget.setObjectName("CardDetailsPanel")
        details_layout = QVBoxLayout(details_widget)
        details_layout.setContentsMargins(16, 12, 16, 12)
        details_layout.setSpacing(8)

        # Process Row
        proc_box = QHBoxLayout()
        proc_lbl = QLabel("PROCESS:")
        proc_lbl.setProperty("class", "detail-label")
        proc_lbl.setFixedWidth(70)
        self.proc_val = QLabel("None running")
        self.proc_val.setProperty("class", "detail-value")
        proc_box.addWidget(proc_lbl)
        proc_box.addWidget(self.proc_val)
        details_layout.addLayout(proc_box)

        # Window Row
        win_box = QHBoxLayout()
        win_lbl = QLabel("WINDOW:")
        win_lbl.setProperty("class", "detail-label")
        win_lbl.setFixedWidth(70)
        self.win_val = QLabel("None bound")
        self.win_val.setProperty("class", "detail-value")
        win_box.addWidget(win_lbl)
        win_box.addWidget(self.win_val)
        details_layout.addLayout(win_box)

        # Path Row
        path_box = QHBoxLayout()
        path_lbl = QLabel("LOCATION:")
        path_lbl.setProperty("class", "detail-label")
        path_lbl.setFixedWidth(70)
        self.path_val = QLabel("Not detected")
        self.path_val.setProperty("class", "detail-value")
        path_box.addWidget(path_lbl)
        path_box.addWidget(self.path_val)
        details_layout.addLayout(path_box)

        main_layout.addWidget(details_widget)
        main_layout.addStretch()

        # 3. Action Buttons
        actions_widget = QWidget()
        actions_widget.setObjectName("CardActionsPanel")
        actions_layout = QHBoxLayout(actions_widget)
        actions_layout.setContentsMargins(16, 10, 16, 14)
        actions_layout.setSpacing(8)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setProperty("class", "card-btn btn-connect")
        self.btn_connect.clicked.connect(self._on_connect_clicked)

        self.btn_focus = QPushButton("Focus")
        self.btn_focus.setProperty("class", "card-btn btn-focus")
        self.btn_focus.clicked.connect(lambda: self.focus_requested.emit(self.agent_id))

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setProperty("class", "card-btn btn-disconnect")
        self.btn_disconnect.clicked.connect(lambda: self.disconnect_requested.emit(self.agent_id))

        actions_layout.addWidget(self.btn_connect)
        actions_layout.addWidget(self.btn_focus)
        actions_layout.addWidget(self.btn_disconnect)

        main_layout.addWidget(actions_widget)

    def set_candidates(self, candidates: List[WindowCandidate]) -> None:
        """Updates available candidate windows discovered for this agent."""
        self.available_candidates = candidates
        if candidates and (not self.current_connection or self.current_connection.status != AgentStatus.BOUND):
            best = candidates[0]
            self.proc_val.setText(f"{best.executable_name} (PID: {best.pid})")
            self.win_val.setText(f"Candidate: '{best.title[:26]}...' ({hex(best.hwnd)})")
            self.path_val.setText(best.executable_path or "Standard Path")
            self.update_status(AgentStatus.DETECTED)

    def set_connection(self, connection: AgentConnection) -> None:
        """Applies an active or updated connection record."""
        self.current_connection = connection
        self.update_status(connection.status)

        if connection.status == AgentStatus.BOUND:
            self.proc_val.setText(f"PID: {connection.process_id}")
            self.win_val.setText(f"HWND: {hex(connection.window_handle or 0)} [Bound]")
            self.path_val.setText(connection.executable_path or "Accessible Path")
        elif connection.status == AgentStatus.STALE:
            self.win_val.setText("Window Invalid / Terminated")
        elif connection.status == AgentStatus.MISSING:
            self.proc_val.setText("None running")
            self.win_val.setText("None bound")
            self.path_val.setText("Not detected")

    def update_status(self, status: AgentStatus) -> None:
        """Updates status badge and button enabled states."""
        self.status_pill.setText(status.value.upper())
        self.status_pill.setProperty("status", status.value)
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

        if status == AgentStatus.BOUND:
            self.btn_connect.setEnabled(False)
            self.btn_focus.setEnabled(True)
            self.btn_disconnect.setEnabled(True)
        elif status == AgentStatus.DETECTED:
            self.btn_connect.setEnabled(True)
            self.btn_focus.setEnabled(False)
            self.btn_disconnect.setEnabled(False)
        elif status == AgentStatus.STALE:
            self.btn_connect.setEnabled(len(self.available_candidates) > 0)
            self.btn_focus.setEnabled(False)
            self.btn_disconnect.setEnabled(True)
        else:  # MISSING
            self.btn_connect.setEnabled(len(self.available_candidates) > 0)
            self.btn_focus.setEnabled(False)
            self.btn_disconnect.setEnabled(False)

    def _on_connect_clicked(self) -> None:
        """Handles user clicking Connect / Bind."""
        if not self.available_candidates:
            return

        if len(self.available_candidates) == 1:
            # Single candidate: connect directly
            self.connect_requested.emit(self.agent_id, self.available_candidates[0])
        else:
            # Multiple candidates: let user choose
            dlg = WindowPickerDialog(self.definition.display_name, self.available_candidates, self)
            if dlg.exec() and dlg.selected_candidate:
                self.connect_requested.emit(self.agent_id, dlg.selected_candidate)

