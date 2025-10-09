from __future__ import annotations

from typing import List, Optional
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHBoxLayout, QMessageBox,
)
from PySide6.QtCore import Qt

from .job_queue_sql import get_all_jobs, update_job_status


class JobDialog(QDialog):
    """Dialog to show and manage upload jobs."""

    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent)
        self.setWindowTitle("Upload Jobs")
        self.resize(700, 400)

        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["ID", "Status", "Attempts", "Max", "Progress", "File", "Last Error", "Drive ID"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh")
        self.retry_btn = QPushButton("Retry Selected")
        self.cancel_btn = QPushButton("Cancel Selected")
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.retry_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        self.refresh_btn.clicked.connect(self.refresh)
        self.retry_btn.clicked.connect(self.retry_selected)
        self.cancel_btn.clicked.connect(self.cancel_selected)

        self.refresh()

    def refresh(self) -> None:
        jobs = get_all_jobs()
        self.table.setRowCount(0)
        for j in jobs:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setItem(r, 0, QTableWidgetItem(str(j.id)))
            self.table.setItem(r, 1, QTableWidgetItem(str(j.status)))
            self.table.setItem(r, 2, QTableWidgetItem(str(j.attempts)))
            self.table.setItem(r, 3, QTableWidgetItem(str(j.max_attempts)))
            # Progress: show uploaded/total if available
            prog = ""
            try:
                if getattr(j, 'uploaded_bytes', 0) and getattr(j, 'total_bytes', None):
                    prog = f"{int(j.uploaded_bytes)}/{int(j.total_bytes)}"
                elif getattr(j, 'uploaded_bytes', 0):
                    prog = f"{int(j.uploaded_bytes)} bytes"
            except Exception:
                prog = ""
            self.table.setItem(r, 4, QTableWidgetItem(prog))
            self.table.setItem(r, 5, QTableWidgetItem(str(j.file_path)))
            self.table.setItem(r, 6, QTableWidgetItem(str(j.last_error or "")))
            self.table.setItem(r, 7, QTableWidgetItem(str(j.drive_file_id or "")))

    def _selected_job_ids(self) -> List[str]:
        ids: List[str] = []
        for idx in self.table.selectionModel().selectedRows():
            row = idx.row()
            item = self.table.item(row, 0)
            if item:
                ids.append(item.text())
        return ids

    def retry_selected(self) -> None:
        ids = self._selected_job_ids()
        if not ids:
            QMessageBox.information(self, "No selection", "No jobs selected to retry")
            return
        for job_id in ids:
            try:
                update_job_status(job_id, 'pending')
            except Exception:
                # Best-effort: continue updating other jobs
                pass
        QMessageBox.information(self, "Queued", "Selected jobs marked for retry")
        self.refresh()

    def cancel_selected(self) -> None:
        ids = self._selected_job_ids()
        if not ids:
            QMessageBox.information(self, "No selection", "No jobs selected to cancel")
            return
        from .job_queue_sql import set_job_cancel_requested
        for job_id in ids:
            try:
                # Ask the running worker to cancel gracefully; also mark status as cancelled
                set_job_cancel_requested(job_id)
                update_job_status(job_id, 'cancelled')
            except Exception:
                pass
        QMessageBox.information(self, "Cancelled", "Selected jobs cancelled (requested)")
        self.refresh()

