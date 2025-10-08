# enhanced_editor.py
# Enhanced audio editor with asynchronous operations, performance improvements, and cloud integration

from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QFileDialog,
    QVBoxLayout, QHBoxLayout, QLineEdit, QMessageBox,
    QProgressBar, QTabWidget, QComboBox
)
from waveform_viewer import WaveformViewer
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl
from PySide6.QtGui import QCloseEvent
from pydub import AudioSegment  # type: ignore
import os
from typing import Optional, Any  # Union not used
from config_manager import config_manager

from audio_processing import (
    AudioLoaderThread, 
    AudioTrimProcessor  # type: ignore
)
from audio_recorder import AudioRecorderManager
from models.database import SessionLocal
from models.recording import Recording
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'utilities'))
from version import APP_NAME, UIConstants  # type: ignore
from core.logging_config import get_logger
from settings_ui import SettingsDialog

# Setup logging for this module
logger = get_logger(__name__)

# Cloud integration (optional import to handle missing dependencies gracefully)
_cloud_available = False
try:
    from cloud.auth_manager import GoogleAuthManager
    from cloud.drive_manager import GoogleDriveManager
    from cloud.feature_gate import FeatureGate
    from cloud.cloud_ui import CloudUI
    _cloud_available = True
except ImportError as e:
    print(f"ℹ️ Cloud features not available: {e}")
    print("💡 Install Google API packages to enable cloud features:")
    print("   pip install -r requirements_cloud.txt")
    # Define placeholder types for type checking
    GoogleAuthManager = None  # type: ignore
    GoogleDriveManager = None  # type: ignore
    FeatureGate = None  # type: ignore
    CloudUI = None  # type: ignore


