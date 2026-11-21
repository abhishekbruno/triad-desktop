from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class DisagreementPage(QWidget):
    """Navigable Disagreement Map and Claim Conflict Matrix view with informative empty state."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # 1. Header Row
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("DISAGREEMENT MAP & CLAIM MATRIX")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #EDF2F7; letter-spacing: 0.5px;")
        sub_lbl = QLabel("Phase 3: Cross-Model Deliberation, Contradiction Tracking & Epistemic Conflict Analysis")
        sub_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_row.addLayout(title_box)

        header_row.addStretch()

        badge = QLabel("Phase 3 — Planned")
        badge.setStyleSheet(
            "background-color: #2D1F4F; border: 1px solid #7E22CE; border-radius: 10px; "
            "padding: 4px 10px; font-size: 10px; font-weight: 600; color: #C084FC;"
        )
        header_row.addWidget(badge)
        layout.addLayout(header_row)

        # 2. Informative Empty State Banner
        empty_frame = QFrame()
        empty_frame.setProperty("class", "surface-card")
        empty_layout = QVBoxLayout(empty_frame)
        empty_layout.setContentsMargins(18, 16, 18, 16)
        empty_layout.setSpacing(8)

        empty_heading = QLabel("No Disagreement Data Available For Current Session")
        empty_heading.setStyleSheet("font-size: 13px; font-weight: 700; color: #EDF2F7;")
        empty_layout.addWidget(empty_heading)

        empty_desc = QLabel(
            "Disagreement mapping will be generated automatically once cross-model debate is conducted.\n"
            "The system compares each participant's position on atomic claims, identifies shared conclusions, "
            "displays contradictory arguments, and tracks position shifts across rounds without paid APIs."
        )
        empty_desc.setWordWrap(True)
        empty_desc.setStyleSheet("font-size: 12px; color: #94A3B8; line-height: 1.5;")
        empty_layout.addWidget(empty_desc)

        layout.addWidget(empty_frame)

        # 3. Planned Architecture Preview Table (Read-Only Preview)
        prev_title = QLabel("PLANNED CLAIM-BY-CLAIM CONFLICT MATRIX:")
        prev_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 0.8px;")
        layout.addWidget(prev_title)

        preview_table = QTableWidget(3, 5)
        preview_table.setHorizontalHeaderLabels([
            "Claim Statement", "ChatGPT Position", "Claude Position", "Gemini Position", "Conflict Status"
        ])
        preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        preview_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        preview_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

        sample_rows = [
            ("Consistency vs Latency Tradeoff", "Event-driven eventual", "Sync transactional", "Hybrid partitioned", "ACTIVE DEBATE"),
            ("Fault Tolerance in Partition", "Outbox pattern", "2-Phase commit", "Saga orchestration", "EVIDENTIARY SPLIT"),
            ("Operational Complexity", "Requires Kafka/Queue infra", "Lower initial overhead", "Requires state store", "CONSENSUS CANDIDATE"),
        ]

        for row, (claim, p1, p2, p3, status) in enumerate(sample_rows):
            for col, val in enumerate([claim, p1, p2, p3, status]):
                item = QTableWidgetItem(f"[Preview] {val}")
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                preview_table.setItem(row, col, item)

        preview_table.setEnabled(False)
        layout.addWidget(preview_table)

        # 4. Explanatory Architecture Footer
        footer_frame = QFrame()
        footer_frame.setStyleSheet("background-color: #111720; border: 1px solid #1D2633; border-radius: 6px; padding: 10px;")
        foot_layout = QVBoxLayout(footer_frame)
        foot_layout.setContentsMargins(10, 8, 10, 8)
        foot_lbl = QLabel(
            "Note: The Disagreement Map is mathematically linked to the Reasoning Memory store. "
            "In Phase 3, atomic claims extracted during critiques will be dynamically populated here."
        )
        foot_lbl.setWordWrap(True)
        foot_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        foot_layout.addWidget(foot_lbl)

        layout.addWidget(footer_frame)
        layout.addStretch()
