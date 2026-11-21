import hashlib
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.models.agent import AgentAppDefinition


class ResponseImportDialog(QDialog):
    """Modal dialog allowing the user to inspect, verify, and accept an imported model response."""

    def __init__(
        self,
        definition: AgentAppDefinition,
        existing_revision: Optional[int] = None,
        initial_text: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.definition = definition
        self.existing_revision = existing_revision
        self.confirmed_text: Optional[str] = None
        self.confirmed_revision: bool = bool(existing_revision)

        self.setWindowTitle(f"Import Response — {definition.display_name}")
        self.setMinimumSize(720, 520)

        self._build_ui(initial_text)
        self._update_telemetry()

    def _build_ui(self, initial_text: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header with Accent
        header = QHBoxLayout()
        accent = QFrame()
        accent.setFixedWidth(5)
        accent.setFixedHeight(26)
        accent.setStyleSheet(f"background-color: {self.definition.accent_color}; border-radius: 2px;")
        header.addWidget(accent)

        title = QLabel(f"Verify and Import Response from {self.definition.display_name}")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #f8fafc;")
        header.addWidget(title)
        header.addStretch()

        if self.existing_revision:
            rev_badge = QLabel(f"Revision {self.existing_revision + 1}")
            rev_badge.setStyleSheet(
                "background-color: #3b2812; color: #fbbf24; border: 1px solid #78350f; "
                "border-radius: 10px; padding: 2px 8px; font-size: 11px; font-weight: 600;"
            )
            header.addWidget(rev_badge)

        layout.addLayout(header)

        # Instructions Banner
        instructions = QLabel(
            "Review the generated response copied from the application below. "
            "TRIAD calculates an integrity SHA-256 hash upon acceptance to verify content provenance."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #94a3b8; font-size: 12px;")
        layout.addWidget(instructions)

        # Text Editor
        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Paste the model's response here...")
        self.editor.setPlainText(initial_text)
        self.editor.textChanged.connect(self._update_telemetry)
        self.editor.setStyleSheet(
            "background-color: #0b0d12; border: 1px solid #232838; border-radius: 6px; "
            "color: #e2e8f0; font-family: 'Consolas', monospace; font-size: 12px; padding: 10px;"
        )
        layout.addWidget(self.editor, 1)

        # Telemetry & Status Bar
        self.telemetry_bar = QLabel("Characters: 0 | Words: 0 | SHA-256: -")
        self.telemetry_bar.setStyleSheet("font-size: 11px; color: #64748b; font-family: monospace;")
        layout.addWidget(self.telemetry_bar)

        # Warning / Status Banner
        self.status_banner = QLabel("")
        self.status_banner.setWordWrap(True)
        self.status_banner.setStyleSheet("font-size: 11px; color: #f87171;")
        layout.addWidget(self.status_banner)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setStyleSheet(
            "background-color: #1e222d; border: 1px solid #2d3345; border-radius: 5px; "
            "padding: 7px 18px; color: #cbd5e1; font-weight: 500;"
        )
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self.btn_accept = QPushButton("Accept Response")
        self.btn_accept.setStyleSheet(
            "background-color: #0f766e; border: 1px solid #14b8a6; border-radius: 5px; "
            "padding: 7px 22px; color: #ffffff; font-weight: 600;"
        )
        self.btn_accept.clicked.connect(self._on_accept)
        btn_layout.addWidget(self.btn_accept)

        layout.addLayout(btn_layout)

    def _update_telemetry(self) -> None:
        text = self.editor.toPlainText().strip()
        chars = len(text)
        words = len(text.split()) if chars > 0 else 0
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16] if chars > 0 else "-"

        self.telemetry_bar.setText(f"Characters: {chars:,} | Words: {words:,} | SHA-256: {sha}...")

        if chars == 0:
            self.status_banner.setText("Notice: Response box is currently empty.")
            self.btn_accept.setEnabled(False)
        elif self.existing_revision:
            self.status_banner.setText(
                f"Attention: An existing response was already accepted. "
                f"Confirming will store this as Revision {self.existing_revision + 1}."
            )
            self.status_banner.setStyleSheet("font-size: 11px; color: #fbbf24;")
            self.btn_accept.setEnabled(True)
        else:
            self.status_banner.setText("")
            self.btn_accept.setEnabled(True)

    def _on_accept(self) -> None:
        text = self.editor.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty Response", "Cannot accept an empty response.")
            return

        if self.existing_revision:
            reply = QMessageBox.question(
                self,
                "Confirm Revision",
                f"A response from {self.definition.display_name} has already been accepted.\n\n"
                f"Do you wish to save this updated text as Revision {self.existing_revision + 1}?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply != QMessageBox.Yes:
                return

        self.confirmed_text = text
        self.accept()

