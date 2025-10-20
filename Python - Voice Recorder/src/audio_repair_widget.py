"""
Audio Repair Widget - Dedicated tool for repairing corrupted audio files

This widget provides:
- File/directory selection for audio files
- Batch audio file repair with progress tracking
- Corruption detection and validation
- Repair result summary with file size improvements
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QTextEdit,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QGroupBox,
    QFormLayout,
    QMessageBox,
    QListWidget,
)
from PySide6.QtGui import QColor

from voice_recorder.services.audio_repair_service import AudioRepairService  # type: ignore
from voice_recorder.core.logging_config import get_logger  # type: ignore
from voice_recorder.utilities import BaseWorkerThread, AudioFileSelector

logger = get_logger(__name__)


class AudioRepairWorkerThread(BaseWorkerThread):
    """Worker thread for batch audio repair operations"""

    progress_updated = Signal(int, str)  # percentage, message
    file_repaired = Signal(str, bool, str)  # file_path, success, message
    repair_complete = Signal(dict)  # summary stats

    def __init__(
        self,
        file_paths: List[str],
        output_dir: Optional[str] = None,
        use_suffix: bool = True,
        force: bool = True,
    ):
        super().__init__()
        self.file_paths = file_paths
        self.output_dir = output_dir
        self.use_suffix = use_suffix
        self.force = force

    def _repair_single_file(self, file_path: str) -> tuple[bool, str, int, int]:
        """Repair a single audio file and return metadata.
        
        Args:
            file_path: Path to the audio file to repair
            
        Returns:
            Tuple of (success: bool, message: str, size_before: int, size_after: int)
        """
        if not os.path.exists(file_path):
            return False, "File not found", 0, 0
        
        try:
            # Get file size before
            size_before = os.path.getsize(file_path)
            
            # Determine output path
            if self.output_dir:
                output_path = os.path.join(
                    self.output_dir,
                    Path(file_path).name.replace(".wav", "_repaired.wav"),
                )
            else:
                p = Path(file_path)
                output_path = str(p.parent / f"{p.stem}_repaired.wav")
            
            # Repair file
            result = AudioRepairService.repair_audio_file(
                input_path=file_path,
                output_path=output_path,
                force=self.force,
            )
            
            if result.get("success"):
                size_after = os.path.getsize(output_path)
                message = f"✓ Repaired: {Path(file_path).name}"
                return True, message, size_before, size_after
            else:
                error = result.get("error", "Unknown error")
                message = f"✗ Failed: {Path(file_path).name} - {error}"
                return False, message, size_before, 0
        
        except Exception as e:
            message = f"✗ Error: {Path(file_path).name} - {str(e)}"
            return False, message, 0, 0

    def safe_run(self):
        """Execute batch repair in worker thread"""
        total_files = len(self.file_paths)
        successful = 0
        failed = 0
        total_size_before = 0
        total_size_after = 0

        for idx, file_path in enumerate(self.file_paths):
            success, message, size_before, size_after = self._repair_single_file(file_path)
            
            # Update counters
            if success:
                successful += 1
                total_size_before += size_before
                total_size_after += size_after
            else:
                failed += 1
                total_size_before += size_before
            
            # Emit file result
            self.file_repaired.emit(file_path, success, message)
            
            # Update progress
            progress = int((idx + 1) / total_files * 100)
            self.progress_updated.emit(progress, f"Processing file {idx + 1} of {total_files}")

        # Emit completion summary
        summary = {
            "total": total_files,
            "successful": successful,
            "failed": failed,
            "size_before": total_size_before,
            "size_after": total_size_after,
        }
        self.repair_complete.emit(summary)


class AudioRepairWidget(QDialog):
    """Dedicated widget for audio file repair and validation"""

    def __init__(self, parent: Optional[Any] = None):
        super().__init__(parent)
        self.setWindowTitle("Audio Repair Tool")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)

        self.selected_files: List[str] = []
        self.repair_thread: Optional[AudioRepairWorkerThread] = None
        self.is_repairing = False

        self.init_ui()

    def init_ui(self):
        """Initialize the UI components"""
        main_layout = QVBoxLayout()

        # File selection section
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("Selected Files:"))
        self.file_button = QPushButton("Select Audio Files...")
        self.file_button.clicked.connect(self.select_files)
        file_layout.addWidget(self.file_button)

        self.dir_button = QPushButton("Select Directory...")
        self.dir_button.clicked.connect(self.select_directory)
        file_layout.addWidget(self.dir_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.clicked.connect(self.clear_files)
        file_layout.addWidget(self.clear_button)

        main_layout.addLayout(file_layout)

        # File list display
        self.file_list = QListWidget()
        self.file_list.setMaximumHeight(120)
        main_layout.addWidget(self.file_list)

        # Options section
        options_group = QGroupBox("Repair Options")
        options_layout = QFormLayout()

        # Output directory
        output_layout = QHBoxLayout()
        self.output_dir_label = QLabel("Same as source")
        output_layout.addWidget(self.output_dir_label)
        self.output_dir_button = QPushButton("Change Output Directory...")
        self.output_dir_button.clicked.connect(self.select_output_directory)
        output_layout.addWidget(self.output_dir_button)
        output_layout.addStretch()
        options_layout.addRow("Output Directory:", output_layout)

        # Repair mode
        self.force_repair_checkbox = QCheckBox(
            "Force repair (re-encode even if file seems valid)"
        )
        self.force_repair_checkbox.setChecked(True)
        options_layout.addRow("", self.force_repair_checkbox)

        # Sample rate
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["44100", "48000", "16000", "22050"])
        self.sample_rate_combo.setCurrentText("44100")
        options_layout.addRow("Sample Rate (Hz):", self.sample_rate_combo)

        # Channels
        self.channels_combo = QComboBox()
        self.channels_combo.addItems(["2 (Stereo)", "1 (Mono)"])
        options_layout.addRow("Channels:", self.channels_combo)

        options_group.setLayout(options_layout)
        main_layout.addWidget(options_group)

        # Progress section
        progress_group = QGroupBox("Repair Progress")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        progress_layout.addWidget(self.status_label)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMaximumHeight(150)
        progress_layout.addWidget(self.results_text)

        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)

        # Action buttons
        button_layout = QHBoxLayout()

        self.validate_button = QPushButton("Validate Files")
        self.validate_button.clicked.connect(self.validate_files)
        button_layout.addWidget(self.validate_button)

        self.repair_button = QPushButton("Repair Selected Files")
        self.repair_button.clicked.connect(self.repair_files)
        button_layout.addWidget(self.repair_button)

        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def select_files(self):
        """Open file dialog to select audio files"""
        files = AudioFileSelector.select_audio_files(self, "recordings/raw")
        if files:
            self.selected_files.extend(files)
            self.update_file_list()

    def select_directory(self):
        """Open directory dialog to select all audio files from a directory"""
        files = AudioFileSelector.select_audio_directory(self, "recordings/raw")
        if files:
            self.selected_files.extend(files)
            self.update_file_list()
            QMessageBox.information(
                self, "Files Found", f"Found {len(files)} audio files."
            )

    def select_output_directory(self):
        """Select custom output directory for repaired files"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory for Repaired Files"
        )

        if directory:
            self.output_dir_label.setText(directory)

    def clear_files(self):
        """Clear selected files"""
        self.selected_files.clear()
        self.update_file_list()
        self.results_text.clear()

    def update_file_list(self):
        """Update the file list display"""
        AudioFileSelector.populate_list_widget(self.file_list, self.selected_files)

    def validate_files(self):
        """Validate selected audio files for corruption"""
        if not self.selected_files:
            QMessageBox.warning(self, "No Files", "Please select audio files first.")
            return

        self.results_text.clear()
        self.results_text.setText("Validating audio files...\n")

        results = []
        for file_path in self.selected_files:
            try:
                result = AudioRepairService.validate_audio_file(file_path)
                status = "✓ Valid" if result.get("valid") else "✗ Invalid"
                message = result.get("message", "")
                results.append(f"{Path(file_path).name}: {status}")
                if message:
                    results.append(f"  {message}")
            except Exception as e:
                results.append(f"{Path(file_path).name}: Error - {str(e)}")

        self.results_text.setText("\n".join(results))

    def repair_files(self):
        """Start batch repair of selected files"""
        if not self.selected_files:
            QMessageBox.warning(self, "No Files", "Please select audio files first.")
            return

        if self.is_repairing:
            QMessageBox.warning(self, "Already Repairing", "Repair is already in progress.")
            return

        # Parse options
        output_dir = None
        if self.output_dir_label.text() != "Same as source":
            output_dir = self.output_dir_label.text()

        force_repair = self.force_repair_checkbox.isChecked()

        # Disable buttons during repair
        self.is_repairing = True
        self.file_button.setEnabled(False)
        self.dir_button.setEnabled(False)
        self.validate_button.setEnabled(False)
        self.repair_button.setEnabled(False)
        self.clear_button.setEnabled(False)

        # Setup progress UI
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.results_text.clear()
        self.results_text.setText("Starting repair...\n")

        # Create and start repair worker thread
        self.repair_thread = AudioRepairWorkerThread(
            file_paths=self.selected_files,
            output_dir=output_dir,
            force=force_repair,
        )

        self.repair_thread.progress_updated.connect(self.on_progress_updated)
        self.repair_thread.file_repaired.connect(self.on_file_repaired)
        self.repair_thread.repair_complete.connect(self.on_repair_complete)
        self.repair_thread.start()

    def on_progress_updated(self, progress: int, message: str):
        """Handle progress updates from repair thread"""
        self.progress_bar.setValue(progress)
        self.status_label.setText(message)

    def on_file_repaired(self, file_path: str, success: bool, message: str):
        """Handle individual file repair completion"""
        current_text = self.results_text.toPlainText()
        self.results_text.setText(current_text + message + "\n")

    def on_repair_complete(self, summary: Dict[str, Any]):
        """Handle completion of all repairs"""
        self.is_repairing = False
        self.progress_bar.setVisible(False)

        # Re-enable buttons
        self.file_button.setEnabled(True)
        self.dir_button.setEnabled(True)
        self.validate_button.setEnabled(True)
        self.repair_button.setEnabled(True)
        self.clear_button.setEnabled(True)

        # Show summary
        if "error" in summary:
            current_text = self.results_text.toPlainText()
            self.results_text.setText(
                current_text
                + f"\n\nError: {summary['error']}"
            )
            QMessageBox.critical(self, "Repair Failed", summary["error"])
        else:
            successful = summary.get("successful", 0)
            failed = summary.get("failed", 0)
            size_before = summary.get("size_before", 0)
            size_after = summary.get("size_after", 0)
            size_saved = size_before - size_after

            summary_text = f"\n\n{'='*50}\nRepair Summary\n{'='*50}\n"
            summary_text += f"Files processed: {summary.get('total', 0)}\n"
            summary_text += f"Successfully repaired: {successful}\n"
            summary_text += f"Failed: {failed}\n"

            if size_before > 0:
                summary_text += f"Size before: {size_before / 1024 / 1024:.2f} MB\n"
                summary_text += f"Size after: {size_after / 1024 / 1024:.2f} MB\n"
                summary_text += f"Space saved: {size_saved / 1024 / 1024:.2f} MB\n"

            current_text = self.results_text.toPlainText()
            self.results_text.setText(current_text + summary_text)

            QMessageBox.information(
                self,
                "Repair Complete",
                f"Repair complete!\n\n"
                f"Successfully repaired: {successful}\n"
                f"Failed: {failed}",
            )