class EnhancedAudioEditor(QWidget):
    """Enhanced audio editor with asynchronous operations, improved performance, and cloud integration"""
    
    def __init__(self, feature_gate: Optional[Any] = None, use_keyring: Optional[bool] = None) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - Professional Audio Editing & Cloud Storage")
        self.setMinimumWidth(600)
        self.setMinimumHeight(600)

        # Audio-related attributes
        self.audio_file: Optional[str] = None
        self.audio_segment: Optional[AudioSegment] = None

        # Waveform viewer
        self.waveform_viewer: Optional[WaveformViewer] = None

        # Audio recorder
        self.audio_recorder = AudioRecorderManager()  # type: ignore
        self.is_recording: bool = False

        # Media player setup
        self.player = QMediaPlayer()  # type: ignore
        self.output = QAudioOutput()  # type: ignore
        self.player.setAudioOutput(self.output)

        # Async processing components
        self.loader_thread: Optional[Any] = None
        self.trim_processor: Optional[Any] = None
        self.progress_dialog: Optional[Any] = None

        # UI state
        self.is_loading: bool = False
        self.is_processing: bool = False

        # Cloud components (optional)
        self.auth_manager: Optional[Any] = None
        self.drive_manager: Optional[Any] = None
        self.feature_gate: Optional[Any] = None
        self.cloud_ui: Optional[Any] = None

        if _cloud_available:
            # Determine effective keyring preference: explicit parameter overrides global config
            effective_use_keyring = use_keyring if use_keyring is not None else config_manager.prefers_keyring()
            self.init_cloud_components(feature_gate, use_keyring=effective_use_keyring)

        self.init_ui()
        self.connect_signals()
        self.setup_audio_recorder()
    
    def init_cloud_components(self, feature_gate: Optional[Any] = None, use_keyring: Optional[bool] = None) -> None:
        """Initialize cloud components if available"""
        try:
            if GoogleAuthManager is not None and GoogleDriveManager is not None and FeatureGate is not None and CloudUI is not None:
                # Respect caller-specified use_keyring; default to config_manager preference
                self.auth_manager = GoogleAuthManager(use_keyring=(use_keyring if use_keyring is not None else config_manager.prefers_keyring()))
                self.drive_manager = GoogleDriveManager(self.auth_manager)
                self.feature_gate = feature_gate or FeatureGate(self.auth_manager)
                self.cloud_ui = CloudUI(self.auth_manager, self.drive_manager, self.feature_gate)
                print("✅ Cloud features initialized")
            else:
                print("ℹ️ Cloud modules not available; cloud features disabled.")
        except Exception as e:
            print(f"❌ Failed to initialize cloud features: {e}")

    def init_ui(self) -> None:
        """Initialize the user interface with tabs for cloud features"""
        main_layout = QVBoxLayout()

        # Title and status section
        title_label = QLabel("🎵 Voice Recorder Pro - Professional Edition")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; margin: 10px;")

        # Preferences button (small)
        pref_btn = QPushButton("⚙ Preferences")
        pref_btn.setFixedSize(120, 28)
        pref_btn.clicked.connect(self.open_preferences)

        self.status_label = QLabel("Ready to load audio file...")
        self.status_label.setStyleSheet("color: #7f8c8d; margin: 5px;")

        # Title row with preferences button on the right
        title_row = QHBoxLayout()
        title_row.addWidget(title_label)
        title_row.addStretch()
        title_row.addWidget(pref_btn)
        main_layout.addLayout(title_row)
        main_layout.addWidget(self.status_label)

        # Create tab widget if cloud features available, otherwise single view
        if _cloud_available and self.cloud_ui:
            self.create_tabbed_interface(main_layout)
        else:
            self.create_single_interface(main_layout)

        self.setLayout(main_layout)

    def open_preferences(self) -> None:
        """Open the settings dialog and apply preferences.

        On accept the dialog persists the setting via config_manager.set_use_keyring().
        We then re-initialize cloud components with the updated preference so it takes
        effect immediately without restarting the app.
        """
        dialog = SettingsDialog(self)
        result = dialog.exec()
        if result:
            try:
                effective_use_keyring = config_manager.prefers_keyring()
                # Re-init cloud components with the updated preference
                if _cloud_available:
                    self.init_cloud_components(self.feature_gate, use_keyring=effective_use_keyring)
                self.status_label.setText("Preferences saved.")
            except Exception as e:
                logger.exception("Failed to apply preferences: %s", e)
                QMessageBox.warning(self, "Preferences", "Saved preferences but failed to reinitialize cloud features.")
    
    def create_tabbed_interface(self, main_layout: QVBoxLayout) -> None:
        """Create tabbed interface with cloud features"""
        tab_widget = QTabWidget()
        
        # Main audio tab
        audio_tab = QWidget()
        audio_layout = QVBoxLayout()
        
        # File operations section
        audio_layout.addWidget(self.create_file_section())
        
        # Recording section  
        audio_layout.addWidget(self.create_recording_section())
        
        # Playback controls section
        audio_layout.addWidget(self.create_playback_section())
        
        # Editing section
        audio_layout.addWidget(self.create_editing_section())
        
        # Progress section
        audio_layout.addWidget(self.create_progress_section())
        
        audio_layout.addStretch()
        audio_tab.setLayout(audio_layout)
        
        # Add tabs
        tab_widget.addTab(audio_tab, "🎵 Audio Editor")
        if self.cloud_ui:
            tab_widget.addTab(self.cloud_ui, "☁️ Cloud Features")
        
        main_layout.addWidget(tab_widget)
    
    def create_single_interface(self, main_layout: QVBoxLayout) -> None:
        """Create single interface without cloud features"""
        """Create single interface without cloud features"""
        # File operations section
        main_layout.addWidget(self.create_file_section())
        
        # Recording section
        main_layout.addWidget(self.create_recording_section())
        
        # Playback controls section
        main_layout.addWidget(self.create_playback_section())
        
        # Editing section
        main_layout.addWidget(self.create_editing_section())
        
        # Progress section
        main_layout.addWidget(self.create_progress_section())
        
        # Cloud availability notice
        if not _cloud_available:
            notice_layout = QHBoxLayout()
            notice_label = QLabel("💡 Install Google API packages for cloud features:")
            notice_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
            install_label = QLabel("pip install -r requirements_cloud.txt")
            install_label.setStyleSheet("color: #3498db; font-family: monospace;")
            notice_layout.addWidget(notice_label)
            notice_layout.addWidget(install_label)
            notice_layout.addStretch()
            
            notice_widget = QWidget()
            notice_widget.setLayout(notice_layout)
            main_layout.addWidget(notice_widget)
        
        main_layout.addStretch()  # Push everything to top

    def create_file_section(self) -> QWidget:
        """Create file operations section"""
        section = QWidget()
        layout = QVBoxLayout()

        # Load button
        self.load_button = QPushButton(UIConstants.LOAD_AUDIO_FILE)
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 10px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.load_button.clicked.connect(self.load_audio_async)

        # File info label
        self.file_info_label = QLabel(UIConstants.NO_FILE_LOADED)
        self.file_info_label.setStyleSheet("color: #34495e; margin: 5px;")

        layout.addWidget(self.load_button)
        layout.addWidget(self.file_info_label)

        # Waveform viewer placeholder
        self.waveform_viewer = None
        self.waveform_container = QWidget()
        self.waveform_layout = QVBoxLayout()
        self.waveform_container.setLayout(self.waveform_layout)
        layout.addWidget(self.waveform_container)

        section.setLayout(layout)
        return section

    def create_recording_section(self) -> QWidget:
        """Create audio recording section"""
        section = QWidget()
        layout = QVBoxLayout()
        
        # Recording title
        record_label = QLabel("🎤 Audio Recording:")
        record_label.setStyleSheet("font-weight: bold; color: #c0392b; margin-top: 10px;")
        
        # Recording controls layout
        record_layout = QHBoxLayout()
        
        # Record button
        self.record_button = QPushButton(UIConstants.START_RECORDING)
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.record_button.clicked.connect(self.toggle_recording)
        
        # Recording status and level display
        self.recording_status = QLabel(UIConstants.READY_TO_RECORD)
        self.recording_status.setStyleSheet("color: #34495e; margin: 5px;")
        
        self.recording_duration = QLabel(UIConstants.TIME_FORMAT_ZERO)
        self.recording_duration.setStyleSheet("font-family: monospace; font-size: 14px; color: #2c3e50;")
        
        # Audio level indicator (simple text for now)
        self.audio_level = QLabel(UIConstants.AUDIO_LEVEL_EMPTY)
        self.audio_level.setStyleSheet("color: #7f8c8d; font-size: 10px;")
        
        record_layout.addWidget(self.record_button)
        record_layout.addWidget(QLabel("Duration:"))
        record_layout.addWidget(self.recording_duration)
        record_layout.addWidget(self.audio_level)
        record_layout.addStretch()

        layout.addWidget(record_label)
        layout.addWidget(self.recording_status)
        layout.addLayout(record_layout)

        # Device selection row
        device_layout = QHBoxLayout()
        device_layout.addWidget(QLabel("Input Device:"))
        self.device_selector = QComboBox()
        self.device_selector.setEditable(False)
        self.device_selector.currentIndexChanged.connect(self.on_device_selected)
        device_layout.addWidget(self.device_selector)

        self.refresh_devices_btn = QPushButton("Refresh Devices")
        self.refresh_devices_btn.clicked.connect(self.populate_device_list)
        device_layout.addWidget(self.refresh_devices_btn)
        device_layout.addStretch()

        layout.addLayout(device_layout)

        section.setLayout(layout)
        return section

    def create_playback_section(self) -> QWidget:
        """Create playback controls section"""
        section = QWidget()
        layout = QHBoxLayout()
        
        self.play_button = QPushButton("▶️ Play")
        self.pause_button = QPushButton("⏸️ Pause")
        self.stop_button = QPushButton("⏹️ Stop")
        
        # Style playback buttons
        button_style = """
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
                margin: 2px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """
        
        for button in [self.play_button, self.pause_button, self.stop_button]:
            button.setStyleSheet(button_style)
            button.setEnabled(False)  # Disabled until file is loaded
        
        self.play_button.clicked.connect(self.play_audio)
        self.pause_button.clicked.connect(self.pause_audio)
        self.stop_button.clicked.connect(self.stop_audio)
        
        layout.addWidget(self.play_button)
        layout.addWidget(self.pause_button)
        layout.addWidget(self.stop_button)
        layout.addStretch()
        
        section.setLayout(layout)
        return section

    def create_editing_section(self) -> QWidget:
        """Create audio editing section"""
        section = QWidget()
        layout = QVBoxLayout()
        
        # Trim controls
        trim_label = QLabel("✂️ Trim Audio:")
        trim_label.setStyleSheet("font-weight: bold; color: #2c3e50; margin-top: 10px;")
        
        trim_layout = QHBoxLayout()
        
        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("Start time (seconds)")
        self.start_input.setStyleSheet("padding: 8px; border: 2px solid #bdc3c7; border-radius: 4px;")
        
        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("End time (seconds)")
        self.end_input.setStyleSheet("padding: 8px; border: 2px solid #bdc3c7; border-radius: 4px;")
        
        self.trim_button = QPushButton(UIConstants.TRIM_AND_SAVE)
        self.trim_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.trim_button.setEnabled(False)
        self.trim_button.clicked.connect(self.trim_audio_async)
        
        trim_layout.addWidget(QLabel("From:"))
        trim_layout.addWidget(self.start_input)
        trim_layout.addWidget(QLabel("To:"))
        trim_layout.addWidget(self.end_input)
        trim_layout.addWidget(self.trim_button)
        
        layout.addWidget(trim_label)
        layout.addWidget(QWidget())  # Spacer
        layout.addLayout(trim_layout)
        
        section.setLayout(layout)
        return section

    def create_progress_section(self) -> QWidget:
        """Create progress tracking section"""
        section = QWidget()
        layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        self.progress_label.setStyleSheet("color: #7f8c8d; text-align: center;")
        
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.progress_label)
        
        section.setLayout(layout)
        return section

    def connect_signals(self):
        """Connect various signals for UI updates"""
        # Connect input validation - only if UI elements exist
        if hasattr(self, 'start_input') and hasattr(self, 'end_input'):
            self.start_input.textChanged.connect(self.validate_trim_inputs)
            self.end_input.textChanged.connect(self.validate_trim_inputs)
        else:
            print("⚠️ Warning: UI elements not yet created for signal connections")

    def load_audio_async(self):
        """Load audio file asynchronously to prevent UI blocking"""
        if self.is_loading:
            return
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Audio File", 
            "recordings/raw", 
            "Audio Files (*.wav *.mp3 *.ogg);;WAV Files (*.wav);;All Files (*)"
        )
        
        if not file_path:
            return
            
        # Start async loading
        self.is_loading = True
        self.update_ui_for_loading(True)
        
        # Create and start loader thread
        self.loader_thread = AudioLoaderThread(file_path)
        self.loader_thread.audio_loaded.connect(self.on_audio_loaded)
        self.loader_thread.error_occurred.connect(self.on_load_error)
        self.loader_thread.progress_updated.connect(self.on_load_progress)
        self.loader_thread.finished.connect(self.on_load_finished)
        
        # Show progress
        self.show_progress("Loading Audio File")
        
        self.loader_thread.start()

    def trim_audio_async(self):
        """Perform audio trimming asynchronously"""
        if not self.audio_segment or self.is_processing:  # type: ignore
            return

        # Validate inputs
        if not self.validate_trim_inputs():
            return

        try:
            start_ms = int(float(self.start_input.text()) * 1000)
            end_ms = int(float(self.end_input.text()) * 1000)

            # Get save location
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Trimmed Audio",
                "recordings/edited/trimmed.wav",
                "WAV Files (*.wav);;MP3 Files (*.mp3);;All Files (*)"
            )

            if not save_path:
                return

            # Start async trimming
            self.is_processing = True
            self.update_ui_for_processing(True)

            self.trim_processor = AudioTrimProcessor(
                self.audio_segment, start_ms, end_ms, save_path)  # type: ignore

            self.trim_processor.progress_updated.connect(self.on_trim_progress)
            self.trim_processor.trim_completed.connect(self.on_trim_completed)
            self.trim_processor.error_occurred.connect(self.on_trim_error)
            self.trim_processor.finished.connect(self.on_trim_finished)

            # Show progress
            self.show_progress("Trimming Audio")

            self.trim_processor.start()
            
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter valid numeric values for start and end times.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start trim operation: {e}")

    def show_progress(self, operation_name: str):
        """Show progress bar and label"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(True)
        self.progress_label.setText(f"{operation_name}...")

    def hide_progress(self):
        """Hide progress indicators"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

    def update_ui_for_loading(self, loading: bool) -> None:
        """Update UI state during loading"""
        self.load_button.setEnabled(not loading)
        if loading:
            self.load_button.setText(UIConstants.LOADING_AUDIO)
            self.status_label.setText("Loading audio file...")
        else:
            self.load_button.setText(UIConstants.LOAD_AUDIO_FILE)

    def update_ui_for_processing(self, processing: bool):
        """Update UI state during processing"""
        self.trim_button.setEnabled(not processing)
        for button in [self.play_button, self.pause_button, self.stop_button]:
            button.setEnabled(not processing and self.audio_segment is not None)  # type: ignore

    def validate_trim_inputs(self) -> bool:
        """Validate trim input fields"""
        if not self.audio_segment:  # type: ignore
            self.trim_button.setEnabled(False)
            return False

        try:
            start_text = self.start_input.text().strip()
            end_text = self.end_input.text().strip()

            if not start_text or not end_text:
                self.trim_button.setEnabled(False)
                return False

            start_ms = float(start_text) * 1000
            end_ms = float(end_text) * 1000

            duration_ms = len(self.audio_segment)  # type: ignore

            # Validate range
            valid = (0 <= start_ms < end_ms <= duration_ms)
            self.trim_button.setEnabled(valid and not self.is_processing)

            return valid

        except ValueError:
            self.trim_button.setEnabled(False)
            return False

    # Event handlers for async operations
    def on_audio_loaded(self, audio_segment: AudioSegment, file_path: str):
        """Handle successful audio loading"""
        self.audio_file = file_path
        self.audio_segment = audio_segment

        # Update UI
        filename = os.path.basename(file_path)
        duration = len(audio_segment) / 1000  # Convert to seconds
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB

        self.file_info_label.setText(
            f"📄 {filename} | ⏱️ {duration:.1f}s | 💾 {file_size:.1f}MB"
        )
        self.status_label.setText("Audio file loaded successfully!")

        # Enable playback controls
        for button in [self.play_button, self.pause_button, self.stop_button]:
            button.setEnabled(True)

        # Setup media player
        self.player.setSource(QUrl.fromLocalFile(file_path))

        # Validate trim inputs
        self.validate_trim_inputs()

        # Show waveform
        self.show_waveform(file_path)

    def show_waveform(self, file_path: str):
        """Display waveform of loaded audio file."""
        # Remove previous waveform if exists
        if self.waveform_viewer:
            self.waveform_layout.removeWidget(self.waveform_viewer)
            self.waveform_viewer.deleteLater()
            self.waveform_viewer = None
        self.waveform_viewer = WaveformViewer(file_path)
        self.waveform_layout.addWidget(self.waveform_viewer)

    def on_load_error(self, error_message: str):
        """Handle audio loading errors"""
        QMessageBox.critical(self, "Loading Error", f"Failed to load audio file:\n{error_message}")
        self.status_label.setText("Failed to load audio file.")

    def on_load_progress(self, value: int, message: str):
        """Handle loading progress updates"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def on_load_finished(self):
        """Handle completion of loading operation"""
        self.is_loading = False
        self.update_ui_for_loading(False)
        self.hide_progress()

    def on_trim_completed(self, output_path: str):
        """Handle successful trim completion"""
        filename = os.path.basename(output_path)
        self.status_label.setText(f"✅ Trimmed audio saved: {filename}")
        QMessageBox.information(self, "Success", f"Audio trimmed successfully!\nSaved to: {filename}")

    def on_trim_error(self, error_message: str):
        """Handle trim operation errors"""
        QMessageBox.critical(self, "Trim Error", f"Failed to trim audio:\n{error_message}")
        self.status_label.setText("Trim operation failed.")

    def on_trim_progress(self, value: int, message: str):
        """Handle trim progress updates"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)

    def on_trim_finished(self):
        """Handle completion of trim operation"""
        self.is_processing = False
        self.update_ui_for_processing(False)
        self.hide_progress()

    # Playback control methods
    def play_audio(self):
        """Play the loaded audio"""
        if self.audio_file:
            self.player.play()
            self.status_label.setText("▶️ Playing audio...")

    def pause_audio(self):
        """Pause audio playback"""
        self.player.pause()
        self.status_label.setText("⏸️ Audio paused.")

    def stop_audio(self):
        """Stop audio playback"""
        self.player.stop()
        self.status_label.setText("⏹️ Audio stopped.")

    def closeEvent(self, event: QCloseEvent):
        """Handle window close event"""
        # Clean up any running threads
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.terminate()
            self.loader_thread.wait()
            
        if self.trim_processor and self.trim_processor.isRunning():
            self.trim_processor.terminate()
            self.trim_processor.wait()
            
        event.accept()

    def setup_audio_recorder(self):
        """Setup audio recorder with signal connections"""
        # Connect audio recorder signals
        self.audio_recorder.recording_started.connect(self.on_recording_started)  # type: ignore
        self.audio_recorder.recording_stopped.connect(self.on_recording_stopped)  # type: ignore
        self.audio_recorder.recording_progress.connect(self.on_recording_progress)  # type: ignore
        self.audio_recorder.recording_error.connect(self.on_recording_error)  # type: ignore
        self.audio_recorder.device_status_changed.connect(self.on_device_status_changed)  # type: ignore

        # Populate device list for UI and select default
        try:
            self.populate_device_list()
        except Exception:
            logger.exception("Failed to populate device list")

    def toggle_recording(self):
        """Toggle recording start/stop"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start audio recording"""
        if self.is_recording:
            return

        # Start recording with auto-generated filename
        # Use manager-selected device by default (UI set via device_selector)
        success = self.audio_recorder.start_recording()  # type: ignore
        if not success:
            self.recording_status.setText("❌ Failed to start recording")
        else:
            # Start level monitoring for visual feedback (uses selected device)
            try:
                self.audio_recorder.start_level_monitoring()
            except Exception:
                logger.exception("Failed to start level monitoring")

    def stop_recording(self):
        """Stop audio recording"""
        if not self.is_recording:
            return
        self.audio_recorder.stop_recording()
        try:
            self.audio_recorder.stop_level_monitoring()
        except Exception:
            logger.exception("Failed to stop level monitoring")

    def populate_device_list(self) -> None:
        """Fill the device selector combo box with available input devices."""
        try:
            devices = self.audio_recorder.get_available_devices()
            self.device_selector.blockSignals(True)
            self.device_selector.clear()
            self.device_selector.addItem("Default")
            for dev in devices:
                self.device_selector.addItem(f"{dev['index']}: {dev['name']}", dev['index'])
            self.device_selector.blockSignals(False)
            # If manager has a selected device, set it
            sel = self.audio_recorder.get_selected_device()
            if sel is not None:
                # Find index in combo box
                for i in range(self.device_selector.count()):
                    data = self.device_selector.itemData(i)
                    if data == sel:
                        self.device_selector.setCurrentIndex(i)
                        break
        except Exception as e:
            logger.exception("Error populating device list: %s", e)

    def on_device_selected(self, index: int) -> None:
        """Handle user selecting a device in the combo box."""
        try:
            data = self.device_selector.itemData(index)
            if data is None:
                # Default selected
                self.audio_recorder.set_selected_device(None)
            else:
                self.audio_recorder.set_selected_device(data)
        except Exception:
            logger.exception("Error handling device selection")

    def on_recording_started(self) -> None:
        """Handle recording start"""
        self.is_recording = True
        self.record_button.setText(UIConstants.STOP_RECORDING)
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2c3e50;
            }
        """)
        self.recording_status.setText(UIConstants.RECORDING_IN_PROGRESS)
        self.status_label.setText("🎤 Recording audio...")

    def on_recording_stopped(self, file_path: str, duration: float) -> None:
        """Handle recording completion with optional cloud upload"""
        self.is_recording = False
        self.record_button.setText(UIConstants.START_RECORDING)
        self.record_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        
        filename = os.path.basename(file_path)
        self.recording_status.setText(f"✅ Recording saved: {filename}")
        self.status_label.setText(f"✅ Recording completed: {duration:.1f}s")
        self.recording_duration.setText(UIConstants.TIME_FORMAT_ZERO)
        self.audio_level.setText(UIConstants.AUDIO_LEVEL_EMPTY)
        
        # Save to database
        self.save_recording_metadata(file_path, duration)
        
        # Automatically load the recorded file for editing
        self.load_recorded_file(file_path)
        
        # Cloud integration: Set current recording for quick upload
        if _cloud_available and self.cloud_ui:
            self.cloud_ui.set_current_recording(file_path)  # type: ignore
            self.status_label.setText(f"✅ Recording completed: {duration:.1f}s | ☁️ Ready for cloud upload")

    def on_recording_progress(self, duration: float, audio_level: float):
        """Handle recording progress updates"""
        # Update duration display
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        self.recording_duration.setText(f"{minutes:02d}:{seconds:02d}")
        
        # Update audio level (simple visualization)
        level_percent = min(100, audio_level * 1000)  # Scale for display
        level_bars = "█" * int(level_percent / 10)
        self.audio_level.setText(f"{UIConstants.AUDIO_LEVEL_PREFIX}{level_bars}")

    def on_recording_error(self, error_message: str) -> None:
        """Handle recording errors"""
        self.is_recording = False
        self.record_button.setText(UIConstants.START_RECORDING)
        self.recording_status.setText(f"❌ Recording error: {error_message}")
        self.status_label.setText("Recording failed.")
        
        # Reset UI state
        self.recording_duration.setText(UIConstants.TIME_FORMAT_ZERO)
        self.audio_level.setText(UIConstants.AUDIO_LEVEL_EMPTY)

    def on_device_status_changed(self, devices_available: bool) -> None:
        """Handle audio device status changes"""
        self.record_button.setEnabled(devices_available)
        if not devices_available:
            self.recording_status.setText(UIConstants.NO_DEVICES_FOUND)
        else:
            self.recording_status.setText(UIConstants.READY_TO_RECORD)

    def save_recording_metadata(self, file_path: str, duration: float):
        """Save recording metadata to database"""
        try:
            filename = os.path.basename(file_path)
            with SessionLocal() as db:
                recording = Recording(
                    filename=filename,
                    stored_filename=filename,  # Fix: Add the required stored_filename
                    duration=duration,
                    status="active"
                )
                db.add(recording)
                db.commit()
                print(f"✅ Saved recording metadata: {recording.filename}")
        except Exception as e:
            print(f"❌ Failed to save recording metadata: {e}")

    def load_recorded_file(self, file_path: str) -> None:
        """Automatically load recorded file for editing"""
        self.audio_file = file_path
        
        try:
            # Load audio segment
            self.audio_segment = AudioSegment.from_wav(file_path)  # type: ignore
            
            # Update UI
            filename = os.path.basename(file_path)
            if self.audio_segment is not None:  # type: ignore
                duration = len(self.audio_segment) / 1000  # type: ignore
                file_size = os.path.getsize(file_path) / (1024 * 1024)
                self.file_info_label.setText(
                    f"📄 {filename} | ⏱️ {duration:.1f}s | 💾 {file_size:.1f}MB"
                )
                
                # Enable playback controls
                for button in [self.play_button, self.pause_button, self.stop_button]:
                    button.setEnabled(True)
                    
                # Setup media player
                self.player.setSource(QUrl.fromLocalFile(file_path))
                
                # Validate trim inputs
                self.validate_trim_inputs()
            
        except Exception as e:
            print(f"Failed to load recorded file: {e}")
