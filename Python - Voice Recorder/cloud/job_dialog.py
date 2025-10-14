from __future__ import annotations

from typing import List, Optional, TYPE_CHECKING, Any

# Guard PySide6 imports so tests can import this module in headless CI
_HAS_QT = True
try:
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
        QPushButton, QHBoxLayout, QMessageBox,
    )
    from PySide6.QtCore import Qt
except Exception:  # pragma: no cover - environment dependent
    _HAS_QT = False

    # Minimal fallbacks so importing this module doesn't fail in tests
    class QDialog:  # type: ignore
        pass

    class QVBoxLayout:  # type: ignore
        pass

    class QTableWidget:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

    class QTableWidgetItem:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

    class QPushButton:  # type: ignore
        def __init__(self, *args, **kwargs):
            pass

    class QHBoxLayout:  # type: ignore
        pass

    class QMessageBox:  # type: ignore
        StandardButton = type("_SB", (), {})
        @staticmethod
        def information(*args, **kwargs):
            pass

    class Qt:  # type: ignore
        AlignmentFlag = type("_AF", (), {"AlignCenter": 0})


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

        # Defer initial refresh to allow test setups to stub DB before first load
        try:
            self.refresh()
        except Exception:
            # Best-effort: ignore refresh errors at construction time
            pass

    def refresh(self) -> None:
        # Lazy-import DB helpers so importing this module doesn't touch SQLite or app models
        try:
            from .job_queue_sql import get_all_jobs
        except Exception:
            # If job DB helpers aren't available, show empty list
            jobs = []
        else:
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
        try:
            from .job_queue_sql import update_job_status
        except Exception:
            update_job_status = None

        for job_id in ids:
            try:
                if update_job_status:
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
        try:
            from .job_queue_sql import set_job_cancel_requested, update_job_status
        except Exception:
            set_job_cancel_requested = None
            update_job_status = None

        for job_id in ids:
            try:
                # Ask the running worker to cancel gracefully; also mark status as cancelled
                if set_job_cancel_requested:
                    set_job_cancel_requested(job_id)
                if update_job_status:
                    update_job_status(job_id, 'cancelled')
            except Exception:
                pass
        QMessageBox.information(self, "Cancelled", "Selected jobs cancelled (requested)")
        self.refresh()

