from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox
from voice_recorder.config_manager import config_manager


class SettingsDialog(QDialog):
    """Simple settings dialog to toggle keyring usage and persist to .env"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.resize(420, 140)

        layout = QVBoxLayout()

        # Keyring toggle
        self.keyring_checkbox = QCheckBox("Use OS Keyring for storing credentials")
        self.keyring_checkbox.setChecked(bool(config_manager.prefers_keyring()))
        layout.addWidget(self.keyring_checkbox)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

        self.save_btn.clicked.connect(self.on_save)
        self.cancel_btn.clicked.connect(self.reject)

    def on_save(self):
        enabled = bool(self.keyring_checkbox.isChecked())
        try:
            config_manager.set_use_keyring(enabled)
        except Exception:
            # Best-effort; ignore failures here but don't crash UI
            pass
        self.accept()
