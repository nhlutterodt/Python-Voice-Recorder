# audio_recorder.py
# Audio recording component with real-time monitoring and async operations

from PySide6.QtCore import QThread, Signal, QObject
import sounddevice as sd  # type: ignore
from typing import Optional, List, Any, Dict, Union
from numpy.typing import NDArray
import numpy as np
import wave
import os
import time
import traceback
from datetime import datetime
import uuid
from voice_recorder.performance_monitor import performance_monitor
from voice_recorder.core.logging_config import get_logger
import threading

# When running headless (scripts/tests) persist recordings to DB automatically
try:
    from voice_recorder.services.recording_service import RecordingService
except Exception:
    RecordingService = None

# Setup logging for this module
logger = get_logger(__name__)


class AudioRecorderThread(QThread):
    """Asynchronous audio recorder with real-time monitoring"""
    recording_started = Signal()
    recording_progress = Signal(float, float)  # duration, audio_level
    recording_completed = Signal(str, float)  # file_path, duration
    recording_error = Signal(str)
    
    def __init__(self, output_path: str, sample_rate: int = 44100, channels: int = 1, device: Optional[Union[int, str]] = None):
        super().__init__()
        self.output_path = output_path
        self.sample_rate = sample_rate
        self.channels = channels
        # Optional device selection (index or name). If None, use default device.
        self.device = device
        self.is_recording = False
        self.audio_data: List[NDArray[np.float32]] = []  # Properly typed audio data list
        self.start_time = 0.0
        self.frames_recorded = 0
        # Internal flag set when a callback-level error occurred; used to
        # prevent finalizing partial files into final recordings.
        self._recording_failed = False
    
    def run(self):
        """Record audio in background thread with progress monitoring.

        The implementation delegates smaller responsibilities to helper
        methods so the top-level flow is easy to follow and test.
        """
        try:
            with performance_monitor.measure_operation("Audio Recording"):
                self.recording_started.emit()
                self.is_recording = True
                self.start_time = time.time()

                # Prepare environment and WAV file
                tmp_path = f"{self.output_path}.part"
                wav_file, wav_lock = self._prepare_wav_file(tmp_path)

                # Configure chunking and build InputStream kwargs
                chunk_duration = 0.1
                chunk_frames = int(chunk_duration * self.sample_rate)
                self.audio_data = []

                audio_callback = self._make_audio_callback(wav_file, wav_lock)
                stream_kwargs = self._open_input_stream_kwargs(audio_callback, chunk_frames)

                # Start the recording stream and loop until stopped
                with sd.InputStream(**stream_kwargs):
                    logger.debug("InputStream started for recording")
                    while self.is_recording:
                        self.msleep(50)
                    logger.debug("Recording stop requested; exiting InputStream context")

                # Finalize WAV and move to final destination
                try:
                    self._finalize_wav(wav_file, wav_lock, tmp_path)
                except Exception:
                    # _finalize_wav already logs; re-raise to hit outer error path
                    raise

        except Exception as e:
            logger.exception("Recording failed")
            self.recording_error.emit(f"Recording failed: {str(e)}")

    def _prepare_wav_file(self, tmp_path: str):
        """Create directories and open a WAV file for streaming writes.

        Returns (wav_file, wav_lock).
        """
        os.makedirs(os.path.dirname(self.output_path) or '.', exist_ok=True)
        wav_lock = threading.Lock()
        try:
            wav_file = wave.open(tmp_path, 'wb')
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            return wav_file, wav_lock
        except Exception:
            logger.exception("Failed to open temporary WAV file for streaming")
            raise

    def _make_audio_callback(self, wav_file, wav_lock):
        """Return the audio callback that writes incoming frames and emits progress."""
        def audio_callback(indata: NDArray[np.float32], frames: int, time: Any, status: Any) -> None:
            if status:
                logger.debug(f"Recording callback status: {status}")

            if not self.is_recording:
                return

            try:
                arr = np.asarray(indata, dtype=np.float32)
                if arr.ndim == 1:
                    arr = arr.reshape(-1, 1)

                int16 = (np.clip(arr, -1.0, 1.0) * 32767).astype(np.int16)
                with wav_lock:
                    wav_file.writeframes(int16.tobytes())

                # Update frames and emit progress
                self.frames_recorded += int16.shape[0]
                audio_level = float(np.sqrt(np.mean(arr**2)))
                current_duration = float(self.frames_recorded) / float(self.sample_rate)
                self.recording_progress.emit(current_duration, audio_level)
            except Exception:
                # Record and surface callback-level errors. We set a flag so
                # the finalizer knows not to promote the .part file to final
                # and emit a recording_error so callers can react.
                logger.exception("Error in audio callback")
                self._recording_failed = True
                try:
                    self.recording_error.emit(f"Recording callback error: {traceback.format_exc()}")
                except Exception:
                    # Emitting signals from a non-Qt thread may fail; swallow
                    # to avoid secondary errors while still marking failure.
                    logger.debug("Could not emit recording_error from audio callback")
                # Stop recording cooperatively
                self.is_recording = False

        return audio_callback

    def _open_input_stream_kwargs(self, callback, chunk_frames: int) -> dict:
        """Build kwargs for sd.InputStream, only including device when set."""
        stream_kwargs = {
            'callback': callback,
            'samplerate': self.sample_rate,
            'channels': self.channels,
            'dtype': np.float32,
            'blocksize': chunk_frames,
        }
        if self.device is not None:
            stream_kwargs['device'] = self.device
        return stream_kwargs

    def _finalize_wav(self, wav_file, wav_lock, tmp_path: str) -> None:
        """Close the wav file under lock and atomically move the temporary file.

        Emits recording_completed on success and recording_error on failure.
        """
        try:
            # If a callback-level error occurred, remove the temporary file and
            # skip promoting it to the final file.
            if getattr(self, '_recording_failed', False):
                try:
                    with wav_lock:
                        try:
                            wav_file.close()
                        except Exception:
                            logger.exception("Error closing wav file after callback failure")
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
                except Exception:
                    logger.exception("Failed to cleanup temporary recording after callback failure")
                # recording_error was already emitted by the callback; return.
                return

            with wav_lock:
                try:
                    wav_file.close()
                except Exception:
                    # Log and continue to attempt cleanup/rename
                    logger.exception("Error closing wav file")

            os.replace(tmp_path, self.output_path)
            duration = float(self.frames_recorded) / float(self.sample_rate)
            self.recording_completed.emit(self.output_path, duration)
        except Exception as e:
            logger.exception("Failed to finalize recording file")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                logger.exception("Failed to remove temporary recording file")
            try:
                self.recording_error.emit(f"Failed to save recording: {e}")
            except Exception:
                logger.debug("Could not emit recording_error from finalizer")
    
    def stop_recording(self):
        """Stop the recording process"""
        self.is_recording = False
    
    def _save_recording(self):
        """Save recorded audio data to file"""
        try:
            # Fallback: if audio_data has been collected, write it using helper
            if self.audio_data:
                duration = AudioRecorderThread.write_wave_from_float32_chunks(
                    self.output_path, self.audio_data, self.sample_rate, self.channels
                )
                self.recording_completed.emit(self.output_path, duration)
                return

            # No buffered audio available; nothing to save
            self.recording_error.emit("No audio data to save")
        
        except Exception as e:
            logger.exception("Failed to save recording")
            self.recording_error.emit(f"Failed to save recording: {str(e)}")

    @staticmethod
    def write_wave_from_float32_chunks(output_path: str, chunks, sample_rate: int, channels: int) -> float:
        """Write float32 numpy chunks (range -1..1) to a WAV file incrementally.

        chunks: iterable of numpy arrays shaped (frames, channels) or (frames,)
        Returns duration in seconds.
        """
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

        frames_written = 0
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)

            for chunk in chunks:
                arr = np.asarray(chunk, dtype=np.float32)
                # If mono chunk shaped (n,) convert to (n,1)
                if arr.ndim == 1:
                    arr = arr.reshape(-1, 1)

                # Ensure channels match
                if arr.shape[1] != channels:
                    # Try to adapt: if arr has more channels, take first N
                    if arr.shape[1] > channels:
                        arr = arr[:, :channels]
                    else:
                        # pad with zeros
                        pad = np.zeros((arr.shape[0], channels - arr.shape[1]), dtype=np.float32)
                        arr = np.concatenate([arr, pad], axis=1)

                # Convert to int16
                int16 = (np.clip(arr, -1.0, 1.0) * 32767).astype(np.int16)
                wav_file.writeframes(int16.tobytes())
                frames_written += int16.shape[0]

        duration = frames_written / float(sample_rate)
        return duration


