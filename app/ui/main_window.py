import os
from pathlib import Path
from typing import Dict, Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.connection_monitor import ConnectionMonitor
from app.core.message_bridge import MessageExchangeBridge
from app.core.session_manager import SessionManager
from app.core.window_manager import WindowManager
from app.models.agent import AgentConnection, AgentStatus, SUPPORTED_AGENTS
from app.models.session import ReasoningMode, ReasoningSession
from app.storage.database import DatabaseManager
from app.storage.session_repository import SessionRepository
from app.ui.connections.connections_page import ConnectionsPage
from app.ui.disagreement.disagreement_page import DisagreementPage
from app.ui.navigation.sidebar import Sidebar
from app.ui.sessions.session_list import SessionListPage
from app.ui.settings.settings_page import SettingsPage
from app.ui.workspace.workspace_page import WorkspacePage
from app.utils.logging import get_logger

logger = get_logger("ui.main_window")


class MainWindow(QMainWindow):
    """Main desktop workspace window for TRIAD — Phase 2A Unified Desktop Workspace."""

    def __init__(
        self,
        registry: AgentRegistry,
        discovery_service: AppDiscoveryService,
        window_manager: WindowManager,
        database: Optional[DatabaseManager] = None,
        message_bridge: Optional[MessageExchangeBridge] = None,
        session_manager: Optional[SessionManager] = None,
        start_monitor: bool = True,
    ):
        super().__init__()
        self.registry = registry
        self.discovery = discovery_service
        self.window_mgr = window_manager
        self.db = database or DatabaseManager()
        self.session_repo = SessionRepository(db=self.db)
        self.session_mgr = session_manager or SessionManager(repository=self.session_repo)
        self.bridge = message_bridge or MessageExchangeBridge(
            registry=self.registry,
            window_manager=self.window_mgr,
            database=self.db,
        )
        self.monitor: Optional[ConnectionMonitor] = None

        self.setWindowTitle("TRIAD — Local AI Consensus Workspace")
        self.setMinimumSize(1040, 720)
        self.resize(1280, 800)

        self._load_stylesheet()
        self._build_ui()
        self._wire_signals()
        if start_monitor:
            self._setup_monitor()

        # Initial scan and summary update
        QTimer.singleShot(150, self.scan_applications)

    def _load_stylesheet(self) -> None:
        """Loads the primary design token stylesheet."""
        theme_path = Path(__file__).parent / "styles" / "theme.qss"
        if not theme_path.exists():
            theme_path = Path(__file__).parent / "styles.qss"

        if theme_path.exists():
            with open(theme_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _build_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Top Header Bar
        header = QWidget()
        header.setObjectName("HeaderWidget")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 12, 20, 12)
        header_layout.setSpacing(12)

        # Brand Title & Session Info
        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        app_title = QLabel("TRIAD — Local AI Consensus Workspace")
        app_title.setObjectName("AppTitleLabel")

        self.header_session_lbl = QLabel("No active session — Compose a new question to begin")
        self.header_session_lbl.setObjectName("AppSubtitleLabel")

        title_box.addWidget(app_title)
        title_box.addWidget(self.header_session_lbl)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        # Mode Badge
        self.header_mode_badge = QLabel("MODE: QUICK CONSENSUS")
        self.header_mode_badge.setObjectName("HeaderModeBadge")
        header_layout.addWidget(self.header_mode_badge)

        # Connection Summary Badge
        self.status_summary_badge = QLabel("0/3 Applications Bound")
        self.status_summary_badge.setObjectName("StatusSummaryBadge")
        header_layout.addWidget(self.status_summary_badge)

        # Settings Quick Button
        btn_quick_settings = QPushButton("⚙")
        btn_quick_settings.setFixedSize(28, 28)
        btn_quick_settings.setToolTip("Workspace Settings")
        btn_quick_settings.setStyleSheet(
            "QPushButton { background: #161D27; border: 1px solid #2B3543; border-radius: 4px; "
            "color: #94A3B8; font-size: 13px; font-weight: bold; } "
            "QPushButton:hover { background: #1D2633; color: #EDF2F7; }"
        )
        btn_quick_settings.clicked.connect(lambda: self.navigate_to("settings"))
        header_layout.addWidget(btn_quick_settings)

        root_layout.addWidget(header)

        # 2. Body: Left Sidebar + Stacked Content Pages
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Navigation Sidebar
        self.sidebar = Sidebar(body_widget)
        body_layout.addWidget(self.sidebar)

        # Stacked Pages
        self.stack = QStackedWidget(body_widget)

        # Page 0: Workspace (Unified Central Canvas)
        self.workspace_page = WorkspacePage(
            registry=self.registry,
            window_manager=self.window_mgr,
            session_manager=self.session_mgr,
            parent=self.stack,
        )
        self.stack.addWidget(self.workspace_page)

        # Page 1: Sessions List
        self.sessions_page = SessionListPage(
            session_manager=self.session_mgr,
            parent=self.stack,
        )
        self.stack.addWidget(self.sessions_page)

        # Page 2: Connections Dashboard
        self.connections_page = ConnectionsPage(
            registry=self.registry,
            discovery_service=self.discovery,
            window_manager=self.window_mgr,
            parent=self.stack,
        )
        self.stack.addWidget(self.connections_page)

        # Page 3: Disagreement Map
        self.disagreement_page = DisagreementPage(parent=self.stack)
        self.stack.addWidget(self.disagreement_page)

        # Page 4: Settings
        self.settings_page = SettingsPage(database=self.db, parent=self.stack)
        self.stack.addWidget(self.settings_page)

        body_layout.addWidget(self.stack, 1)
        root_layout.addWidget(body_widget, 1)

        # 3. Bottom Status Bar
        status_bar = QWidget()
        status_bar.setObjectName("StatusBarWidget")
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(18, 4, 18, 4)

        self.status_left_lbl = QLabel("Local Workspace • Zero Paid APIs • Win32 Window Management")
        self.status_left_lbl.setObjectName("StatusBarLabel")
        status_layout.addWidget(self.status_left_lbl)

        status_layout.addStretch()

        self.status_right_lbl = QLabel("0/3 Apps Bound")
        self.status_right_lbl.setObjectName("StatusBarLabel")
        status_layout.addWidget(self.status_right_lbl)

        root_layout.addWidget(status_bar)

    def _wire_signals(self) -> None:
        # Sidebar navigation
        self.sidebar.page_selected.connect(self.navigate_to)
        self.sidebar.mode_selected.connect(self.set_reasoning_mode)
        self.sidebar.new_session_requested.connect(self._on_new_session_requested)
        self.sidebar.search_requested.connect(self._on_search_requested)

        # Sessions page interactions
        self.sessions_page.session_opened.connect(self._on_session_opened_from_list)
        self.sessions_page.new_session_requested.connect(self._on_new_session_requested)

        # Connections page interactions
        self.connections_page.connections_updated.connect(self._on_connections_updated)

        # Workspace page interactions
        self.workspace_page.session_created.connect(self._on_session_created)

        # SessionManager lifecycle notifications
        self.session_mgr.session_created.connect(self._update_session_header)
        self.session_mgr.session_loaded.connect(self._update_session_header)
        self.session_mgr.session_updated.connect(self._update_session_header)
        self.session_mgr.session_deleted.connect(self._on_session_deleted)
        self.session_mgr.mode_changed.connect(self._on_mode_changed_externally)

        # Registry live changes
        self.registry.subscribe(self._on_registry_changed)

    def _setup_monitor(self) -> None:
        """Starts background ConnectionMonitor with safe periodic evaluation."""
        self.monitor = ConnectionMonitor(
            registry=self.registry,
            discovery_service=self.discovery,
            window_manager=self.window_mgr,
            database_manager=self.db,
            poll_interval_sec=2.0,
        )
        self.monitor.start()

    def navigate_to(self, page_name: str) -> None:
        """Switches the active view in QStackedWidget."""
        pages = {
            "workspace": 0,
            "sessions": 1,
            "connections": 2,
            "disagreement": 3,
            "settings": 4,
        }
        idx = pages.get(page_name, 0)
        self.stack.setCurrentIndex(idx)
        self.sidebar.select_page_button(page_name)

        if page_name == "sessions":
            self.sessions_page.refresh_sessions()
        elif page_name == "workspace":
            self.workspace_page.sync_agent_panels()

    def set_reasoning_mode(self, mode_key: str) -> None:
        """Sets reasoning mode from sidebar or composer."""
        self.workspace_page.set_reasoning_mode(mode_key)
        self.header_mode_badge.setText(f"MODE: {mode_key.replace('_', ' ').upper()}")
        self.sidebar.select_mode_button(mode_key)

    def _on_new_session_requested(self) -> None:
        self.navigate_to("workspace")
        self.workspace_page.start_new_discussion()
        self.header_session_lbl.setText("New Reasoning Session — Compose a question to begin")

    def _on_search_requested(self) -> None:
        self.navigate_to("sessions")
        self.sessions_page.focus_search()

    def _on_session_opened_from_list(self, session_id: str) -> None:
        self.navigate_to("workspace")

    def _on_session_created(self, session: ReasoningSession) -> None:
        self._update_session_header(session)
        self.sessions_page.refresh_sessions()

    def _update_session_header(self, session: ReasoningSession) -> None:
        short_title = session.title if len(session.title) <= 50 else session.title[:47] + "..."
        self.header_session_lbl.setText(f"Session: [{session.session_id}] {short_title}")
        self.header_mode_badge.setText(f"MODE: {session.mode.value.replace('_', ' ').upper()}")
        self.sidebar.select_mode_button(session.mode.value)

    def _on_session_deleted(self, session_id: str) -> None:
        if self.session_mgr.current_session is None:
            self.header_session_lbl.setText("No active session — Compose a new question to begin")
            self.workspace_page.start_new_discussion()

    def _on_mode_changed_externally(self, mode_value: str) -> None:
        self.header_mode_badge.setText(f"MODE: {mode_value.replace('_', ' ').upper()}")
        self.sidebar.select_mode_button(mode_value)

    def _on_connections_updated(self) -> None:
        self.update_summary()
        self.workspace_page.sync_agent_panels()

    def _on_registry_changed(self, agent_id: str, conn: AgentConnection) -> None:
        self.update_summary()
        self.workspace_page.sync_agent_panels()

    def update_summary(self) -> None:
        """Refreshes header and status bar application connection counts."""
        bound_count = self.registry.bound_count
        total_count = self.registry.total_count

        badge_text = f"{bound_count}/{total_count} Applications Bound"
        self.status_summary_badge.setText(badge_text)
        self.status_right_lbl.setText(badge_text)

        if bound_count == total_count:
            self.status_summary_badge.setStyleSheet(
                "background-color: #0F3324; border: 1px solid #065F46; color: #34D399; "
                "border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: 600;"
            )
        elif bound_count > 0:
            self.status_summary_badge.setStyleSheet(
                "background-color: #3B2E14; border: 1px solid #78350F; color: #FBBF24; "
                "border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: 600;"
            )
        else:
            self.status_summary_badge.setStyleSheet(
                "background-color: #161D27; border: 1px solid #2B3543; color: #94A3B8; "
                "border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: 600;"
            )

    def scan_applications(self) -> None:
        """Triggers desktop application scan."""
        self.connections_page.scan_applications()

    def closeEvent(self, event) -> None:
        """Gracefully halts background monitor thread when window closes."""
        if self.monitor:
            self.monitor.stop()
        super().closeEvent(event)
