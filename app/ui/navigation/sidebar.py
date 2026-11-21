from typing import Dict, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from app.models.session import ReasoningMode


class SidebarButton(QPushButton):
    """Button styled for sidebar navigation with support for icon-only collapsed state."""

    def __init__(self, key: str, text: str, short_code: str, tooltip: str, parent: Optional[QWidget] = None):
        super().__init__(text, parent)
        self.key = key
        self.full_text = text
        self.short_code = short_code
        self.tooltip_text = tooltip
        self.setCheckable(True)
        self.setProperty("class", "sidebar-btn")
        self.setToolTip(tooltip)
        self.setCursor(Qt.PointingHandCursor)

    def set_collapsed(self, collapsed: bool) -> None:
        if collapsed:
            self.setText(self.short_code)
            self.setToolTip(f"{self.full_text} — {self.tooltip_text}")
        else:
            self.setText(self.full_text)
            self.setToolTip(self.tooltip_text)


class Sidebar(QFrame):
    """Persistent collapsible left sidebar navigation."""

    page_selected = Signal(str)       # ('workspace', 'sessions', 'connections', 'disagreement', 'settings')
    mode_selected = Signal(str)       # ('quick_consensus', 'deep_debate', 'research_council', 'code_review', 'creative_council')
    new_session_requested = Signal()
    search_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("SidebarFrame")
        self.is_collapsed = False
        self.buttons: Dict[str, SidebarButton] = {}
        self.mode_buttons: Dict[str, SidebarButton] = {}

        self.setFixedWidth(230)
        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 12, 8, 12)
        main_layout.setSpacing(6)

        # 1. Top Header / Brand & Collapse Toggle
        top_box = QHBoxLayout()
        top_box.setContentsMargins(6, 4, 6, 8)

        self.brand_label = QLabel("TRIAD")
        self.brand_label.setStyleSheet("font-size: 15px; font-weight: 800; color: #4285F4; letter-spacing: 1px;")
        top_box.addWidget(self.brand_label)
        top_box.addStretch()

        self.btn_toggle_collapse = QPushButton("«")
        self.btn_toggle_collapse.setFixedSize(26, 26)
        self.btn_toggle_collapse.setToolTip("Collapse / Expand Sidebar")
        self.btn_toggle_collapse.setStyleSheet(
            "QPushButton { background: #161D27; border: 1px solid #2B3543; border-radius: 4px; "
            "color: #94A3B8; font-weight: bold; font-size: 12px; } "
            "QPushButton:hover { background: #1D2633; color: #EDF2F7; }"
        )
        self.btn_toggle_collapse.clicked.connect(self.toggle_collapse)
        top_box.addWidget(self.btn_toggle_collapse)
        main_layout.addLayout(top_box)

        # Scrollable area for navigation items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(4)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        # SECTION: WORKSPACE
        self.lbl_workspace = self._add_section_label(container_layout, "WORKSPACE")
        btn_new = self._create_btn("workspace_new", "New Discussion", "ND", "Start a new reasoning session")
        btn_new.clicked.connect(lambda: (self.new_session_requested.emit(), self.page_selected.emit("workspace")))
        btn_new.setChecked(True)
        self._add_btn(container_layout, btn_new)

        btn_all_sess = self._create_btn("all_sessions", "All Sessions", "AS", "View and manage stored sessions")
        btn_all_sess.clicked.connect(lambda: self.page_selected.emit("sessions"))
        self._add_btn(container_layout, btn_all_sess)

        # SECTION: REASONING MODES
        self.lbl_reasoning = self._add_section_label(container_layout, "REASONING MODES")
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        modes = [
            ("quick_consensus", "Quick Consensus", "QC", "1 independent round + deterministic vote"),
            ("deep_debate", "Deep Debate", "DD", "Multi-round cross-critique & rebuttal"),
            ("research_council", "Research Council", "RC", "Evidence & claim verification"),
            ("code_review", "Code Review Council", "CR", "Architecture, security & syntax analysis"),
            ("creative_council", "Creative Council", "CC", "Divergent ideation & convergent ranking"),
        ]

        for mode_key, mode_name, short_code, tip in modes:
            m_btn = SidebarButton(mode_key, mode_name, short_code, tip, self)
            m_btn.setStyleSheet(
                "QPushButton { text-align: left; padding: 6px 12px; font-size: 11px; color: #94A3B8; "
                "border: none; border-radius: 4px; background: transparent; } "
                "QPushButton:hover { background-color: #161D27; color: #EDF2F7; } "
                "QPushButton:checked { background-color: #1D2633; color: #4285F4; font-weight: 600; "
                "border-left: 2px solid #4285F4; }"
            )
            m_btn.clicked.connect(lambda checked, k=mode_key: self.mode_selected.emit(k))
            if mode_key == "quick_consensus":
                m_btn.setChecked(True)
            self.mode_group.addButton(m_btn)
            self.mode_buttons[mode_key] = m_btn
            container_layout.addWidget(m_btn)

        # SECTION: HISTORY
        self.lbl_history = self._add_section_label(container_layout, "HISTORY")
        btn_recent = self._create_btn("history_recent", "Recent Sessions", "RS", "Browse recent discussion history")
        btn_recent.clicked.connect(lambda: self.page_selected.emit("sessions"))
        self._add_btn(container_layout, btn_recent)

        btn_search = self._create_btn("history_search", "Search Sessions", "SS", "Search sessions by title or question")
        btn_search.clicked.connect(lambda: (self.page_selected.emit("sessions"), self.search_requested.emit()))
        self._add_btn(container_layout, btn_search)

        # SECTION: SYSTEM
        self.lbl_system = self._add_section_label(container_layout, "SYSTEM")
        btn_connections = self._create_btn("sys_connections", "Agent Connections", "AC", "Manage desktop AI applications")
        btn_connections.clicked.connect(lambda: self.page_selected.emit("connections"))
        self._add_btn(container_layout, btn_connections)

        btn_disagreement = self._create_btn("sys_disagreement", "Disagreement Map", "DM", "View position matrix and claim conflicts")
        btn_disagreement.clicked.connect(lambda: self.page_selected.emit("disagreement"))
        self._add_btn(container_layout, btn_disagreement)

        btn_settings = self._create_btn("sys_settings", "Settings", "ST", "Configure workspace parameters")
        btn_settings.clicked.connect(lambda: self.page_selected.emit("settings"))
        self._add_btn(container_layout, btn_settings)

        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, 1)

    def _add_section_label(self, layout: QVBoxLayout, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("SidebarSectionLabel")
        lbl.setProperty("section_header", True)
        layout.addWidget(lbl)
        return lbl

    def _create_btn(self, key: str, text: str, short_code: str, tooltip: str) -> SidebarButton:
        btn = SidebarButton(key, text, short_code, tooltip, self)
        self.nav_group.addButton(btn)
        self.buttons[key] = btn
        return btn

    def _add_btn(self, layout: QVBoxLayout, btn: SidebarButton) -> None:
        layout.addWidget(btn)

    def toggle_collapse(self) -> None:
        """Toggles between expanded sidebar (230px) and collapsed icons sidebar (64px)."""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.setFixedWidth(64)
            self.btn_toggle_collapse.setText("»")
            self.brand_label.setText("T")
            self.lbl_workspace.setVisible(False)
            self.lbl_reasoning.setVisible(False)
            self.lbl_history.setVisible(False)
            self.lbl_system.setVisible(False)
        else:
            self.setFixedWidth(230)
            self.btn_toggle_collapse.setText("«")
            self.brand_label.setText("TRIAD")
            self.lbl_workspace.setVisible(True)
            self.lbl_reasoning.setVisible(True)
            self.lbl_history.setVisible(True)
            self.lbl_system.setVisible(True)

        for btn in self.buttons.values():
            btn.set_collapsed(self.is_collapsed)
        for btn in self.mode_buttons.values():
            btn.set_collapsed(self.is_collapsed)

    def select_page_button(self, page_name: str) -> None:
        """Selects the corresponding sidebar button when navigated programmatically."""
        mapping = {
            "workspace": "workspace_new",
            "sessions": "all_sessions",
            "connections": "sys_connections",
            "disagreement": "sys_disagreement",
            "settings": "sys_settings",
        }
        key = mapping.get(page_name)
        if key and key in self.buttons:
            self.buttons[key].setChecked(True)

    def select_mode_button(self, mode_value: str) -> None:
        """Selects the corresponding mode button in the sidebar."""
        if mode_value in self.mode_buttons:
            self.mode_buttons[mode_value].setChecked(True)
