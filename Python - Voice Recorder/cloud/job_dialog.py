from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QMessageBox
from PySide6.QtCore import Qt
from typing import List

from .job_queue_sql import get_all_jobs, update_job_status, enqueue_job


class JobDialog(QDialog):
    """Dialog to show and manage upload jobs."""

    from __future__ import annotations

    from PySide6.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QHBoxLayout, QMessageBox
    from PySide6.QtCore import Qt
    from typing import List

    from .job_queue_sql import get_all_jobs, update_job_status, enqueue_job


    class JobDialog(QDialog):
        """Dialog to show and manage upload jobs."""

        def __init__(self, parent=None):
            super().__init__(parent)
            from __future__ import annotations

            from typing import List, Optional

            from PySide6.QtWidgets import (
                QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
                QPushButton, QHBoxLayout, QMessageBox,
            )

            from .job_queue_sql import get_all_jobs, update_job_status


            class JobDialog(QDialog):
                """Dialog to show and manage upload jobs."""

                def __init__(self, parent: Optional[QDialog] = None):
                    super().__init__(parent)
                    self.setWindowTitle("Upload Jobs")
                    self.resize(700, 400)

                    layout = QVBoxLayout(self)

                    self.table = QTableWidget(0, 6)
                    self.table.setHorizontalHeaderLabels(["ID", "Status", "Attempts", "Max", "File", "Last Error"])
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
                        self.table.setItem(r, 0, QTableWidgetItem(j.id))
                        self.table.setItem(r, 1, QTableWidgetItem(j.status))
                        self.table.setItem(r, 2, QTableWidgetItem(str(j.attempts)))
                        self.table.setItem(r, 3, QTableWidgetItem(str(j.max_attempts)))
                        self.table.setItem(r, 4, QTableWidgetItem(j.file_path))
                        self.table.setItem(r, 5, QTableWidgetItem(j.last_error or ""))

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
                        update_job_status(job_id, 'pending')
                    QMessageBox.information(self, "Queued", "Selected jobs marked for retry")
                    self.refresh()

                def cancel_selected(self) -> None:
                    ids = self._selected_job_ids()
                    if not ids:
                        QMessageBox.information(self, "No selection", "No jobs selected to cancel")
                        return
                    for job_id in ids:
                        update_job_status(job_id, 'cancelled')
                    QMessageBox.information(self, "Cancelled", "Selected jobs cancelled")
                    self.refresh()
