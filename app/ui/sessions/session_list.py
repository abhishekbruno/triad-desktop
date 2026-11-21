from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.session_manager import SessionManager
from app.models.session import ReasoningSession


class SessionListPage(QWidget):
    """View displaying all stored reasoning sessions with search, rename, and deletion with confirmation."""

    session_opened = Signal(str)         # (session_id)
    new_session_requested = Signal()

    def __init__(self, session_manager: SessionManager, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.session_mgr = session_manager
        self.sessions: List[ReasoningSession] = []

        self._build_ui()
        self._wire_signals()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)

        # 1. Header Row
        header_row = QHBoxLayout()
        title_box = QVBoxLayout()
        title_lbl = QLabel("ALL REASONING SESSIONS")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #EDF2F7; letter-spacing: 0.5px;")
        sub_lbl = QLabel("Browse, search, resume, and manage your local consensus reasoning sessions.")
        sub_lbl.setStyleSheet("font-size: 11px; color: #94A3B8;")
        title_box.addWidget(title_lbl)
        title_box.addWidget(sub_lbl)
        header_row.addLayout(title_box)

        header_row.addStretch()

        self.btn_new = QPushButton("+ New Discussion")
        self.btn_new.setProperty("class", "btn-primary")
        self.btn_new.clicked.connect(self.new_session_requested.emit)
        header_row.addWidget(self.btn_new)
        layout.addLayout(header_row)

        # 2. Search & Filter Bar
        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search sessions by title or question content...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_text_changed)
        search_row.addWidget(self.search_input, 1)

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh_sessions)
        search_row.addWidget(self.btn_refresh)
        layout.addLayout(search_row)

        # 3. Sessions Table
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "Title", "Mode", "State", "Rounds", "Created", "Last Updated"
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.doubleClicked.connect(self._on_open_clicked)
        layout.addWidget(self.table, 1)

        # 4. Action Row
        actions_row = QHBoxLayout()
        self.btn_open = QPushButton("Open Session")
        self.btn_open.setProperty("class", "btn-primary")
        self.btn_open.clicked.connect(self._on_open_clicked)
        actions_row.addWidget(self.btn_open)

        self.btn_rename = QPushButton("Rename...")
        self.btn_rename.clicked.connect(self._on_rename_clicked)
        actions_row.addWidget(self.btn_rename)

        self.btn_delete = QPushButton("Delete Session")
        self.btn_delete.setProperty("class", "btn-danger")
        self.btn_delete.clicked.connect(self._on_delete_clicked)
        actions_row.addWidget(self.btn_delete)

        actions_row.addStretch()

        self.count_lbl = QLabel("0 sessions stored")
        self.count_lbl.setStyleSheet("font-size: 11px; color: #64748B;")
        actions_row.addWidget(self.count_lbl)

        layout.addLayout(actions_row)

    def _wire_signals(self) -> None:
        self.session_mgr.session_created.connect(lambda s: self.refresh_sessions())
        self.session_mgr.session_updated.connect(lambda s: self.refresh_sessions())
        self.session_mgr.session_deleted.connect(lambda s_id: self.refresh_sessions())

    def refresh_sessions(self) -> None:
        """Reloads all sessions from persistent storage."""
        query = self.search_input.text().strip()
        if query:
            self.sessions = self.session_mgr.search_sessions(query)
        else:
            self.sessions = self.session_mgr.list_recent_sessions(limit=100)

        self.table.setRowCount(len(self.sessions))
        for row, s in enumerate(self.sessions):
            title_item = QTableWidgetItem(s.title)
            mode_item = QTableWidgetItem(s.mode.value.replace("_", " ").title())
            state_item = QTableWidgetItem(s.state.value.replace("_", " ").upper())
            rounds_item = QTableWidgetItem(f"{s.current_round} / {s.max_rounds}")
            created_item = QTableWidgetItem(s.created_at[:19].replace("T", " "))
            updated_item = QTableWidgetItem(s.updated_at[:19].replace("T", " "))

            title_item.setFlags(title_item.flags() ^ Qt.ItemIsEditable)
            mode_item.setFlags(mode_item.flags() ^ Qt.ItemIsEditable)
            state_item.setFlags(state_item.flags() ^ Qt.ItemIsEditable)
            rounds_item.setFlags(rounds_item.flags() ^ Qt.ItemIsEditable)
            created_item.setFlags(created_item.flags() ^ Qt.ItemIsEditable)
            updated_item.setFlags(updated_item.flags() ^ Qt.ItemIsEditable)

            self.table.setItem(row, 0, title_item)
            self.table.setItem(row, 1, mode_item)
            self.table.setItem(row, 2, state_item)
            self.table.setItem(row, 3, rounds_item)
            self.table.setItem(row, 4, created_item)
            self.table.setItem(row, 5, updated_item)

        self.count_lbl.setText(f"{len(self.sessions)} sessions stored")
        if self.sessions:
            self.table.selectRow(0)

    def _on_search_text_changed(self) -> None:
        self.refresh_sessions()

    def _get_selected_session(self) -> Optional[ReasoningSession]:
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows:
            return None
        row = selected_rows[0].row()
        if 0 <= row < len(self.sessions):
            return self.sessions[row]
        return None

    def _on_open_clicked(self) -> None:
        session = self._get_selected_session()
        if not session:
            QMessageBox.information(self, "Select Session", "Please select a session from the table to open.")
            return

        self.session_mgr.load_session(session.session_id)
        self.session_opened.emit(session.session_id)

    def _on_rename_clicked(self) -> None:
        session = self._get_selected_session()
        if not session:
            QMessageBox.information(self, "Select Session", "Please select a session to rename.")
            return

        new_title, ok = QInputDialog.getText(
            self,
            "Rename Reasoning Session",
            "Enter new session title:",
            QLineEdit.Normal,
            session.title,
        )
        if ok and new_title.strip():
            self.session_mgr.rename_session(session.session_id, new_title.strip())
            self.refresh_sessions()

    def _on_delete_clicked(self) -> None:
        session = self._get_selected_session()
        if not session:
            QMessageBox.information(self, "Select Session", "Please select a session to delete.")
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to permanently delete session '{session.title}'?\n\nThis action cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm == QMessageBox.Yes:
            self.session_mgr.delete_session(session.session_id)
            self.refresh_sessions()

    def focus_search(self) -> None:
        """Focuses the search box for quick typing."""
        self.search_input.setFocus()
        self.search_input.selectAll()
