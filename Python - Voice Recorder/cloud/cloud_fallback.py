import os

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CloudFallbackWidget(QWidget):
    """Small widget that explains missing cloud deps and exposes actions."""

    def __init__(self, parent=None, editor_ref=None):
        super().__init__(parent)
        self.editor_ref = editor_ref
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        label = QLabel("Cloud features are not available in this environment.")
        label.setStyleSheet("color: #7f8c8d;")
        layout.addWidget(label)

        hint = QLabel(
            "Install dev/cloud requirements and add a Google client_secrets.json to enable sign-in."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        retry_btn = QPushButton("🔁 Retry Init")
        retry_btn.clicked.connect(self.on_retry)
        btn_row.addWidget(retry_btn)

        req_btn = QPushButton("📦 Open requirements_cloud.txt")
        req_btn.clicked.connect(self.on_open_requirements)
        btn_row.addWidget(req_btn)

        cs_btn = QPushButton("🔑 Open client_secrets.json")
        cs_btn.clicked.connect(self.on_open_client_secrets)
        btn_row.addWidget(cs_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)
        self.setLayout(layout)

    def on_retry(self):
        try:
            # Attempt to initialize cloud components again
            if self.editor_ref is not None:
                self.editor_ref.init_cloud_components(self.editor_ref.feature_gate)
                # If initialization created cloud_ui, replace fallback
                self.editor_ref._replace_fallback_with_cloud()
        except Exception as e:
            QMessageBox.warning(
                self, "Retry Failed", f"Failed to initialize cloud features: {e}"
            )

    def on_open_requirements(self):
        try:
            path = os.path.join(
                os.path.dirname(__file__), "..", "requirements_cloud.txt"
            )
            abs_path = os.path.abspath(path)
            if os.path.exists(abs_path):
                QDesktopServices.openUrl(QUrl.fromLocalFile(abs_path))
            else:
                QMessageBox.information(
                    self, "Not Found", f"Requirements file not found: {abs_path}"
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open requirements file: {e}")

    def on_open_client_secrets(self):
        try:
            app_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            cs = os.path.join(app_dir, "config", "client_secrets.json")
            if os.path.exists(cs):
                QDesktopServices.openUrl(QUrl.fromLocalFile(cs))
            else:
                QMessageBox.information(
                    self,
                    "Not Found",
                    f"client_secrets.json not found at: {cs}\n\nPlace your OAuth client config there or set VRP_CLIENT_SECRETS env var.",
                )
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open client_secrets: {e}")
