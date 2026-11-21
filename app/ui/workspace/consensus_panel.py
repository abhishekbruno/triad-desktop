from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ConsensusPanel(QFrame):
    """Permanent space for the future consensus and voting engine.

    Displays:
    - Future-feature banner: 'Consensus becomes available after discussion and voting are implemented.'
    - Visual layout of planned decision engine (Unanimous 3/3, Majority 2/3, Minority Report, Confidence)
    - All voting actions disabled with clear tooltips.
    - Zero simulated votes presented as real.
    """

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("ConsensusPanel")
        self.setProperty("class", "surface-card")

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(10)

        # 1. Header with Feature Badge
        header_row = QHBoxLayout()
        title_lbl = QLabel("CONSENSUS & DECISION ENGINE")
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 700; color: #22C55E; letter-spacing: 0.8px;")
        header_row.addWidget(title_lbl)

        header_row.addStretch()

        badge = QLabel("Phase 4 — Planned")
        badge.setStyleSheet(
            "background-color: #133324; border: 1px solid #15803D; border-radius: 10px; "
            "padding: 2px 8px; font-size: 10px; font-weight: 600; color: #4ADE80;"
        )
        header_row.addWidget(badge)
        layout.addLayout(header_row)

        # 2. Informative Empty State Banner
        empty_banner = QFrame()
        empty_banner.setStyleSheet(
            "background-color: #111720; border: 1px solid #1D2633; border-radius: 6px; padding: 10px;"
        )
        banner_layout = QVBoxLayout(empty_banner)
        banner_layout.setContentsMargins(10, 8, 10, 8)
        banner_layout.setSpacing(4)

        status_text = QLabel("Consensus becomes available after discussion and voting are implemented.")
        status_text.setWordWrap(True)
        status_text.setStyleSheet("font-size: 11px; font-weight: 600; color: #EDF2F7;")
        banner_layout.addWidget(status_text)

        sub_text = QLabel(
            "When debate concludes, models will cast structured ballots. "
            "TRIAD calculates mathematical consensus (3/3 unanimous or 2/3 majority) without paid APIs."
        )
        sub_text.setWordWrap(True)
        sub_text.setStyleSheet("font-size: 10px; color: #94A3B8;")
        banner_layout.addWidget(sub_text)

        layout.addWidget(empty_banner)

        # 3. Planned Architecture Preview Cards (Disabled / Visual Preview)
        preview_box = QFrame()
        preview_box.setStyleSheet("background-color: #0B0F14; border: 1px dashed #2B3543; border-radius: 6px; padding: 10px;")
        prev_layout = QVBoxLayout(preview_box)
        prev_layout.setContentsMargins(8, 6, 8, 6)
        prev_layout.setSpacing(6)

        prev_title = QLabel("PLANNED CONSENSUS METRICS:")
        prev_title.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.5px;")
        prev_layout.addWidget(prev_title)

        # Metrics rows
        row1 = QHBoxLayout()
        row1.addWidget(self._create_metric_pill("Unanimous Verdict", "3/3 Agreement"))
        row1.addWidget(self._create_metric_pill("Majority Consensus", "2/3 Agreement"))
        prev_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(self._create_metric_pill("Minority Report", "Dissent Tracking"))
        row2.addWidget(self._create_metric_pill("Human Override", "Audit Preserved"))
        prev_layout.addLayout(row2)

        layout.addWidget(preview_box)

        # 4. Action Row (Disabled buttons demonstrating future triggers)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.btn_cast_ballots = QPushButton("Cast Ballots (Phase 4)")
        self.btn_cast_ballots.setEnabled(False)
        self.btn_cast_ballots.setToolTip("Voting engine will be enabled in Phase 4")
        self.btn_cast_ballots.setStyleSheet(
            "QPushButton:disabled { background-color: #111720; color: #64748B; border: 1px solid #1D2633; }"
        )
        btn_row.addWidget(self.btn_cast_ballots, 1)

        self.btn_view_report = QPushButton("Export Decision")
        self.btn_view_report.setEnabled(False)
        self.btn_view_report.setToolTip("Consensus export will be enabled in Phase 4")
        self.btn_view_report.setStyleSheet(
            "QPushButton:disabled { background-color: #111720; color: #64748B; border: 1px solid #1D2633; }"
        )
        btn_row.addWidget(self.btn_view_report, 1)

        layout.addLayout(btn_row)
        layout.addStretch()

    def _create_metric_pill(self, title: str, subtitle: str) -> QWidget:
        pill = QFrame()
        pill.setStyleSheet("background-color: #161D27; border: 1px solid #2B3543; border-radius: 4px; padding: 4px;")
        l = QVBoxLayout(pill)
        l.setContentsMargins(6, 4, 6, 4)
        l.setSpacing(2)

        t = QLabel(title)
        t.setStyleSheet("font-size: 10px; font-weight: 600; color: #94A3B8;")
        s = QLabel(subtitle)
        s.setStyleSheet("font-size: 9px; color: #64748B;")
        l.addWidget(t)
        l.addWidget(s)
        return pill
