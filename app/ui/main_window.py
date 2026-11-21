import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.connection_monitor import ConnectionMonitor
from app.core.message_bridge import MessageExchangeBridge
from app.core.window_manager import WindowManager
from app.models.agent import (
    AgentAppDefinition,
    AgentConnection,
    AgentStatus,
    SUPPORTED_AGENTS,
    WindowCandidate,
)
from app.models.session import (
    AgentRoundStatus,
    ReasoningMode,
    ReasoningSession,
    SessionState,
)
from app.storage.database import DatabaseManager
from app.ui.agent_card import AgentCard
from app.ui.response_import_dialog import ResponseImportDialog
from app.ui.session_agent_panel import SessionAgentPanel
from app.utils.logging import get_logger

logger = get_logger("ui.main_window")


class MainWindow(QMainWindow):
    """Main desktop workspace window for TRIAD (Phase 1 & Phase 2)."""

    def __init__(
        self,
        registry: AgentRegistry,
        discovery_service: AppDiscoveryService,
        window_manager: WindowManager,
        database: Optional[DatabaseManager] = None,
        message_bridge: Optional[MessageExchangeBridge] = None,
    ):
        super().__init__()
        self.registry = registry
        self.discovery = discovery_service
        self.window_mgr = window_manager
        self.db = database or DatabaseManager()
        self.bridge = message_bridge or MessageExchangeBridge(
            registry=self.registry,
            window_manager=self.window_mgr,
            database=self.db,
        )

        self.cards: Dict[str, AgentCard] = {}
        self.agent_panels: Dict[str, SessionAgentPanel] = {}

        self.setWindowTitle("TRIAD — Local AI Consensus Workspace")
        self.setMinimumSize(1040, 740)

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
        header_layout.setContentsMargins(24, 16, 24, 16)

        title_box = QVBoxLayout()
        title_box.setSpacing(3)
        app_title = QLabel("TRIAD — Local AI Consensus Workspace")
        app_title.setObjectName("AppTitleLabel")
        subtitle = QLabel("Phase 2: Local Message Exchange Bridge (Round 1 Independent Reasoning)")
        subtitle.setObjectName("AppSubtitleLabel")
        title_box.addWidget(app_title)
        title_box.addWidget(subtitle)
        header_layout.addLayout(title_box)

        header_layout.addStretch()

        self.status_summary_badge = QLabel("0/3 applications bound")
        self.status_summary_badge.setObjectName("StatusSummaryBadge")
        header_layout.addWidget(self.status_summary_badge)

        root_layout.addWidget(header)

        # 2. Main Tabbed Navigation
        self.tabs = QTabWidget()
        root_layout.addWidget(self.tabs, 1)

        # Tab 1: Reasoning Workspace (Phase 2 Central View)
        workspace_tab = self._build_workspace_tab()
        self.tabs.addTab(workspace_tab, "🧠 Reasoning Workspace (Round 1)")

        # Tab 2: Desktop Connections (Phase 1 Management)
        connections_tab = self._build_connections_tab()
        self.tabs.addTab(connections_tab, "🖥️ Desktop Applications")

        # Tab 3: Session History
        history_tab = self._build_history_tab()
        self.tabs.addTab(history_tab, "📜 Session History")

        # Initial message
        self.log_message("TRIAD Phase 2 Workspace active. Local Message Exchange Bridge ready.")

    def _build_workspace_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        # Section A: Session Initiation Card
        init_frame = QFrame()
        init_frame.setStyleSheet(
            "background-color: #12151e; border: 1px solid #232736; border-radius: 8px; padding: 12px;"
        )
        init_layout = QVBoxLayout(init_frame)
        init_layout.setContentsMargins(12, 10, 12, 10)
        init_layout.setSpacing(8)

        # Top line: Title + Mode + Create Button
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Session Title (e.g. Distributed Consensus Engine Design)...")
        self.title_input.setText("Distributed Architecture Consensus")
        top_row.addWidget(self.title_input, 2)

        self.mode_select = QComboBox()
        self.mode_select.addItems([
            "Quick Consensus",
            "Deep Debate",
            "Research Council",
            "Code Review Council",
            "Creative Council",
        ])
        top_row.addWidget(self.mode_select, 1)

        self.btn_create_session = QPushButton("Create Reasoning Session")
        self.btn_create_session.setProperty("class", "global-btn global-btn-primary")
        self.btn_create_session.clicked.connect(self._handle_create_session)
        top_row.addWidget(self.btn_create_session)

        init_layout.addLayout(top_row)

        # Question editor
        self.question_editor = QTextEdit()
        self.question_editor.setPlaceholderText("Enter the central prompt/problem statement for the three AI participants...")
        self.question_editor.setFixedHeight(75)
        self.question_editor.setPlainText(
            "Compare event-driven architecture versus synchronous request-response for high-throughput financial transactions. "
            "Address fault tolerance, latency, and data consistency."
        )
        init_layout.addWidget(self.question_editor)

        # Session Status Banner
        self.session_status_banner = QLabel("DRAFT: Enter question and click 'Create Reasoning Session' to stage prompts.")
        self.session_status_banner.setStyleSheet(
            "font-size: 12px; font-weight: 600; color: #38bdf8; padding: 4px 0px;"
        )
        init_layout.addWidget(self.session_status_banner)

        layout.addWidget(init_frame)

        # Section B: Three Agent Response Panels
        panels_layout = QHBoxLayout()
        panels_layout.setSpacing(12)

        for agent_id, defn in SUPPORTED_AGENTS.items():
            panel = SessionAgentPanel(defn, self)
            panel.copy_focus_requested.connect(self._handle_copy_and_focus)
            panel.import_requested.connect(self._handle_import_response)
            self.agent_panels[agent_id] = panel
            panels_layout.addWidget(panel, 1)

        layout.addLayout(panels_layout, 1)

        # Section C: Activity Log Panel
        log_panel = QWidget()
        log_panel.setObjectName("ActivityLogWidget")
        log_layout = QVBoxLayout(log_panel)
        log_layout.setContentsMargins(12, 8, 12, 10)
        log_layout.setSpacing(4)

        log_header = QLabel("DELIBERATION ACTIVITY LOG")
        log_header.setProperty("class", "detail-label")
        log_layout.addWidget(log_header)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("ActivityLogText")
        self.log_text.setReadOnly(True)
        self.log_text.setFixedHeight(95)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_panel)

        return tab

    def _build_connections_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Controls bar
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

        layout.addWidget(controls_bar)

        # Dashboard Grid (3 Cards)
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

        layout.addWidget(dashboard_widget, 1)
        return tab

    def _build_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        lbl = QLabel("Past Reasoning Sessions")
        lbl.setStyleSheet("font-size: 16px; font-weight: 600; color: #f8fafc;")
        header_layout.addWidget(lbl)
        header_layout.addStretch()

        btn_reload = QPushButton("Refresh History")
        btn_reload.setProperty("class", "global-btn")
        btn_reload.clicked.connect(self._load_session_history)
        header_layout.addWidget(btn_reload)

        layout.addLayout(header_layout)

        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Session ID", "Date", "Title", "State", "Responses"])
        self.history_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.history_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.setSelectionMode(QTableWidget.SingleSelection)
        self.history_table.doubleClicked.connect(self._on_history_session_selected)
        layout.addWidget(self.history_table, 1)

        bottom_bar = QHBoxLayout()
        bottom_bar.addStretch()
        btn_restore = QPushButton("Restore Selected Session")
        btn_restore.setProperty("class", "global-btn global-btn-primary")
        btn_restore.clicked.connect(self._on_history_session_selected)
        bottom_bar.addWidget(btn_restore)
        layout.addLayout(bottom_bar)

        return tab

    def _setup_monitor(self) -> None:
        self.monitor = ConnectionMonitor(
            registry=self.registry,
            discovery_service=self.discovery,
            window_manager=self.window_mgr,
            database_manager=self.db,
            poll_interval_sec=1.5,
        )
        self.monitor.start()

    def closeEvent(self, event) -> None:
        if hasattr(self, "monitor") and self.monitor:
            self.monitor.stop()
        super().closeEvent(event)

    def log_message(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        logger.info(message)

    def _update_summary_status(self) -> None:
        summary = self.registry.get_summary_text()
        self.status_summary_badge.setText(summary)
        is_ready = self.registry.bound_count == self.registry.total_count
        self.status_summary_badge.setProperty("ready", "true" if is_ready else "false")
        self.status_summary_badge.style().unpolish(self.status_summary_badge)
        self.status_summary_badge.style().polish(self.status_summary_badge)

    def _on_registry_changed(self, agent_id: str, conn: AgentConnection) -> None:
        if agent_id in self.cards:
            self.cards[agent_id].set_connection(conn)
        if agent_id in self.agent_panels:
            self.agent_panels[agent_id].set_connection_status(conn.status)
        self._update_summary_status()

    # -------------------------------------------------------------------------
    # Phase 2: Session & Message Exchange Handlers
    # -------------------------------------------------------------------------

    def _handle_create_session(self) -> None:
        title = self.title_input.text().strip()
        question = self.question_editor.toPlainText().strip()
        if not question:
            QMessageBox.warning(self, "Validation Error", "Please enter a question or problem statement.")
            return

        mode_map = {
            "Quick Consensus": ReasoningMode.QUICK_CONSENSUS,
            "Deep Debate": ReasoningMode.DEEP_DEBATE,
            "Research Council": ReasoningMode.RESEARCH_COUNCIL,
            "Code Review Council": ReasoningMode.CODE_REVIEW,
            "Creative Council": ReasoningMode.CREATIVE_COUNCIL,
        }
        mode = mode_map.get(self.mode_select.currentText(), ReasoningMode.QUICK_CONSENSUS)

        try:
            session = self.bridge.create_session(title=title, initial_question=question, mode=mode)
            for agent_id, panel in self.agent_panels.items():
                panel.clear()
                panel.set_round_status(AgentRoundStatus.PROMPT_STAGED)
                conn = self.registry.get_connection(agent_id)
                if conn:
                    panel.set_connection_status(conn.status)

            self.session_status_banner.setText("ROUND 1 READY: 0/3 Responses Collected")
            self.session_status_banner.setStyleSheet("font-size: 12px; font-weight: 600; color: #fbbf24;")
            self.log_message(f"Created Reasoning Session [{session.session_id}]: '{session.title}'. Staged 3 isolated prompts.")
            self._load_session_history()
        except Exception as e:
            QMessageBox.critical(self, "Error Creating Session", str(e))

    def _handle_copy_and_focus(self, agent_id: str) -> None:
        if not self.bridge.active_session:
            QMessageBox.information(self, "Notice", "Please create a reasoning session first.")
            return

        session_id = self.bridge.active_session.session_id
        success, msg = self.bridge.copy_and_focus(session_id, 1, agent_id)
        self.log_message(msg)

        if success:
            panel = self.agent_panels.get(agent_id)
            if panel and (not panel.current_response):
                panel.set_round_status(AgentRoundStatus.PROMPT_COPIED)

    def _handle_import_response(self, agent_id: str) -> None:
        if not self.bridge.active_session:
            QMessageBox.information(self, "Notice", "Please create a reasoning session first.")
            return

        session_id = self.bridge.active_session.session_id
        panel = self.agent_panels.get(agent_id)
        existing_rev = panel.current_response.revision_number if panel and panel.current_response else None

        # Fetch clipboard content safely
        from PySide6.QtWidgets import QApplication
        clipboard_text = ""
        app = QApplication.instance()
        if app:
            try:
                clipboard_text = app.clipboard().text() or ""
            except Exception:
                clipboard_text = ""

        # Open inspection dialog
        defn = SUPPORTED_AGENTS[agent_id]
        dlg = ResponseImportDialog(
            definition=defn,
            existing_revision=existing_rev,
            initial_text=clipboard_text,
            parent=self,
        )

        if dlg.exec() and dlg.confirmed_text:
            success, msg, response_obj = self.bridge.import_response(
                session_id=session_id,
                round_number=1,
                agent_id=agent_id,
                response_text=dlg.confirmed_text,
                confirm_revision=dlg.confirmed_revision,
            )

            if success and response_obj:
                if panel:
                    panel.set_response(response_obj)
                self.log_message(f"Imported response for {defn.display_name} (SHA: {response_obj.sha256_hash[:12]}...).")
                self._update_workspace_progress(session_id)
            else:
                QMessageBox.warning(self, "Import Notice", msg)

    def _update_workspace_progress(self, session_id: str) -> None:
        progress = self.bridge.get_round_progress(session_id, 1)
        self.session_status_banner.setText(progress["summary_text"])
        if progress["is_complete"]:
            self.session_status_banner.setStyleSheet("font-size: 12px; font-weight: 700; color: #34d399;")
            self.log_message("★ Independent Round 1 Complete! All 3 participant responses verified and accepted.")
        else:
            self.session_status_banner.setStyleSheet("font-size: 12px; font-weight: 600; color: #fbbf24;")
        self._load_session_history()

    def _load_session_history(self) -> None:
        sessions = self.db.list_reasoning_sessions(limit=30)
        self.history_table.setRowCount(len(sessions))
        for row, s in enumerate(sessions):
            resp_count = len(self.db.get_session_responses(s["session_id"], s.get("current_round", 1)))
            id_item = QTableWidgetItem(s["session_id"])
            date_item = QTableWidgetItem(s["created_at"][:19].replace("T", " "))
            title_item = QTableWidgetItem(s["title"])
            state_item = QTableWidgetItem(s["state"].upper())
            resp_item = QTableWidgetItem(f"{resp_count}/3")

            for item in (id_item, date_item, title_item, state_item, resp_item):
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)

            self.history_table.setItem(row, 0, id_item)
            self.history_table.setItem(row, 1, date_item)
            self.history_table.setItem(row, 2, title_item)
            self.history_table.setItem(row, 3, state_item)
            self.history_table.setItem(row, 4, resp_item)

    def _on_history_session_selected(self) -> None:
        selected_rows = self.history_table.selectionModel().selectedRows()
        if not selected_rows:
            return

        row = selected_rows[0].row()
        session_id_item = self.history_table.item(row, 0)
        if not session_id_item:
            return

        session_id = session_id_item.text()
        session = self.bridge.restore_session(session_id)
        if not session:
            QMessageBox.warning(self, "Restore Error", f"Unable to restore session {session_id}.")
            return

        # Restore UI
        self.title_input.setText(session.title)
        self.question_editor.setPlainText(session.initial_question)

        for agent_id, panel in self.agent_panels.items():
            panel.clear()
            if agent_id in session.responses:
                panel.set_response(session.responses[agent_id])
            elif agent_id in session.prompts:
                panel.set_round_status(session.agent_statuses.get(agent_id, AgentRoundStatus.PROMPT_STAGED))

        self._update_workspace_progress(session_id)
        self.tabs.setCurrentIndex(0)
        self.log_message(f"Restored session [{session.session_id}]: '{session.title}'.")

    # -------------------------------------------------------------------------
    # Phase 1: Application Discovery & Window Management Handlers
    # -------------------------------------------------------------------------

    def scan_applications(self) -> None:
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
            if "foreground restriction" in msg.lower():
                QMessageBox.information(
                    self,
                    "Focus Notification",
                    f"{display_name} window was notified. Windows foreground rules may have flashed the application icon on your taskbar.",
                )

    def _handle_card_disconnect(self, agent_id: str) -> None:
        self.registry.disconnect(agent_id)
        if self.db:
            self.db.log_discovery_event(
                agent_id=agent_id,
                event_type="DISCONNECTED",
            )
        self.log_message(f"Disconnected {SUPPORTED_AGENTS[agent_id].display_name}.")

    def connect_available_apps(self) -> None:
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
        self.log_message("Refreshing application states...")
        self.monitor.check_connections_once()
        self.scan_applications()

    def disconnect_all(self) -> None:
        self.registry.disconnect_all()
        self.log_message("Disconnected all registered applications.")
