from typing import List, Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.models.agent import WindowCandidate


class WindowPickerDialog(QDialog):
    """Dialog allowing the user to select the intended application window when multiple candidates exist."""

    def __init__(self, agent_name: str, candidates: List[WindowCandidate], parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Select Window — {agent_name}")
        self.setMinimumSize(680, 360)
        self.candidates = candidates
        self.selected_candidate: Optional[WindowCandidate] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        info_label = QLabel(
            f"Multiple candidate windows were detected for <b>{agent_name}</b>.<br>"
            "Please select the active window you wish to bind to TRIAD:"
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        self.table = QTableWidget(len(candidates), 4)
        self.table.setHorizontalHeaderLabels(["Title", "PID", "HWND", "Confidence"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)

        for row, cand in enumerate(candidates):
            title_item = QTableWidgetItem(cand.title)
            pid_item = QTableWidgetItem(str(cand.pid))
            hwnd_item = QTableWidgetItem(hex(cand.hwnd))
            conf_item = QTableWidgetItem(f"{int(cand.confidence * 100)}%")

            title_item.setFlags(title_item.flags() ^ Qt.ItemIsEditable)
            pid_item.setFlags(pid_item.flags() ^ Qt.ItemIsEditable)
            hwnd_item.setFlags(hwnd_item.flags() ^ Qt.ItemIsEditable)
            conf_item.setFlags(conf_item.flags() ^ Qt.ItemIsEditable)

            self.table.setItem(row, 0, title_item)
            self.table.setItem(row, 1, pid_item)
            self.table.setItem(row, 2, hwnd_item)
            self.table.setItem(row, 3, conf_item)

        self.table.selectRow(0)
        self.table.doubleClicked.connect(self._on_accept)
        layout.addWidget(self.table)

        btn_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btn_box.accepted.connect(self._on_accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)

    def _on_accept(self) -> None:
        selected_rows = self.table.selectionModel().selectedRows()
        if selected_rows:
            row = selected_rows[0].row()
            if 0 <= row < len(self.candidates):
                self.selected_candidate = self.candidates[row]
        self.accept()

