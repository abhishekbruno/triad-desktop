import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.connection_monitor import ConnectionMonitor
from app.core.window_manager import WindowManager
from app.models.agent import (
    AgentAppDefinition,
    AgentConnection,
    AgentStatus,
    SUPPORTED_AGENTS,
    WindowCandidate,
)
from app.storage.database import DatabaseManager
from app.ui.agent_card import AgentCard
from app.utils.logging import get_logger

logger = get_logger("ui.main_window")


class MainWindow(QMainWindow):
    """Main desktop workspace window for TRIAD Phase 1."""

    def __init__(
        self,
        registry: AgentRegistry,
        discovery_service: AppDiscoveryService,
        window_manager: WindowManager,
        database: Optional[DatabaseManager] = None,
    ):
        super().__init__()
        self.registry = registry
        self.discovery = discovery_service
        self.window_mgr = window_manager
        self.db = database

        self.cards: Dict[str, AgentCard] = {}

        self.setWindowTitle("TRIAD — Local AI Consensus Workspace")
        self.setMinimumSize(980, 680)

        self._load_stylesheet()
        self._build_ui()
        self._setup_monitor()

        # Connect registry notifications to UI updates
        self.registry.subscribe(self._on_registry_changed)

        # Initial automatic scan
        QTimer.singleShot(150, self.scan_applications)

    def _load_stylesheet(self) -> None:
        qss_path = Path(__file__).parent / "styles.qss"
        if qss_path.exists():
            with open(qss_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def _build_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # 1. Header Bar
        header = QWidget()
        header.setObjectName("HeaderWidget")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 18, 24, 18)

        title_box = QVBoxLayout()
        title_box.setSpacing(4)
        app_title = QLabel("TRIAD — Local AI Consensus Workspace")
        app_title.setObjectName("AppTitleLabel")
        subtitle = QLabel("Phase 1: Native Desktop Application Discovery, Registration & Focus")
        subtitle.setObjectName("AppSubtitleLabel")
        title_box.addWidget(app_title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.status_summary_badge = QLabel("0/3 applications bound")
        self.status_summary_badge.setObjectName("StatusSummaryBadge")
        header_layout.addWidget(self.status_summary_badge)

        root_layout.addWidget(header)

        # 2. Global Controls Bar
        controls_bar = QWidget()
        controls_bar.setObjectName("GlobalControlsBar")
        controls_layout = QHBoxLayout(controls_bar)
        controls_layout.setContentsMargins(24, 12, 24, 12)
        controls_layout.setSpacing(10)

        self.btn_scan = QPushButton("Scan Applications")
        self.btn_scan.setProperty("class", "global-btn global-btn-primary")
        self.btn_scan.clicked.connect(self.scan_applications)

        self.btn_connect_all = QPushButton("Connect Available Apps")
        self.btn_connect_all.setProperty("class", "global-btn")
        self.btn_connect_all.clicked.connect(self.connect_available_apps)

        self.btn_refresh = QPushButton("Refresh All")
        self.btn_refresh.setProperty("class", "global-btn")
        self.btn_refresh.clicked.connect(self.refresh_all)

        self.btn_disconnect_all = QPushButton("Disconnect All")
        self.btn_disconnect_all.setProperty("class", "global-btn")
        self.btn_disconnect_all.clicked.connect(self.disconnect_all)

        controls_layout.addWidget(self.btn_scan)
        controls_layout.addWidget(self.btn_connect_all)
        controls_layout.addWidget(self.btn_refresh)
        controls_layout.addWidget(self.btn_disconnect_all)
        controls_layout.addStretch()

        root_layout.addWidget(controls_bar)

        # 3. Connection Dashboard (3 Agent Cards Grid)
        dashboard_widget = QWidget()
        dashboard_layout = QHBoxLayout(dashboard_widget)
        dashboard_layout.setContentsMargins(18, 18, 18, 18)
        dashboard_layout.setSpacing(16)

        for agent_id, defn in SUPPORTED_AGENTS.items():
            card = AgentCard(defn, self)
            card.connect_requested.connect(self._handle_card_connect)
            card.focus_requested.connect(self._handle_card_focus)
            card.disconnect_requested.connect(self._handle_card_disconnect)
            self.cards[agent_id] = card
            dashboard_layout.addWidget(card)

        root_layout.addWidget(dashboard_widget, 1)

        # 4. Activity Log and Console
        log_panel = QWidget()
        log_panel.setObjectName("ActivityLogWidget")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(24, 10, 24, 14)
        log_layout.setSpacing(6)

        log_header = QLabel("WORKSPACE ACTIVITY LOG")
        log_header.setProperty("class", "detail-label")
        log_layout.addWidget(log_header)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("ActivityLogText")
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(110)
        log_layout.addWidget(self.log_text)

        root_layout.addWidget(log_panel)

        self.log_message("TRIAD Phase 1 Workspace initialized. Local discovery ready.")

    def _setup_monitor(self) -> None:
        """Sets up the ConnectionMonitor and periodic UI update."""
        self.monitor = ConnectionMonitor(
            registry=self.registry,
            discovery_service=self.discovery,
            window_manager=self.window_mgr,
            database_manager=self.db,
            poll_interval_sec=1.5,
        )
        self.monitor.start()

    def closeEvent(self, event) -> None:
        """Stops background threads cleanly on exit."""
        if hasattr(self, "monitor") and self.monitor:
            self.monitor.stop()
        super().closeEvent(event)

    def log_message(self, message: str) -> None:
        """Appends a timestamped status line to the activity log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        logger.info(message)

    def _update_summary_status(self) -> None:
        """Updates the top right status banner."""
        summary = self.registry.get_summary_text()
        self.status_summary_badge.setText(summary)
        is_ready = self.registry.bound_count == self.registry.total_count
        self.status_summary_badge.setProperty("ready", "true" if is_ready else "false")
        self.status_summary_badge.style().unpolish(self.status_summary_badge)
        self.status_summary_badge.style().polish(self.status_summary_badge)

    def _on_registry_changed(self, agent_id: str, conn: AgentConnection) -> None:
        """Invoked when an agent status changes in the registry."""
        if agent_id in self.cards:
            self.cards[agent_id].set_connection(conn)
        self._update_summary_status()

    def scan_applications(self) -> None:
        """Scans the system for all target applications and updates candidate lists."""
        self.log_message("Scanning running desktop windows...")
        candidates = self.discovery.discover_candidates()

        total_candidates = sum(len(cands) for cands in candidates.values())
        self.log_message(f"Scan complete. Discovered {total_candidates} total candidate window(s).")

        for agent_id, cands in candidates.items():
            card = self.cards.get(agent_id)
            if card:
                card.set_candidates(cands)
                if cands and self.registry.get_connection(agent_id).status != AgentStatus.BOUND:
                    self.registry.set_detected(
                        agent_id,
                        pid=cands[0].pid,
                        hwnd=cands[0].hwnd,
                        exec_path=cands[0].executable_path,
                    )
                    self.log_message(
                        f"Detected {SUPPORTED_AGENTS[agent_id].display_name}: "
                        f"{cands[0].executable_name} (PID: {cands[0].pid}, {len(cands)} window(s))"
                    )

    def _handle_card_connect(self, agent_id: str, candidate: WindowCandidate) -> None:
        """Binds an agent to the specified candidate window."""
        self.registry.bind_candidate(agent_id, candidate)
        if self.db:
            self.db.set_agent_preference(
                agent_id=agent_id,
                display_name=SUPPORTED_AGENTS[agent_id].display_name,
                preferred_executable=candidate.executable_name,
                preferred_title_keyword=candidate.title,
            )
            self.db.log_discovery_event(
                agent_id=agent_id,
                event_type="BOUND",
                executable_name=candidate.executable_name,
                details=f"HWND {candidate.hwnd}, PID {candidate.pid}, Title: {candidate.title}",
            )
        self.log_message(f"Successfully bound {SUPPORTED_AGENTS[agent_id].display_name} to HWND {hex(candidate.hwnd)}.")

    def _handle_card_focus(self, agent_id: str) -> None:
        """Brings the bound native application window to front without disturbing chat state."""
        conn = self.registry.get_connection(agent_id)
        if not conn or not conn.window_handle:
            self.log_message(f"Cannot focus {agent_id}: no window handle bound.")
            return

        success, msg = self.window_mgr.focus_window(conn.window_handle)
        display_name = SUPPORTED_AGENTS[agent_id].display_name
        if success:
            self.log_message(f"Focused {display_name} (HWND: {hex(conn.window_handle)}).")
        else:
            self.log_message(f"Notice focusing {display_name}: {msg}")
            # Non-blocking notification if Windows restrictions intervene
            if "foreground restriction" in msg.lower():
                QMessageBox.information(
                    self,
                    "Focus Notification",
                    f"{display_name} window was notified. Windows foreground rules may have flashed the application icon on your taskbar.",
                )

    def _handle_card_disconnect(self, agent_id: str) -> None:
        """Unbinds an agent."""
        self.registry.disconnect(agent_id)
        if self.db:
            self.db.log_discovery_event(
                agent_id=agent_id,
                event_type="DISCONNECTED",
            )
        self.log_message(f"Disconnected {SUPPORTED_AGENTS[agent_id].display_name}.")

    def connect_available_apps(self) -> None:
        """Binds all detected applications that have an unambiguous candidate window."""
        candidates = self.discovery.discover_candidates()
        bound_any = False
        for agent_id, cands in candidates.items():
            conn = self.registry.get_connection(agent_id)
            if conn and conn.status != AgentStatus.BOUND and cands:
                best = cands[0]
                self._handle_card_connect(agent_id, best)
                bound_any = True

        if not bound_any:
            self.log_message("No new unbound candidate windows available to connect.")

    def refresh_all(self) -> None:
        """Performs a full re-validation of connections and rescans system."""
        self.log_message("Refreshing application states...")
        self.monitor.check_connections_once()
        self.scan_applications()

    def disconnect_all(self) -> None:
        """Unbinds all currently registered applications."""
        self.registry.disconnect_all()
        self.log_message("Disconnected all registered applications.")

