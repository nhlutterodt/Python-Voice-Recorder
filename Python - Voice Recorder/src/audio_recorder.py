# audio_recorder.py
# Audio recording component with real-time monitoring and async operations

from PySide6.QtCore import QThread, Signal, QObject, QTimer
import sounddevice as sd  # type: ignore
from typing import Optional, List, Any, Dict
from numpy.typing import NDArray
import numpy as np
import wave
import os
import time
from datetime import datetime
import uuid
from performance_monitor import performance_monitor
from core.logging_config import get_logger

# Setup logging for this module
logger = get_logger(__name__)


class AudioRecorderThread(QThread):
    """Asynchronous audio recorder with real-time monitoring"""
    recording_started = Signal()
    recording_progress = Signal(float, float)  # duration, audio_level
    recording_completed = Signal(str, float)  # file_path, duration
    recording_error = Signal(str)
    
    def __init__(self, output_path: str, sample_rate: int = 44100, channels: int = 1):
        super().__init__()
        self.output_path = output_path
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.audio_data: List[NDArray[np.float32]] = []  # Properly typed audio data list
        self.start_time = 0.0
    
    def run(self):
        """Record audio in background thread with progress monitoring"""
        try:
            with performance_monitor.measure_operation("Audio Recording"):
                self.recording_started.emit()
                self.is_recording = True
                self.start_time = time.time()
                
                # Ensure output directory exists
                os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
                
                # Configure recording parameters
                chunk_duration = 0.1  # 100ms chunks for real-time feedback
                chunk_frames = int(chunk_duration * self.sample_rate)
                
                self.audio_data = []
                
                # Start recording with callback for real-time monitoring
                def audio_callback(indata: NDArray[np.float32], frames: int, time: Any, status: Any) -> None:
                    """Audio callback for real-time recording"""
                    if status:
                        print(f"Recording status: {status}")
                    
                    if self.is_recording:
                        # Store audio data
                        self.audio_data.append(indata.copy())
                        
                        # Calculate audio level (RMS)
                        audio_level = float(np.sqrt(np.mean(indata**2)))
                        current_duration = time.currentTime - self.start_time if hasattr(time, 'currentTime') else len(self.audio_data) * chunk_duration
                        
                        # Emit progress signal
                        self.recording_progress.emit(current_duration, audio_level)
                
                # Start the recording stream
                with sd.InputStream(  # type: ignore
                    callback=audio_callback,
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=np.float32,
                    blocksize=chunk_frames
                ):
                    # Keep recording until stopped
                    while self.is_recording:
                        self.msleep(50)  # Check every 50ms
                
                # Process and save recorded audio
                if self.audio_data:
                    self._save_recording()
                else:
                    self.recording_error.emit("No audio data recorded")
        
        except Exception as e:
            self.recording_error.emit(f"Recording failed: {str(e)}")
    
    def stop_recording(self):
        """Stop the recording process"""
        self.is_recording = False
    
    def _save_recording(self):
        """Save recorded audio data to file"""
        try:
            # Concatenate all audio chunks
            audio_array = np.concatenate(self.audio_data, axis=0)
            
            # Convert to 16-bit integer for WAV format
            audio_int16 = (audio_array * 32767).astype(np.int16)
            
            # Save as WAV file
            with wave.open(self.output_path, 'wb') as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes(audio_int16.tobytes())
            
            # Calculate final duration
            duration = len(audio_array) / self.sample_rate
            
            self.recording_completed.emit(self.output_path, duration)
        
        except Exception as e:
            self.recording_error.emit(f"Failed to save recording: {str(e)}")


class AudioLevelMonitor(QObject):
    """Real-time audio level monitoring for input validation"""
    level_updated = Signal(float)
    device_error = Signal(str)
    
    def __init__(self, sample_rate: int = 44100):
        super().__init__()
        self.sample_rate = sample_rate
        self.is_monitoring = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._check_audio_level)
        self.current_level = 0.0
    
    def start_monitoring(self):
        """Start monitoring audio input levels"""
        try:
            self.is_monitoring = True
            self.timer.start(50)  # Update every 50ms
        except Exception as e:
            self.device_error.emit(f"Failed to start monitoring: {str(e)}")
    
    def stop_monitoring(self):
        """Stop monitoring audio levels"""
        self.is_monitoring = False
        self.timer.stop()    
    def _check_audio_level(self):
        """Check current audio input level"""
        if not self.is_monitoring:
            return
        
        try:
            # Quick audio level sample
            duration = 0.05  # 50ms sample
            audio_sample = sd.rec(  # type: ignore
                int(duration * self.sample_rate),
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32
            )
            sd.wait()  # type: ignore
            
            # Calculate RMS level 
            level = float(np.sqrt(np.mean(audio_sample**2)))  # type: ignore
            self.current_level = level
            self.level_updated.emit(level)
        
        except Exception as e:
            self.device_error.emit(f"Audio monitoring error: {str(e)}")


