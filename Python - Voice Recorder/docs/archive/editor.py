# editor.py
# Basic audio editor GUI using PySide6

from PySide6.QtWidgets import (
    QWidget, QPushButton, QLabel, QFileDialog,
    QVBoxLayout, QHBoxLayout, QLineEdit, QMessageBox
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl
from pydub import AudioSegment  # type: ignore
import os
from typing import Optional, cast


class AudioEditorWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voice Editor - Trim Audio")
        self.setMinimumWidth(400)
        
        self.audio_file: Optional[str] = None
        self.audio_segment: Optional[AudioSegment] = None
        
        self.player = QMediaPlayer()
        self.output = QAudioOutput()
        self.player.setAudioOutput(self.output)

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.load_button = QPushButton("Load Audio File")
        self.load_button.clicked.connect(self.load_audio)

        self.play_button = QPushButton("▶️ Play")
        self.play_button.clicked.connect(self.play_audio)

        self.pause_button = QPushButton("⏸️ Pause")
        self.pause_button.clicked.connect(self.pause_audio)

        trim_layout = QHBoxLayout()
        self.start_input = QLineEdit()
        self.start_input.setPlaceholderText("Start (sec)")
        self.end_input = QLineEdit()
        self.end_input.setPlaceholderText("End (sec)")
        self.trim_button = QPushButton("Trim & Save")
        self.trim_button.clicked.connect(self.trim_audio)
        trim_layout.addWidget(self.start_input)
        trim_layout.addWidget(self.end_input)
        trim_layout.addWidget(self.trim_button)

        self.status = QLabel("No file loaded.")

        layout.addWidget(self.load_button)
        layout.addWidget(self.play_button)
        layout.addWidget(self.pause_button)
        layout.addLayout(trim_layout)
        layout.addWidget(self.status)
        self.setLayout(layout)

    def load_audio(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Audio File", "recordings/raw", "*.wav")
        if file_path:
            try:
                self.audio_file = file_path
                # Cast to suppress type warnings - pydub doesn't have complete type stubs
                self.audio_segment = cast(AudioSegment, AudioSegment.from_wav(file_path))  # type: ignore
                self.player.setSource(QUrl.fromLocalFile(file_path))
                self.status.setText(f"Loaded: {os.path.basename(file_path)}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load audio: {e}")
                self.audio_segment = None

    def play_audio(self):
        if self.audio_file:
            self.player.play()

    def pause_audio(self):
        self.player.pause()

    def trim_audio(self):
        if not self.audio_segment:
            QMessageBox.warning(self, "No File", "Please load an audio file first.")
            return

        try:
            # Validate input fields
            if not self.start_input.text() or not self.end_input.text():
                QMessageBox.warning(self, "Invalid Input", "Please enter both start and end times.")
                return
                
            start_ms = int(float(self.start_input.text()) * 1000)
            end_ms = int(float(self.end_input.text()) * 1000)
            
            # Validate range
            if start_ms >= end_ms:
                QMessageBox.warning(self, "Invalid Range", "Start time must be less than end time.")
                return
            
            if start_ms < 0 or end_ms > len(self.audio_segment):
                QMessageBox.warning(self, "Invalid Range", f"Time range must be between 0 and {len(self.audio_segment)/1000:.1f} seconds.")
                return

            # Perform trimming with type casting to handle pydub type issues
            trimmed = cast(AudioSegment, self.audio_segment[start_ms:end_ms])
            trimmed = trimmed.fade_in(250).fade_out(250)  # type: ignore

            save_path, _ = QFileDialog.getSaveFileName(self, "Save Trimmed File", "recordings/edited/trimmed.wav", "*.wav")
            if save_path:
                # Ensure directory exists
                os.makedirs(os.path.dirname(save_path), exist_ok=True)
                trimmed.export(save_path, format="wav")  # type: ignore
                self.status.setText(f"Saved trimmed audio to: {save_path}")
        except ValueError as e:
            QMessageBox.critical(self, "Input Error", f"Invalid time format: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to trim: {e}")
