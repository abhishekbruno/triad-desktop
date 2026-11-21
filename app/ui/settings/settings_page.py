from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.models.session import ReasoningMode
from app.storage.database import DatabaseManager


class SettingsPage(QWidget):
    """View allowing configuration of workspace parameters, polling interval, and storage paths."""

    settings_saved = Signal()

    def __init__(self, database: DatabaseManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.db = database
        self._build_ui()
        self._load_saved_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(16)

        # Header
        title_box = QVBoxLayout()
        title_lbl = QLabel("WORKSPACE SETTINGS")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #EDF2F7; letter-spacing: 0.5px;")
        sub_lbl = QLabel("Configure local workspace preferences, discovery intervals, and system defaults.")
        sub_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        layout.addLayout(title_box)

        # Section 1: Connection Monitor
        mon_frame = QFrame()
        mon_frame.setProperty("class", "surface-card")
        mon_layout = QVBoxLayout(mon_frame)
        mon_layout.setContentsMargins(16, 14, 16, 14)
        mon_layout.setSpacing(10)

        mon_title = QLabel("CONNECTION MONITORING")
        mon_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #4285F4; letter-spacing: 0.8px;")
        mon_layout.addWidget(mon_title)

        poll_row = QHBoxLayout()
        poll_lbl = QLabel("Background Polling Interval (seconds):")
        poll_lbl.setStyleSheet("color: #EDF2F7;")
        self.poll_spin = QDoubleSpinBox()
        self.poll_spin.setRange(0.5, 30.0)
        self.poll_spin.setSingleStep(0.5)
        self.poll_spin.setValue(2.0)
        self.poll_spin.setFixedWidth(80)
        poll_row.addWidget(poll_lbl)
        poll_row.addStretch()
        poll_row.addWidget(self.poll_spin)
        mon_layout.addLayout(poll_row)

        layout.addWidget(mon_frame)

        # Section 2: Reasoning Defaults
        cfg_frame = QFrame()
        cfg_frame.setProperty("class", "surface-card")
        cfg_layout = QVBoxLayout(cfg_frame)
        cfg_layout.setContentsMargins(16, 14, 16, 14)
        cfg_layout.setSpacing(10)

        cfg_title = QLabel("DEFAULT REASONING CONFIGURATION")
        cfg_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #4285F4; letter-spacing: 0.8px;")
        cfg_layout.addWidget(cfg_title)

        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Default Reasoning Mode:")
        self.mode_select = QComboBox()
        self.mode_select.addItem("Quick Consensus (1 Round + Vote)", "quick_consensus")
        self.mode_select.addItem("Deep Debate (Multi-Round Critique)", "deep_debate")
        self.mode_select.addItem("Research Council (Evidence Verification)", "research_council")
        self.mode_select.addItem("Code Review Council (Syntax & Security)", "code_review")
        self.mode_select.addItem("Creative Council (Ideation & Synthesis)", "creative_council")
        mode_row.addWidget(mode_lbl)
        mode_row.addStretch()
        mode_row.addWidget(self.mode_select)
        cfg_layout.addLayout(mode_row)

        rounds_row = QHBoxLayout()
        rounds_lbl = QLabel("Default Maximum Rounds:")
        self.rounds_spin = QSpinBox()
        self.rounds_spin.setRange(1, 10)
        self.rounds_spin.setValue(3)
        self.rounds_spin.setFixedWidth(80)
        rounds_row.addWidget(rounds_lbl)
        rounds_row.addStretch()
        rounds_row.addWidget(self.rounds_spin)
        cfg_layout.addLayout(rounds_row)

        layout.addWidget(cfg_frame)

        # Section 3: Storage & Local Database
        store_frame = QFrame()
        store_frame.setProperty("class", "surface-card")
        store_layout = QVBoxLayout(store_frame)
        store_layout.setContentsMargins(16, 14, 16, 14)
        store_layout.setSpacing(10)

        store_title = QLabel("PERSISTENT STORAGE (SQLITE)")
        store_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #4285F4; letter-spacing: 0.8px;")
        store_layout.addWidget(store_title)

        db_row = QHBoxLayout()
        db_lbl = QLabel("Database Path:")
        self.db_path_input = QLineEdit(self.db.db_path)
        self.db_path_input.setReadOnly(True)
        db_row.addWidget(db_lbl)
        db_row.addWidget(self.db_path_input, 1)
        store_layout.addLayout(db_row)

        layout.addWidget(store_frame)

        # Save Button & Status Feedback
        action_row = QHBoxLayout()
        self.btn_save = QPushButton("Save Settings")
        self.btn_save.setProperty("class", "btn-primary")
        self.btn_save.clicked.connect(self._save_settings)
        action_row.addWidget(self.btn_save)

        self.feedback_lbl = QLabel("")
        self.feedback_lbl.setStyleSheet("color: #34D399; font-weight: 600; font-size: 11px;")
        action_row.addWidget(self.feedback_lbl)
        action_row.addStretch()
        layout.addLayout(action_row)

        layout.addStretch()

    def _load_saved_settings(self) -> None:
        poll_val = self.db.get_setting("poll_interval", default="2.0")
        try:
            self.poll_spin.setValue(float(poll_val))
        except (ValueError, TypeError):
            self.poll_spin.setValue(2.0)

        default_mode = self.db.get_setting("default_mode", default="quick_consensus")
        idx = self.mode_select.findData(default_mode)
        if idx >= 0:
            self.mode_select.setCurrentIndex(idx)

        default_rounds = self.db.get_setting("default_max_rounds", default="3")
        try:
            self.rounds_spin.setValue(int(default_rounds))
        except (ValueError, TypeError):
            self.rounds_spin.setValue(3)

    def _save_settings(self) -> None:
        self.db.set_setting("poll_interval", str(self.poll_spin.value()))
        self.db.set_setting("default_mode", self.mode_select.currentData())
        self.db.set_setting("default_max_rounds", str(self.rounds_spin.value()))

        self.feedback_lbl.setText("Settings saved successfully.")
        self.settings_saved.emit()
