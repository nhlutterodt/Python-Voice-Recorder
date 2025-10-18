# enhanced_editor.py
# Enhanced audio editor with asynchronous operations, performance improvements, and cloud integration

import os
from typing import TYPE_CHECKING, Any, Optional, Tuple, cast

from PySide6.QtCore import QUrl
from PySide6.QtGui import QCloseEvent
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from voice_recorder.audio_processing import (  # type: ignore
    AudioLoaderThread,
    AudioTrimProcessor,
)
from voice_recorder.audio_recorder import AudioRecorderManager
from voice_recorder.config_manager import config_manager
from voice_recorder.waveform_viewer import WaveformViewer

if TYPE_CHECKING:
    # For type-checkers only; import AudioSegment for annotations and
    # keep runtime import-free so optional/native deps don't crash import.
    from pydub import AudioSegment  # type: ignore

    # At runtime, DB/models are imported lazily inside functions to avoid
    # SQLAlchemy mapped-class registration during module import.

from voice_recorder.core.logging_config import get_logger
from voice_recorder.scripts.utilities.version import (  # type: ignore
    APP_NAME,
    UIConstants,
)
from voice_recorder.settings_ui import SettingsDialog

# Setup logging for this module
logger = get_logger(__name__)

# Cloud integration (optional import to handle missing dependencies gracefully)
_cloud_available = False
try:
    from voice_recorder.cloud.auth_manager import GoogleAuthManager
    from voice_recorder.cloud.cloud_ui import CloudUI
    from voice_recorder.cloud.drive_manager import GoogleDriveManager
    from voice_recorder.cloud.feature_gate import FeatureGate

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

    def __init__(
        self, feature_gate: Optional[Any] = None, use_keyring: Optional[bool] = None
    ) -> None:
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - Professional Audio Editing & Cloud Storage")
        self.setMinimumWidth(600)
        self.setMinimumHeight(600)
        # Audio-related attributes
        self.audio_file: Optional[str] = None
        # Use a forward-reference for runtime safety (AudioSegment is
        # only imported inside functions at runtime when needed)
        self.audio_segment: Optional["AudioSegment"] = None

        # Waveform viewer
        self.waveform_viewer: Optional[WaveformViewer] = None
        self.waveform_container: Optional[QWidget] = None
        self.waveform_layout: Optional[QVBoxLayout] = None

        # UI widget placeholders (declare here so type-checkers know these attributes exist)
        self.load_button: Any = None
        self.file_info_label: Any = None
        self.progress_bar: Any = None
        self.progress_label: Any = None
        self.play_button: Any = None
        self.pause_button: Any = None
        self.stop_button: Any = None
        self.trim_button: Any = None
        self.start_input: Any = None
        self.end_input: Any = None

        # Audio recorder
        self.audio_recorder = AudioRecorderManager()  # type: ignore
        self.is_recording: bool = False

        # Media player setup
        self.player = QMediaPlayer()  # type: ignore
        self.output = QAudioOutput()  # type: ignore
        self.player.setAudioOutput(self.output)

        # Async processing components
        self.loader_thread: Any = None
        self.trim_processor: Any = None
        self.progress_dialog: Any = None

        # UI state
        self.is_loading: bool = False
        self.is_processing: bool = False

        # Cloud components (optional)
        self.auth_manager: Optional[Any] = None
        self.drive_manager: Optional[Any] = None
        self.feature_gate: Optional[Any] = None
        self.cloud_ui: Optional[Any] = None
        # UI placeholders that may be created later
        self.fallback_widget: Optional[QWidget] = None
        self.tab_widget: Optional[QTabWidget] = None

        if _cloud_available:
            # Determine effective keyring preference: explicit parameter overrides global config
            effective_use_keyring = (
                bool(use_keyring)
                if use_keyring is not None
                else bool(config_manager.prefers_keyring())
            )
            self.init_cloud_components(feature_gate, use_keyring=effective_use_keyring)

        self.init_ui()
        self.connect_signals()
        self.setup_audio_recorder()

    def init_cloud_components(
        self, feature_gate: Optional[Any] = None, use_keyring: Optional[bool] = None
    ) -> None:
        """Initialize cloud components if available"""
        try:
            if (
                GoogleAuthManager is not None
                and GoogleDriveManager is not None
                and FeatureGate is not None
                and CloudUI is not None
            ):
                # Respect caller-specified use_keyring; default to config_manager preference
                self.auth_manager = GoogleAuthManager(
                    use_keyring=(
                        use_keyring
                        if use_keyring is not None
                        else config_manager.prefers_keyring()
                    )
                )
                self.drive_manager = GoogleDriveManager(self.auth_manager)
                self.feature_gate = feature_gate or FeatureGate(self.auth_manager)
                self.cloud_ui = CloudUI(
                    self.auth_manager, self.drive_manager, self.feature_gate
                )
                print("✅ Cloud features initialized")
            else:
                print("ℹ️ Cloud modules not available; cloud features disabled.")
        except Exception as e:
            print(f"❌ Failed to initialize cloud features: {e}")

    def _replace_fallback_with_cloud(self) -> None:
        """If a fallback Cloud widget was shown, replace it with the real CloudUI after
        a successful initialization attempt.
        """
        try:
            if getattr(self, "cloud_ui", None) is None:
                return

            # Try tabbed replacement first, then single-widget replacement
            if self._replace_tabbed_fallback_with_cloud():
                return
            self._replace_single_fallback_with_cloud()
        except Exception:
            # Don't let UI replacement crash the app
            pass

    def _replace_tabbed_fallback_with_cloud(self) -> bool:
        """Return True if a CloudFallback tab was found and replaced."""
        if getattr(self, "tab_widget", None) is None:
            return False
        tw: QTabWidget = self.tab_widget
        for i in range(tw.count()):
            w = tw.widget(i)
            if (
                getattr(w, "__class__", None)
                and w.__class__.__name__ == "CloudFallbackWidget"
            ):
                tw.removeTab(i)
                tw.addTab(self.cloud_ui, "☁️ Cloud Features")
                return True
        return False

    def _replace_single_fallback_with_cloud(self) -> None:
        """Safely replace a single fallback widget with the initialized CloudUI."""
        if getattr(self, "fallback_widget", None) is None:
            return
        try:
            fb = self.fallback_widget
            if fb is None:
                return
            parent = fb.parentWidget()
            if parent is None:
                return
            parent_layout = parent.layout()
            if parent_layout is not None:
                parent_layout.removeWidget(fb)
                fb.deleteLater()
                parent_layout.addWidget(self.cloud_ui)
                self.fallback_widget = None
        except Exception:
            # Best-effort replacement; ignore any errors
            pass

    def init_ui(self) -> None:
        """Initialize the user interface with tabs for cloud features"""
        main_layout = QVBoxLayout()

        # Title and status section
        title_label = QLabel("🎵 Voice Recorder Pro - Professional Edition")
        title_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #2c3e50; margin: 10px;"
        )

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
            # Create interfaces but include a fallback cloud widget so users can
            # discover how to enable cloud features and attempt to initialize.
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
                    self.init_cloud_components(
                        self.feature_gate, use_keyring=effective_use_keyring
                    )
                self.status_label.setText("Preferences saved.")
            except Exception as e:
                logger.exception("Failed to apply preferences: %s", e)
                QMessageBox.warning(
                    self,
                    "Preferences",
                    "Saved preferences but failed to reinitialize cloud features.",
                )

    def create_tabbed_interface(self, main_layout: QVBoxLayout) -> None:
        """Create tabbed interface with cloud features"""
        tab_widget = QTabWidget()
        # Keep a reference for dynamic replacement when cloud becomes available
        self.tab_widget = tab_widget

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

            # Add a fallback cloud widget with helpful actions (Retry init, open requirements)
            fb = None
            try:
                # Import the extracted fallback widget implementation
                from voice_recorder.cloud.cloud_fallback import CloudFallbackWidget

                fb = CloudFallbackWidget(self, editor_ref=self)
                self.fallback_widget = fb
                main_layout.addWidget(fb)
            except Exception:
                # If fallback creation fails, silently continue
                pass

        main_layout.addStretch()  # Push everything to top

    def create_file_section(self) -> QWidget:
        """Create file operations section"""
        section = QWidget()
        layout = QVBoxLayout()

        # Load button
        self.load_button = QPushButton(UIConstants.LOAD_AUDIO_FILE)
        self.load_button.setStyleSheet(
            """
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
        """
        )
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
        record_label.setStyleSheet(
            "font-weight: bold; color: #c0392b; margin-top: 10px;"
        )

        # Recording controls layout
        record_layout = QHBoxLayout()

        # Record button
        self.record_button = QPushButton(UIConstants.START_RECORDING)
        self.record_button.setStyleSheet(
            """
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
        """
        )
        self.record_button.clicked.connect(self.toggle_recording)

        # Recording status and level display
        self.recording_status = QLabel(UIConstants.READY_TO_RECORD)
        self.recording_status.setStyleSheet("color: #34495e; margin: 5px;")

        self.recording_duration = QLabel(UIConstants.TIME_FORMAT_ZERO)
        self.recording_duration.setStyleSheet(
            "font-family: monospace; font-size: 14px; color: #2c3e50;"
        )

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
        self.start_input.setStyleSheet(
            "padding: 8px; border: 2px solid #bdc3c7; border-radius: 4px;"
        )

        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("End time (seconds)")
        self.end_input.setStyleSheet(
            "padding: 8px; border: 2px solid #bdc3c7; border-radius: 4px;"
        )

        self.trim_button = QPushButton(UIConstants.TRIM_AND_SAVE)
        self.trim_button.setStyleSheet(
            """
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
        """
        )
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
        self.progress_bar.setStyleSheet(
            """
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
        """
        )

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
        if hasattr(self, "start_input") and hasattr(self, "end_input"):
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
            "Audio Files (*.wav *.mp3 *.ogg);;WAV Files (*.wav);;All Files (*)",
        )

        if not file_path:
            return

        # Start async loading
        self.is_loading = True
        self.update_ui_for_loading(True)

        # Create and start loader thread
        # Type as Any to avoid mypy noise about Qt signal attributes on the thread
        self.loader_thread = cast(Any, AudioLoaderThread(file_path))
        # connect signals if thread present
        if self.loader_thread is not None:
            try:
                self.loader_thread.audio_loaded.connect(self.on_audio_loaded)  # type: ignore[attr-defined]
                self.loader_thread.error_occurred.connect(self.on_load_error)  # type: ignore[attr-defined]
                self.loader_thread.progress_updated.connect(self.on_load_progress)  # type: ignore[attr-defined]
                self.loader_thread.finished.connect(self.on_load_finished)  # type: ignore[attr-defined]
            except Exception:
                # best-effort connect; if signals missing, continue gracefully
                pass

        # Show progress
        self.show_progress("Loading Audio File")

        if self.loader_thread is not None:
            try:
                self.loader_thread.start()
            except Exception:
                # guard against unexpected missing start
                pass

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
                "WAV Files (*.wav);;MP3 Files (*.mp3);;All Files (*)",
            )

            if not save_path:
                return

            # Start async trimming
            self.is_processing = True
            self.update_ui_for_processing(True)

            self.trim_processor = AudioTrimProcessor(
                self.audio_segment, start_ms, end_ms, save_path
            )  # type: ignore

            self.trim_processor.progress_updated.connect(self.on_trim_progress)
            self.trim_processor.trim_completed.connect(self.on_trim_completed)
            self.trim_processor.error_occurred.connect(self.on_trim_error)
            self.trim_processor.finished.connect(self.on_trim_finished)

            # Show progress
            self.show_progress("Trimming Audio")

            self.trim_processor.start()

        except ValueError:
            QMessageBox.warning(
                self,
                "Invalid Input",
                "Please enter valid numeric values for start and end times.",
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start trim operation: {e}")

    def show_progress(self, operation_name: str):
        """Show progress bar and label"""
        if self.progress_bar is not None:
            try:
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
            except Exception:
                pass
        if self.progress_label is not None:
            try:
                self.progress_label.setVisible(True)
                self.progress_label.setText(f"{operation_name}...")
            except Exception:
                pass

    def hide_progress(self):
        """Hide progress indicators"""
        if self.progress_bar is not None:
            try:
                self.progress_bar.setVisible(False)
            except Exception:
                pass
        if self.progress_label is not None:
            try:
                self.progress_label.setVisible(False)
            except Exception:
                pass

    def update_ui_for_loading(self, loading: bool) -> None:
        """Update UI state during loading"""
        if self.load_button is not None:
            try:
                self.load_button.setEnabled(not loading)
                if loading:
                    self.load_button.setText(UIConstants.LOADING_AUDIO)
                    if self.status_label is not None:
                        self.status_label.setText("Loading audio file...")
                else:
                    self.load_button.setText(UIConstants.LOAD_AUDIO_FILE)
            except Exception:
                pass

    def update_ui_for_processing(self, processing: bool):
        """Update UI state during processing"""
        if self.trim_button is not None:
            try:
                self.trim_button.setEnabled(not processing)
            except Exception:
                pass
        for button in [self.play_button, self.pause_button, self.stop_button]:
            if button is not None:
                try:
                    button.setEnabled(not processing and self.audio_segment is not None)  # type: ignore
                except Exception:
                    pass

    def validate_trim_inputs(self) -> bool:
        """Validate trim input fields"""
        if not self.audio_segment:  # type: ignore
            self._disable_trim_button()
            return False

        parsed = self._parse_trim_inputs()
        if parsed is None:
            self._disable_trim_button()
            return False

        start_ms, end_ms = parsed
        duration_ms = len(self.audio_segment)  # type: ignore

        # Validate range and set button state
        valid = 0 <= start_ms < end_ms <= duration_ms
        if self.trim_button is not None:
            try:
                self.trim_button.setEnabled(valid and not self.is_processing)
            except Exception:
                pass
        return valid

    def _disable_trim_button(self) -> None:
        if self.trim_button is not None:
            try:
                self.trim_button.setEnabled(False)
            except Exception:
                pass

    def _parse_trim_inputs(self) -> Optional[Tuple[float, float]]:
        """Parse trim inputs and return (start_ms, end_ms) or None on invalid input."""
        if self.start_input is None or self.end_input is None:
            return None
        try:
            start_text = self.start_input.text().strip()
            end_text = self.end_input.text().strip()
            if not start_text or not end_text:
                return None
            start_ms = float(start_text) * 1000
            end_ms = float(end_text) * 1000
            return (start_ms, end_ms)
        except Exception:
            return None

    # Event handlers for async operations
    def on_audio_loaded(self, audio_segment: "AudioSegment", file_path: str):
        """Handle successful audio loading"""
        self.audio_file = file_path
        self.audio_segment = audio_segment

        # Update UI
        filename = os.path.basename(file_path)
        duration = len(audio_segment) / 1000  # Convert to seconds
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Convert to MB

        if self.file_info_label is not None:
            try:
                self.file_info_label.setText(
                    f"📄 {filename} | ⏱️ {duration:.1f}s | 💾 {file_size:.1f}MB"
                )
            except Exception:
                pass
        if self.status_label is not None:
            try:
                self.status_label.setText("Audio file loaded successfully!")
            except Exception:
                pass

        # Enable playback controls
        for button in [self.play_button, self.pause_button, self.stop_button]:
            if button is not None:
                try:
                    button.setEnabled(True)
                except Exception:
                    pass

        # Setup media player
        try:
            self.player.setSource(QUrl.fromLocalFile(file_path))
        except Exception:
            pass

        # Validate trim inputs
        try:
            self.validate_trim_inputs()
        except Exception:
            pass

        # Show waveform
        try:
            self.show_waveform(file_path)
        except Exception:
            pass

    def show_waveform(self, file_path: str):
        """Display waveform of loaded audio file."""
        # Remove previous waveform if exists
        if self.waveform_viewer and self.waveform_layout is not None:
            try:
                self.waveform_layout.removeWidget(self.waveform_viewer)
                self.waveform_viewer.deleteLater()
                self.waveform_viewer = None
            except Exception:
                pass
        try:
            self.waveform_viewer = WaveformViewer(file_path)
            if self.waveform_layout is not None:
                self.waveform_layout.addWidget(self.waveform_viewer)
        except Exception:
            pass

    def on_load_error(self, error_message: str):
        """Handle audio loading errors with helpful recovery suggestions"""
        try:
            # Create a detailed error message with recovery options
            detailed_message = error_message
            
            # Add helpful suggestions based on the error
            if "FFmpeg" in error_message or "codec" in error_message.lower():
                detailed_message += "\n\n💡 Suggestions:\n"
                detailed_message += "• The audio file may be corrupted or in an unsupported format\n"
                detailed_message += "• Try converting it with FFmpeg:\n"
                detailed_message += "  ffmpeg -i input.wav -acodec pcm_s16le -ar 44100 output.wav\n"
                detailed_message += "• Or use the Audio Repair Tool:\n"
                detailed_message += "  python tools/audio_repair.py <file.wav>"
            elif "not found" in error_message.lower():
                detailed_message += "\n\n💡 Suggestions:\n"
                detailed_message += "• The audio file could not be found\n"
                detailed_message += "• Check that the file path is correct\n"
                detailed_message += "• Ensure the file has not been moved or deleted"
            
            QMessageBox.critical(
                self, "Loading Error", detailed_message
            )
        except Exception:
            pass
        if self.status_label is not None:
            try:
                self.status_label.setText("Failed to load audio file.")
            except Exception:
                pass

    def on_load_progress(self, value: int, message: str):
        """Handle loading progress updates"""
        if self.progress_bar is not None:
            try:
                self.progress_bar.setValue(value)
            except Exception:
                pass
        if self.progress_label is not None:
            try:
                self.progress_label.setText(message)
            except Exception:
                pass

    def on_load_finished(self):
        """Handle completion of loading operation"""
        self.is_loading = False
        self.update_ui_for_loading(False)
        self.hide_progress()

    def on_trim_completed(self, output_path: str):
        """Handle successful trim completion"""
        filename = os.path.basename(output_path)
        self.status_label.setText(f"✅ Trimmed audio saved: {filename}")
        QMessageBox.information(
            self, "Success", f"Audio trimmed successfully!\nSaved to: {filename}"
        )

    def on_trim_error(self, error_message: str):
        """Handle trim operation errors"""
        QMessageBox.critical(
            self, "Trim Error", f"Failed to trim audio:\n{error_message}"
        )
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
                self.device_selector.addItem(
                    f"{dev['index']}: {dev['name']}", dev["index"]
                )
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
        self.record_button.setStyleSheet(
            """
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
        """
        )
        self.recording_status.setText(UIConstants.RECORDING_IN_PROGRESS)
        self.status_label.setText("🎤 Recording audio...")

    def on_recording_stopped(self, file_path: str, duration: float) -> None:
        """Handle recording completion with optional cloud upload"""
        self.is_recording = False
        self.record_button.setText(UIConstants.START_RECORDING)
        self.record_button.setStyleSheet(
            """
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
        """
        )

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
            self.status_label.setText(
                f"✅ Recording completed: {duration:.1f}s | ☁️ Ready for cloud upload"
            )

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
        """Save recording metadata to database.

        Import the DB session and model lazily so importing this module does not
        register SQLAlchemy mappings at import time (prevents duplicate-table
        errors during import-only validation runs).
        """
        try:
            from models.database import SessionLocal as _SessionLocal
            from models.recording import Recording as _Recording
        except Exception as e:
            # DB/models unavailable in this environment (e.g., limited test runner)
            print(f"⚠️ DB models unavailable, skipping metadata save: {e}")
            return

        try:
            filename = os.path.basename(file_path)
            with _SessionLocal() as db:
                recording = _Recording(
                    filename=filename,
                    stored_filename=filename,
                    duration=duration,
                    status="active",
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
            # Lazy-import pydub.AudioSegment to avoid import-time crashes when
            # optional native deps (audioop/pyaudioop) are missing in the
            # test/runtime environment.
            try:
                from pydub import AudioSegment  # type: ignore
            except Exception as _e:
                # Surface a clear ImportError so callers/tests can skip or
                # handle missing audio support.
                raise ImportError("pydub.AudioSegment not available: %s" % _e)

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
