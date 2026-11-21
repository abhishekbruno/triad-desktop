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
            "When debate concludes, models cast structured ballots. "
            "TRIAD calculates mathematical consensus (3/3 unanimous or 2/3 majority) locally without paid APIs."
        )
        sub_text.setWordWrap(True)
        sub_text.setStyleSheet("font-size: 10px; color: #94A3B8;")
        banner_layout.addWidget(sub_text)

        layout.addWidget(empty_banner)

        # 3. Three Dedicated Future Consensus Module Cards
        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(8)

        # Card 1: Voting Panel Placeholder
        card_voting = self._create_module_card(
            title="1. Voting & Verdict Panel",
            phase_tag="Phase 4",
            description="Aggregates individual model ballots into mathematical consensus. Calculates unanimous (3/3) or majority (2/3) verdicts deterministically.",
        )
        self.btn_cast_ballots = QPushButton("Cast Ballots (Phase 4)")
        self.btn_cast_ballots.setEnabled(False)
        self.btn_cast_ballots.setToolTip("Voting engine will be enabled in Phase 4")
        self.btn_cast_ballots.setStyleSheet(
            "QPushButton:disabled { background-color: #111720; color: #64748B; border: 1px solid #1D2633; font-size: 10px; padding: 4px 8px; }"
        )
        card_voting.layout().addWidget(self.btn_cast_ballots)
        cards_layout.addWidget(card_voting)

        # Card 2: Disagreement Map Placeholder
        card_disagreement = self._create_module_card(
            title="2. Disagreement Map",
            phase_tag="Phase 3/4",
            description="Semantic conflict matrix tracing points of departure, contradictory claims, and convergence progression across rounds.",
        )
        self.btn_view_disagreement = QPushButton("Explore Conflict Map (Phase 3)")
        self.btn_view_disagreement.setEnabled(False)
        self.btn_view_disagreement.setToolTip("Disagreement matrix generation will be enabled in Phase 3")
        self.btn_view_disagreement.setStyleSheet(
            "QPushButton:disabled { background-color: #111720; color: #64748B; border: 1px solid #1D2633; font-size: 10px; padding: 4px 8px; }"
        )
        card_disagreement.layout().addWidget(self.btn_view_disagreement)
        cards_layout.addWidget(card_disagreement)

        # Card 3: Minority Report Placeholder
        card_minority = self._create_module_card(
            title="3. Minority Report & Dissent",
            phase_tag="Phase 4",
            description="Captures dissenting model arguments, identifying hidden risks and nuances when a 2/3 majority split occurs.",
        )
        self.btn_view_report = QPushButton("Generate Minority Report (Phase 4)")
        self.btn_view_report.setEnabled(False)
        self.btn_view_report.setToolTip("Minority report generation will be enabled in Phase 4")
        self.btn_view_report.setStyleSheet(
            "QPushButton:disabled { background-color: #111720; color: #64748B; border: 1px solid #1D2633; font-size: 10px; padding: 4px 8px; }"
        )
        card_minority.layout().addWidget(self.btn_view_report)
        cards_layout.addWidget(card_minority)

        layout.addLayout(cards_layout)
        layout.addStretch()

    def _create_module_card(self, title: str, phase_tag: str, description: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("background-color: #0B0F14; border: 1px dashed #2B3543; border-radius: 6px; padding: 8px;")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(8, 6, 8, 6)
        c_layout.setSpacing(4)

        header = QHBoxLayout()
        t = QLabel(title)
        t.setStyleSheet("font-size: 10px; font-weight: 700; color: #EDF2F7; letter-spacing: 0.4px;")
        header.addWidget(t)
        header.addStretch()

        tag = QLabel(phase_tag)
        tag.setStyleSheet("font-size: 9px; font-weight: 600; color: #F59E0B; background: #2D2211; border: 1px solid #78350F; border-radius: 4px; padding: 1px 5px;")
        header.addWidget(tag)
        c_layout.addLayout(header)

        d = QLabel(description)
        d.setWordWrap(True)
        d.setStyleSheet("font-size: 9px; color: #94A3B8; line-height: 1.3;")
        c_layout.addWidget(d)

        return card
