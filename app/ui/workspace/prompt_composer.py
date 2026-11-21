from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models.session import ReasoningMode, ReasoningSession


class PromptComposer(QFrame):
    """Multiline question composer with title, mode configuration, rounds, and draft clearing."""

    create_session_requested = Signal(str, str, str, int)  # (title, question, mode, max_rounds)
    draft_cleared = Signal()
    new_draft_requested = Signal()

    MODE_LABELS = {
        ReasoningMode.QUICK_CONSENSUS.value: "Quick Consensus (1 Round + Vote)",
        ReasoningMode.DEEP_DEBATE.value: "Deep Debate (Multi-Round Critique)",
        ReasoningMode.RESEARCH_COUNCIL.value: "Research Council (Evidence Verification)",
        ReasoningMode.CODE_REVIEW.value: "Code Review Council (Syntax & Security)",
        ReasoningMode.CREATIVE_COUNCIL.value: "Creative Council (Ideation & Synthesis)",
    }

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("PromptComposer")
        self.setProperty("class", "surface-card")

        self.is_displaying_active_session = False
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        # 1. Header Banner & Title Row
        top_header_row = QHBoxLayout()
        self.section_title = QLabel("NEW REASONING SESSION")
        self.section_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #4285F4; letter-spacing: 0.8px;")
        top_header_row.addWidget(self.section_title)
        top_header_row.addStretch()

        self.btn_new_draft = QPushButton("+ New Draft")
        self.btn_new_draft.setStyleSheet(
            "QPushButton { background-color: #1D2633; border: 1px solid #2B3543; color: #94A3B8; "
            "padding: 3px 10px; font-size: 11px; border-radius: 4px; } "
            "QPushButton:hover { background-color: #243042; color: #EDF2F7; }"
        )
        self.btn_new_draft.setVisible(False)
        self.btn_new_draft.clicked.connect(self.start_new_draft)
        top_header_row.addWidget(self.btn_new_draft)
        layout.addLayout(top_header_row)

        # 2. Title & Mode Row
        config_row = QHBoxLayout()
        config_row.setSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Session Title (e.g. Distributed Consensus Engine Design)...")
        config_row.addWidget(self.title_input, 3)

        self.mode_select = QComboBox()
        for mode_key, label in self.MODE_LABELS.items():
            self.mode_select.addItem(label, mode_key)
        config_row.addWidget(self.mode_select, 2)

        rounds_box = QHBoxLayout()
        rounds_box.setSpacing(6)
        rounds_lbl = QLabel("Max Rounds:")
        rounds_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        self.rounds_spin = QSpinBox()
        self.rounds_spin.setRange(1, 10)
        self.rounds_spin.setValue(3)
        self.rounds_spin.setFixedWidth(55)
        rounds_box.addWidget(rounds_lbl)
        rounds_box.addWidget(self.rounds_spin)
        config_row.addLayout(rounds_box)

        layout.addLayout(config_row)

        # 3. Question Editor
        self.question_editor = QTextEdit()
        self.question_editor.setPlaceholderText("Ask your AI council a question (enter prompt, architecture query, or problem statement)...")
        self.question_editor.setMinimumHeight(80)
        self.question_editor.setMaximumHeight(160)
        self.question_editor.textChanged.connect(self._on_question_text_changed)
        layout.addWidget(self.question_editor)

        # 4. Validation Error Alert (hidden by default)
        self.validation_alert = QLabel("")
        self.validation_alert.setStyleSheet(
            "background-color: #3B1818; border: 1px solid #7F1D1D; border-radius: 4px; "
            "color: #F87171; padding: 6px 10px; font-size: 11px; font-weight: 600;"
        )
        self.validation_alert.setVisible(False)
        layout.addWidget(self.validation_alert)

        # 5. Bottom Action Bar: Character Count & Actions
        bottom_bar = QHBoxLayout()
        self.char_count_lbl = QLabel("0 characters")
        self.char_count_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        bottom_bar.addWidget(self.char_count_lbl)

        bottom_bar.addStretch()

        self.btn_clear = QPushButton("Clear Draft")
        self.btn_clear.clicked.connect(self.clear_draft)
        bottom_bar.addWidget(self.btn_clear)

        self.btn_create = QPushButton("Create Session")
        self.btn_create.setProperty("class", "btn-primary")
        self.btn_create.clicked.connect(self._handle_create_session)
        bottom_bar.addWidget(self.btn_create)

        layout.addLayout(bottom_bar)

    def _on_question_text_changed(self) -> None:
        length = len(self.question_editor.toPlainText())
        self.char_count_lbl.setText(f"{length:,} characters")
        if length > 0 and self.validation_alert.isVisible():
            self.validation_alert.setVisible(False)

    def _handle_create_session(self) -> None:
        title = self.title_input.text().strip()
        question = self.question_editor.toPlainText().strip()
        mode_key = self.mode_select.currentData()
        max_rounds = self.rounds_spin.value()

        if not question:
            self.validation_alert.setText("Validation error: Question cannot be empty. Please enter a problem statement.")
            self.validation_alert.setVisible(True)
            self.question_editor.setFocus()
            return

        self.validation_alert.setVisible(False)
        self.create_session_requested.emit(title, question, mode_key, max_rounds)

    def clear_draft(self) -> None:
        """Clears inputs for a new draft."""
        self.title_input.clear()
        self.question_editor.clear()
        self.validation_alert.setVisible(False)
        self.draft_cleared.emit()

    def start_new_draft(self) -> None:
        """Resets the composer to draft mode."""
        self.is_displaying_active_session = False
        self.section_title.setText("NEW REASONING SESSION")
        self.section_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #4285F4; letter-spacing: 0.8px;")
        self.btn_new_draft.setVisible(False)
        self.btn_create.setEnabled(True)
        self.title_input.setReadOnly(False)
        self.question_editor.setReadOnly(False)
        self.clear_draft()
        self.new_draft_requested.emit()

    def set_active_session(self, session: ReasoningSession) -> None:
        """Populates the composer with an active session's data in workspace view."""
        self.is_displaying_active_session = True
        self.section_title.setText(f"ACTIVE SESSION: {session.session_id}")
        self.section_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #22C55E; letter-spacing: 0.8px;")
        self.btn_new_draft.setVisible(True)

        self.title_input.setText(session.title)
        self.question_editor.setPlainText(session.initial_question)

        # Select mode in combo
        idx = self.mode_select.findData(session.mode.value)
        if idx >= 0:
            self.mode_select.setCurrentIndex(idx)

        self.rounds_spin.setValue(session.max_rounds)
        self.validation_alert.setVisible(False)

    def set_reasoning_mode(self, mode_value: str) -> None:
        """Updates the selected reasoning mode dropdown."""
        idx = self.mode_select.findData(mode_value)
        if idx >= 0:
            self.mode_select.setCurrentIndex(idx)
