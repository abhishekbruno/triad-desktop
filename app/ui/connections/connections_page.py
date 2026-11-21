from typing import Dict, List, Optional
from PySide6.QtCore import Qt, QTimer, Signal
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

from app.core.agent_registry import AgentRegistry
from app.core.app_discovery import AppDiscoveryService
from app.core.window_manager import WindowManager
from app.models.agent import AgentAppDefinition, AgentConnection, AgentStatus, SUPPORTED_AGENTS, WindowCandidate
from app.ui.agent_card import AgentCard
from app.ui.window_picker_dialog import WindowPickerDialog
from app.utils.logging import get_logger

logger = get_logger("ui.connections_page")


class ConnectionsPage(QWidget):
    """Dedicated connections dashboard embedding Phase 1 app discovery, window picker, scan, and focus."""

    connections_updated = Signal()

    def __init__(
        self,
        registry: AgentRegistry,
        discovery_service: AppDiscoveryService,
        window_manager: WindowManager,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.registry = registry
        self.discovery = discovery_service
        self.window_mgr = window_manager
        self.cards: Dict[str, AgentCard] = {}

        self._build_ui()
        self._wire_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # 1. Top Header Row
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("DESKTOP APPLICATION CONNECTIONS")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #EDF2F7; letter-spacing: 0.5px;")
        sub_lbl = QLabel("Connect, monitor, and focus your local ChatGPT, Claude, and Gemini desktop applications.")
        sub_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_row.addLayout(title_box)

        header_row.addStretch()

        self.btn_scan = QPushButton("Scan Desktop Applications")
        self.btn_scan.setProperty("class", "btn-primary")
        self.btn_scan.clicked.connect(self.scan_applications)
        header_row.addWidget(self.btn_scan)
        layout.addLayout(header_row)

        # 2. Three Agent Cards (Phase 1 connection management)
        cards_frame = QFrame()
        cards_layout = QHBoxLayout(cards_frame)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setSpacing(14)

        for agent_id, defn in SUPPORTED_AGENTS.items():
            card = AgentCard(defn, parent=cards_frame)
            card.connect_requested.connect(self._handle_card_connect)
            card.focus_requested.connect(self._handle_card_focus)
            card.disconnect_requested.connect(self._handle_card_disconnect)
            self.cards[agent_id] = card
            cards_layout.addWidget(card)

        layout.addWidget(cards_frame)

        # 3. Connection Telemetry & Audit Log Table
        telem_title = QLabel("DISCOVERY & CONNECTION AUDIT LOG")
        telem_title.setStyleSheet("font-size: 11px; font-weight: 700; color: #64748B; letter-spacing: 0.8px;")
        layout.addWidget(telem_title)

        self.audit_table = QTableWidget(0, 4)
        self.audit_table.setHorizontalHeaderLabels(["Agent", "Status", "Process / Window", "Last Seen"])
        self.audit_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.audit_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.audit_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.audit_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.audit_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.audit_table.setMaximumHeight(200)
        layout.addWidget(self.audit_table)

    def _wire_signals(self) -> None:
        self.registry.subscribe(self._on_registry_changed)

    def scan_applications(self) -> None:
        """Runs the Windows Application Discovery Service and updates cards."""
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Scanning Windows...")

        def _do_scan():
            candidates = self.discovery.scan_all()
            for agent_id, card in self.cards.items():
                card_candidates = candidates.get(agent_id, [])
                card.set_candidates(card_candidates)
                conn = self.registry.get_connection(agent_id)
                if card_candidates and conn and conn.status == AgentStatus.MISSING:
                    best = card_candidates[0]
                    self.registry.set_detected(agent_id, pid=best.pid, hwnd=best.hwnd, exec_path=best.executable_path)

            self.btn_scan.setEnabled(True)
            self.btn_scan.setText("Scan Desktop Applications")
            self._update_audit_table()
            self.connections_updated.emit()

        QTimer.singleShot(100, _do_scan)

    def _on_registry_changed(self, agent_id: str, conn: AgentConnection) -> None:
        """Listener invoked when AgentRegistry status changes."""
        if agent_id in self.cards:
            self.cards[agent_id].set_connection(conn)
        self._update_audit_table()
        self.connections_updated.emit()

    def _handle_card_connect(self, agent_id: str, candidate: Optional[WindowCandidate]) -> None:
        """Binds an agent to a discovered window."""
        card = self.cards.get(agent_id)
        if not card or not card.available_candidates:
            return

        if len(card.available_candidates) > 1 and candidate is None:
            picker = WindowPickerDialog(card.definition.display_name, card.available_candidates, self)
            if picker.exec() and picker.selected_candidate:
                self.registry.bind_candidate(agent_id, picker.selected_candidate)
        else:
            chosen = candidate or card.available_candidates[0]
            self.registry.bind_candidate(agent_id, chosen)

    def _handle_card_focus(self, agent_id: str) -> None:
        """Focuses the connected desktop window."""
        conn = self.registry.get_connection(agent_id)
        if not conn or not conn.window_handle:
            return
        self.window_mgr.focus_window(conn.window_handle)

    def _handle_card_disconnect(self, agent_id: str) -> None:
        """Disconnects an agent."""
        self.registry.disconnect(agent_id)

    def _update_audit_table(self) -> None:
        """Updates the live status audit table."""
        self.audit_table.setRowCount(len(SUPPORTED_AGENTS))
        for row, (agent_id, defn) in enumerate(SUPPORTED_AGENTS.items()):
            conn = self.registry.get_connection(agent_id)
            status_text = conn.status.value.upper() if conn else "MISSING"

            agent_item = QTableWidgetItem(defn.display_name)
            status_item = QTableWidgetItem(status_text)
            proc_item = QTableWidgetItem(
                f"{conn.executable_path or 'PID: ' + str(conn.process_id)} (HWND: {hex(conn.window_handle or 0)})"
                if conn and conn.window_handle
                else "None bound"
            )
            time_item = QTableWidgetItem("Active" if conn and conn.status == AgentStatus.BOUND else "Inactive")

            agent_item.setFlags(agent_item.flags() ^ Qt.ItemIsEditable)
            status_item.setFlags(status_item.flags() ^ Qt.ItemIsEditable)
            proc_item.setFlags(proc_item.flags() ^ Qt.ItemIsEditable)
            time_item.setFlags(time_item.flags() ^ Qt.ItemIsEditable)

            self.audit_table.setItem(row, 0, agent_item)
            self.audit_table.setItem(row, 1, status_item)
            self.audit_table.setItem(row, 2, proc_item)
            self.audit_table.setItem(row, 3, time_item)