class AudioLevelMonitor(QThread):
    """Real-time audio level monitoring running in a background thread.

    Uses sounddevice.InputStream with a callback to emit short-term RMS levels.
    """
    level_updated = Signal(float)
    device_error = Signal(str)

    def __init__(self, sample_rate: int = 44100, channels: int = 1, device: Optional[Union[int, str]] = None):
        super().__init__()
        self.sample_rate = sample_rate
        self.channels = channels
        self._stop_requested = False
        # Optional device index or name to monitor
        self.device = device

    def start_monitoring(self):
        """Start the monitor thread."""
        self._stop_requested = False
        if not self.isRunning():
            self.start()

    def stop_monitoring(self):
        """Request the monitor to stop and wait for it."""
        self._stop_requested = True
        if self.isRunning():
            self.requestInterruption()
            self.wait(1000)

    def run(self):
        try:
            chunk_duration = 0.05
            frames = int(chunk_duration * self.sample_rate)

            def callback(indata, frames_, time_, status):
                if status:
                    logger.debug(f"AudioLevelMonitor status: {status}")
                try:
                    level = float(np.sqrt(np.mean(indata**2)))
                    self.level_updated.emit(level)
                except Exception:
                    logger.exception("Error computing audio level")

            stream_kwargs = dict(callback=callback, samplerate=self.sample_rate, channels=self.channels, dtype=np.float32, blocksize=frames)
            if self.device is not None:
                stream_kwargs['device'] = self.device

            with sd.InputStream(**stream_kwargs):
                logger.debug("AudioLevelMonitor InputStream started")
                while not self._stop_requested and not self.isInterruptionRequested():
                    self.msleep(50)
                logger.debug("AudioLevelMonitor stopping")

        except Exception as e:
            logger.exception("Audio monitoring error")
            self.device_error.emit(f"Audio monitoring error: {e}")


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
        # Currently selected device (index or name) used by manager-level
        # operations when callers do not pass an explicit device.
        self.selected_device: Optional[Union[int, str]] = None
        
        # Ensure output directory exists
        os.makedirs(self.output_directory, exist_ok=True)
        
        # Validate audio devices on initialization (default device)
        self._validate_audio_devices()

    def set_selected_device(self, device: Optional[Union[int, str]]) -> bool:
        """Set and validate the selected input device for subsequent operations.

        Returns True on success, False if the device is unusable.
        """
        if device is None:
            # Clearing selection is always allowed
            self.selected_device = None
            self.device_status_changed.emit(True)
            return True

        # Validate the requested device
        ok = self._validate_audio_devices(device=device)
        if ok:
            self.selected_device = device
            self.device_status_changed.emit(True)
            return True
        else:
            return False

    def get_selected_device(self) -> Optional[Union[int, str]]:
        """Return the currently selected device (index or name)."""
        return self.selected_device
    
    def _validate_audio_devices(self, device: Optional[Union[int, str]] = None) -> bool:
        """Validate that audio input devices are available.

        If `device` is provided it will be used when attempting to open a
        short InputStream. Returns True when a usable input device exists.
        """
        try:
            devices = sd.query_devices()  # type: ignore
            input_devices = [d for d in devices if d.get('max_input_channels', 0) > 0]  # type: ignore

            if not input_devices:
                self.device_status_changed.emit(False)
                return False

            # Determine a sensible samplerate for the target device
            test_samplerate = 44100
            try:
                target_dev = device if device is not None else sd.default.device  # type: ignore
                if isinstance(target_dev, (list, tuple)):
                    target_dev = target_dev[0]

                if target_dev is not None:
                    try:
                        dev_info = sd.query_devices(target_dev)  # type: ignore
                        if isinstance(dev_info, dict):
                            test_samplerate = int(dev_info.get('default_samplerate', test_samplerate))
                    except Exception:
                        # ignore and keep fallback samplerate
                        pass
            except Exception:
                pass

            # Try opening an InputStream for the specified (or default)
            # device to ensure it is usable.
            try:
                stream_kwargs = dict(samplerate=test_samplerate, channels=1, dtype=np.float32, blocksize=1024)
                if device is not None:
                    stream_kwargs['device'] = device

                with sd.InputStream(**stream_kwargs):
                    pass
                self.device_status_changed.emit(True)
                return True
            except Exception as e:
                logger.exception("InputStream device test failed")
                self.device_status_changed.emit(False)
                self.recording_error.emit(f"Audio device test failed: {e}")
                return False

        except Exception as e:
            logger.exception("Device validation failed")
            self.device_status_changed.emit(False)
            self.recording_error.emit(f"Device validation failed: {str(e)}")
            return False
    
    def start_recording(self, filename: Optional[str] = None, sample_rate: int = 44100, device: Optional[Union[int, str]] = None) -> bool:
        """Start audio recording with optional custom filename"""
        if self.is_recording:
            self.recording_error.emit("Recording already in progress")
            return False
        
        # Validate devices before starting
        # If caller didn't pass a device, prefer the manager's selected_device
        if device is None:
            device = self.selected_device

        if not self._validate_audio_devices(device=device):
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
            
            # Create and start recorder thread, forwarding device selection
            self.recorder_thread = AudioRecorderThread(output_path, sample_rate, channels=1, device=device)
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
        # Request a cooperative stop
        self.recorder_thread.stop_recording()
        # Wait briefly for thread to finish
        if self.recorder_thread.isRunning():
            self.recorder_thread.wait(2000)
    
    def start_level_monitoring(self):
        """Start monitoring input audio levels.

        If `device` is provided it will be used; otherwise the manager's
        `selected_device` will be used when available.
        """
        def _ensure_monitor(dev: Optional[Union[int, str]]):
            if self.level_monitor is None:
                self.level_monitor = AudioLevelMonitor(device=dev)
                self.level_monitor.level_updated.connect(self._on_level_updated)
                self.level_monitor.device_error.connect(self.recording_error.emit)

        # Use provided device if present, otherwise fall back to selected_device
        def start_with_device(device: Optional[Union[int, str]] = None):
            dev_to_use = device if device is not None else self.selected_device
            _ensure_monitor(dev_to_use)
            if self.level_monitor and self.level_monitor.device != dev_to_use:
                # recreate monitor with requested device
                try:
                    self.level_monitor.stop_monitoring()
                except Exception:
                    pass
                self.level_monitor = AudioLevelMonitor(device=dev_to_use)
                self.level_monitor.level_updated.connect(self._on_level_updated)
                self.level_monitor.device_error.connect(self.recording_error.emit)

            if self.level_monitor:
                self.level_monitor.start_monitoring()

        # Public entry: if caller passed a device, use it; otherwise default
        # to manager selected device.
        start_with_device()
    
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
        # If running headless (no QApplication instance), auto-persist metadata
        try:
            from PySide6.QtWidgets import QApplication
            has_qt_app = QApplication.instance() is not None
        except Exception:
            has_qt_app = False

        if not has_qt_app and RecordingService is not None:
            try:
                # inject the app db_context so the service uses the same DB as the app
                from voice_recorder.models.database import db_context as app_db_context
                svc = RecordingService(db_ctx=app_db_context)
                svc.create_from_file(file_path)
                logger.info("Auto-persisted recording metadata for %s", file_path)
            except Exception:
                logger.exception("Failed to auto-persist recording for %s", file_path)

        # Notify listeners
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
            # Request cooperative stop and wait briefly
            try:
                self.recorder_thread.stop_recording()
                self.recorder_thread.wait(1000)
            except Exception:
                logger.exception("Error while stopping recorder thread during cleanup")