class AudioRecorderManager(QObject):
    """High-level audio recorder manager with device validation"""
    recording_started = Signal()
    recording_stopped = Signal(str, float)  # file_path, duration
    recording_progress = Signal(float, float)  # duration, level
    recording_error = Signal(str)
    device_status_changed = Signal(bool)  # True if devices available
    
    def __init__(self):
        super().__init__()
        self.recorder_thread: Optional[AudioRecorderThread] = None
        self.level_monitor: Optional[AudioLevelMonitor] = None
        self.is_recording = False
        self.output_directory = "recordings/raw"
        
        # Ensure output directory exists
        os.makedirs(self.output_directory, exist_ok=True)
        
        # Validate audio devices on initialization
        self._validate_audio_devices()
    
    def _validate_audio_devices(self) -> bool:
        """Validate that audio input devices are available"""
        try:
            devices = sd.query_devices()  # type: ignore
            input_devices = [d for d in devices if d.get('max_input_channels', 0) > 0]  # type: ignore
            
            if not input_devices:
                self.device_status_changed.emit(False)
                return False
            
            # Test default input device
            try:
                sd.rec(  # type: ignore
                    frames=1024,  # Very short test
                    samplerate=44100,
                    channels=1,
                    dtype=np.float32
                )
                sd.wait()  # type: ignore
                self.device_status_changed.emit(True)
                return True
            
            except Exception as e:
                self.device_status_changed.emit(False)
                self.recording_error.emit(f"Audio device test failed: {str(e)}")
                return False
        
        except Exception as e:
            self.device_status_changed.emit(False)
            self.recording_error.emit(f"Device validation failed: {str(e)}")
            return False
    
    def start_recording(self, filename: Optional[str] = None, sample_rate: int = 44100) -> bool:
        """Start audio recording with optional custom filename"""
        if self.is_recording:
            self.recording_error.emit("Recording already in progress")
            return False
        
        # Validate devices before starting
        if not self._validate_audio_devices():
            self.recording_error.emit("No audio input devices available")
            return False
        
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"recording_{timestamp}_{uuid.uuid4().hex[:8]}.wav"
            
            # Ensure .wav extension
            if not filename.lower().endswith('.wav'):
                filename += '.wav'
            
            output_path = os.path.join(self.output_directory, filename)
            
            # Create and start recorder thread
            self.recorder_thread = AudioRecorderThread(output_path, sample_rate)
            self.recorder_thread.recording_started.connect(self._on_recording_started)
            self.recorder_thread.recording_progress.connect(self.recording_progress.emit)
            self.recorder_thread.recording_completed.connect(self._on_recording_completed)
            self.recorder_thread.recording_error.connect(self._on_recording_error)
            
            self.recorder_thread.start()
            self.is_recording = True
            
            return True
        
        except Exception as e:
            self.recording_error.emit(f"Failed to start recording: {str(e)}")
            return False
    
    def stop_recording(self):
        """Stop current recording"""
        if not self.is_recording or not self.recorder_thread:
            return
        
        self.recorder_thread.stop_recording()
    
    def start_level_monitoring(self):
        """Start monitoring input audio levels"""
        if self.level_monitor is None:
            self.level_monitor = AudioLevelMonitor()
            self.level_monitor.level_updated.connect(self._on_level_updated)
            self.level_monitor.device_error.connect(self.recording_error.emit)
        
        self.level_monitor.start_monitoring()
    
    def stop_level_monitoring(self):
        """Stop monitoring input audio levels"""
        if self.level_monitor:
            self.level_monitor.stop_monitoring()
    
    def get_available_devices(self) -> List[Dict[str, Any]]:
        """Get list of available audio input devices"""
        try:
            devices = sd.query_devices()  # type: ignore
            input_devices: List[Dict[str, Any]] = []
            
            for i, device in enumerate(devices):  # type: ignore
                if device.get('max_input_channels', 0) > 0:  # type: ignore
                    input_devices.append({
                        'index': i,
                        'name': device.get('name', ''),  # type: ignore
                        'channels': device.get('max_input_channels', 0),  # type: ignore
                        'sample_rate': device.get('default_samplerate', 44100)  # type: ignore
                    })
            
            return input_devices
        
        except Exception as e:
            self.recording_error.emit(f"Failed to get devices: {str(e)}")
            return []
    
    def _on_recording_started(self):
        """Handle recording start confirmation"""
        self.recording_started.emit()
    
    def _on_recording_completed(self, file_path: str, duration: float):
        """Handle recording completion"""
        self.is_recording = False
        self.recording_stopped.emit(file_path, duration)
        
        # Clean up thread
        if self.recorder_thread:
            self.recorder_thread.wait()
            self.recorder_thread = None
    
    def _on_recording_error(self, error_message: str):
        """Handle recording errors"""
        self.is_recording = False
        self.recording_error.emit(error_message)
        
        # Clean up thread
        if self.recorder_thread:
            self.recorder_thread.wait()
            self.recorder_thread = None
    
    def _on_level_updated(self, level: float):
        """Handle audio level updates (for standalone monitoring)"""
        # This can be used for input level display when not recording
        pass
    
    def cleanup(self):
        """Clean up resources"""
        if self.is_recording:
            self.stop_recording()
        
        if self.level_monitor:
            self.stop_level_monitoring()
        
        if self.recorder_thread and self.recorder_thread.isRunning():
            self.recorder_thread.terminate()
            self.recorder_thread.wait()