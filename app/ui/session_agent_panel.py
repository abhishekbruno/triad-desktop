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

from app.models.agent import AgentAppDefinition, AgentConnection, AgentStatus
from app.models.session import AgentRoundStatus, ModelResponse


class SessionAgentPanel(QFrame):
    """Card widget representing an agent participant in an active reasoning session."""

    copy_focus_requested = Signal(str)  # (agent_id)
    import_requested = Signal(str)      # (agent_id)

    def __init__(self, definition: AgentAppDefinition, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.definition = definition
        self.agent_id = definition.agent_id
        self.current_response: Optional[ModelResponse] = None

        self.setObjectName("SessionAgentPanel")
        self.setStyleSheet(
            "QFrame#SessionAgentPanel { background-color: #13161f; border: 1px solid #222634; "
            "border-radius: 8px; margin: 4px; }"
        )

        self._build_ui()
        self.set_round_status(AgentRoundStatus.PENDING)
        self.set_connection_status(AgentStatus.MISSING)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header Row
        header = QHBoxLayout()
        accent = QFrame()
        accent.setFixedWidth(4)
        accent.setFixedHeight(20)
        accent.setStyleSheet(f"background-color: {self.definition.accent_color}; border-radius: 2px;")
        header.addWidget(accent)

        name_lbl = QLabel(self.definition.display_name)
        name_lbl.setStyleSheet("font-size: 15px; font-weight: 600; color: #f8fafc;")
        header.addWidget(name_lbl)
        header.addStretch()

        self.conn_pill = QLabel("APP: MISSING")
        self.conn_pill.setStyleSheet(
            "font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 4px; "
            "background-color: #21242d; color: #94a3b8; border: 1px solid #333846;"
        )
        header.addWidget(self.conn_pill)

        self.round_pill = QLabel("PENDING")
        self.round_pill.setStyleSheet(
            "font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; "
            "background-color: #262933; color: #94a3b8; border: 1px solid #383e4d;"
        )
        header.addWidget(self.round_pill)
        layout.addLayout(header)

        # Action Buttons Row
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        self.btn_copy_focus = QPushButton(f"Copy & Focus")
        self.btn_copy_focus.setStyleSheet(
            f"QPushButton {{ background-color: #18202f; border: 1px solid #2d3b55; "
            f"color: #e2e8f0; border-radius: 5px; padding: 7px 12px; font-weight: 600; font-size: 11px; }} "
            f"QPushButton:hover {{ background-color: #222f46; border-color: {self.definition.accent_color}; }}"
        )
        self.btn_copy_focus.clicked.connect(lambda: self.copy_focus_requested.emit(self.agent_id))
        btn_layout.addWidget(self.btn_copy_focus, 1)

        self.btn_import = QPushButton("Import Response")
        self.btn_import.setStyleSheet(
            "QPushButton { background-color: #172420; border: 1px solid #1f3d33; "
            "color: #34d399; border-radius: 5px; padding: 7px 12px; font-weight: 600; font-size: 11px; } "
            "QPushButton:hover { background-color: #1f362c; border-color: #10b981; }"
        )
        self.btn_import.clicked.connect(lambda: self.import_requested.emit(self.agent_id))
        btn_layout.addWidget(self.btn_import, 1)

        layout.addLayout(btn_layout)

        # Response Preview Box
        self.preview_box = QTextEdit()
        self.preview_box.setReadOnly(True)
        self.preview_box.setPlaceholderText("No response imported yet. Copy prompt and paste answer here...")
        self.preview_box.setStyleSheet(
            "background-color: #0b0d12; border: 1px solid #1c212e; border-radius: 6px; "
            "color: #cbd5e1; font-family: 'Consolas', monospace; font-size: 11px; padding: 8px;"
        )
        layout.addWidget(self.preview_box, 1)

        # Telemetry Footer
        self.telemetry_lbl = QLabel("Awaiting response transfer...")
        self.telemetry_lbl.setStyleSheet("font-size: 10px; color: #64748b; font-family: monospace;")
        layout.addWidget(self.telemetry_lbl)

    def set_connection_status(self, status: AgentStatus) -> None:
        """Updates desktop application connection pill."""
        if status == AgentStatus.BOUND:
            self.conn_pill.setText("APP: BOUND")
            self.conn_pill.setStyleSheet(
                "font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 4px; "
                "background-color: #064e3b; color: #34d399; border: 1px solid #059669;"
            )
        elif status == AgentStatus.DETECTED:
            self.conn_pill.setText("APP: DETECTED")
            self.conn_pill.setStyleSheet(
                "font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 4px; "
                "background-color: #2e2612; color: #fbbf24; border: 1px solid #78350f;"
            )
        elif status == AgentStatus.STALE:
            self.conn_pill.setText("APP: STALE")
            self.conn_pill.setStyleSheet(
                "font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 4px; "
                "background-color: #450a0a; color: #f87171; border: 1px solid #991b1b;"
            )
        else:
            self.conn_pill.setText("APP: MISSING")
            self.conn_pill.setStyleSheet(
                "font-size: 10px; font-weight: 600; padding: 2px 7px; border-radius: 4px; "
                "background-color: #21242d; color: #94a3b8; border: 1px solid #333846;"
            )

    def set_round_status(self, status: AgentRoundStatus) -> None:
        """Updates round status indicator pill."""
        if status == AgentRoundStatus.RESPONSE_ACCEPTED:
            self.round_pill.setText("ACCEPTED")
            self.round_pill.setStyleSheet(
                "font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; "
                "background-color: #064e3b; color: #34d399; border: 1px solid #059669;"
            )
        elif status == AgentRoundStatus.PROMPT_COPIED:
            self.round_pill.setText("PROMPT COPIED")
            self.round_pill.setStyleSheet(
                "font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; "
                "background-color: #2e2612; color: #fbbf24; border: 1px solid #78350f;"
            )
        elif status == AgentRoundStatus.PROMPT_STAGED:
            self.round_pill.setText("PROMPT READY")
            self.round_pill.setStyleSheet(
                "font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; "
                "background-color: #1e283b; color: #93c5fd; border: 1px solid #3b82f6;"
            )
        else:
            self.round_pill.setText("PENDING")
            self.round_pill.setStyleSheet(
                "font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 4px; "
                "background-color: #262933; color: #94a3b8; border: 1px solid #383e4d;"
            )

    def set_response(self, response: ModelResponse) -> None:
        """Populates the preview with an accepted model response."""
        self.current_response = response
        self.preview_box.setPlainText(response.raw_response)
        self.set_round_status(AgentRoundStatus.RESPONSE_ACCEPTED)

        sha_short = response.sha256_hash[:16]
        rev_text = f"Rev {response.revision_number}"
        self.telemetry_lbl.setText(
            f"Words: {response.word_count:,} | Chars: {response.char_count:,} | {rev_text} | SHA: {sha_short}..."
        )

    def clear(self) -> None:
        """Resets the panel for a new session."""
        self.current_response = None
        self.preview_box.clear()
        self.set_round_status(AgentRoundStatus.PENDING)
        self.telemetry_lbl.setText("Awaiting response transfer...")

