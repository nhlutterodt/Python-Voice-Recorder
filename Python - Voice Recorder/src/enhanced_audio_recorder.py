# Enhanced Audio Recorder with Integrated Storage System
# Phase 3 Integration: audio_recorder.py with enhanced file storage

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
try:
    from .performance_monitor import performance_monitor
except Exception:
    from performance_monitor import performance_monitor
from core.logging_config import get_logger

# PHASE 3 INTEGRATION: Enhanced Storage System
from services.file_storage.config import StorageConfig, EnvironmentManager
from services.file_storage.metadata import FileMetadataCalculator
from services.file_storage.exceptions import StorageConfigValidationError, FileMetadataError

# Setup logging for this module
logger = get_logger(__name__)

# Service for persisting recordings to DB when running headless (scripts/tests)
from services.recording_service import RecordingService


class AudioRecorderThread(QThread):
    """Asynchronous audio recorder with real-time monitoring and enhanced storage"""
    recording_started = Signal()
    recording_progress = Signal(float, float)  # duration, audio_level
    recording_completed = Signal(str, float, dict)  # file_path, duration, metadata
    recording_error = Signal(str)
    
    def __init__(self, output_path: str, sample_rate: int = 44100, channels: int = 1, 
                 storage_config: Optional[StorageConfig] = None):
        super().__init__()
        self.output_path = output_path
        self.sample_rate = sample_rate
        self.channels = channels
        self.is_recording = False
        self.audio_data: List[NDArray[np.float32]] = []  # Properly typed audio data list
        self.start_time = 0.0
        
        # PHASE 3 INTEGRATION: Enhanced storage configuration
        self.storage_config = storage_config
        self.metadata_calculator = FileMetadataCalculator()
    
    def run(self):
        """Record audio in background thread with progress monitoring and enhanced storage"""
        try:
            with performance_monitor.measure_operation("Audio Recording"):
                self.recording_started.emit()
                self.is_recording = True
                self.start_time = time.time()
                
                # PHASE 3 INTEGRATION: Enhanced directory creation
                self._ensure_output_directory()
                
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
                
                # Process and save recorded audio with enhanced metadata
                if self.audio_data:
                    self._save_recording_enhanced()
                else:
                    self.recording_error.emit("No audio data recorded")
        
        except Exception as e:
            self.recording_error.emit(f"Recording failed: {str(e)}")
    
    def stop_recording(self):
        """Stop the recording process"""
        self.is_recording = False
    
    def _ensure_output_directory(self):
        """Ensure output directory exists using enhanced storage configuration"""
        try:
            if self.storage_config:
                # Use enhanced directory creation
                result = self.storage_config.ensure_directories_enhanced()
                if not result.get('success', False):
                    logger.warning(f"Enhanced directory creation had issues: {result}")
                    # Fall back to basic directory creation
                    os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            else:
                # Basic directory creation as fallback
                os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to ensure output directory: {e}")
            # Try basic creation as last resort
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
    
    def _save_recording_enhanced(self):
        """Save recorded audio data to file with enhanced metadata calculation"""
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
            
            # PHASE 3 INTEGRATION: Calculate enhanced metadata
            metadata = self._calculate_recording_metadata(duration)
            
            self.recording_completed.emit(self.output_path, duration, metadata)
        
        except Exception as e:
            self.recording_error.emit(f"Failed to save recording: {str(e)}")
    
    def _calculate_recording_metadata(self, duration: float) -> Dict[str, Any]:
        """Calculate enhanced metadata for the recorded file"""
        metadata = {
            'duration': duration,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'recording_time': datetime.now().isoformat()
        }
        
        try:
            # PHASE 3 INTEGRATION: Use enhanced metadata calculator
            if os.path.exists(self.output_path):
                enhanced_metadata = self.metadata_calculator.calculate_metadata(self.output_path)
                metadata.update(enhanced_metadata)
            else:
                logger.warning(f"File not found for metadata calculation: {self.output_path}")
        except FileMetadataError as e:
            logger.error(f"Metadata calculation failed: {e}")
            metadata['metadata_error'] = str(e)
        except Exception as e:
            logger.error(f"Unexpected error in metadata calculation: {e}")
            metadata['metadata_error'] = f"Unexpected error: {str(e)}"
        
        return metadata


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


class EnhancedAudioRecorderManager(QObject):
    """Enhanced audio recorder manager with integrated storage system"""
    recording_started = Signal()
    recording_stopped = Signal(str, float, dict)  # file_path, duration, metadata
    recording_progress = Signal(float, float)  # duration, level
    recording_error = Signal(str)
    device_status_changed = Signal(bool)  # True if devices available
    storage_status_changed = Signal(bool)  # True if storage ready
    
    def __init__(self, environment: str = 'development'):
        super().__init__()
        self.recorder_thread: Optional[AudioRecorderThread] = None
        self.level_monitor: Optional[AudioLevelMonitor] = None
        self.is_recording = False
        
        # PHASE 3 INTEGRATION: Enhanced storage configuration
        self.environment = environment
        self.storage_config: Optional[StorageConfig] = None
        self.env_manager = EnvironmentManager()
        
        # Initialize enhanced storage
        self._initialize_enhanced_storage()
        
        # Validate audio devices on initialization
        self._validate_audio_devices()
    
    def _initialize_enhanced_storage(self):
        """Initialize enhanced storage configuration"""
        try:
            # Create environment-aware storage configuration
            self.storage_config = StorageConfig.from_environment(self.environment)
            
            # Get the raw recordings path using enhanced path management
            if hasattr(self.storage_config, 'get_path_for_type_enhanced'):
                path_result = self.storage_config.get_path_for_type_enhanced('raw')
                if 'path' in path_result:
                    self.output_directory = str(path_result['path'])
                else:
                    # Fall back to basic method
                    self.output_directory = str(self.storage_config.get_path_for_type('raw'))
            else:
                # Use basic method if enhanced not available
                self.output_directory = str(self.storage_config.get_path_for_type('raw'))
            
            # Validate storage configuration
            self._validate_storage_health()
            
            logger.info(f"Enhanced storage initialized for environment: {self.environment}")
            logger.info(f"Recording directory: {self.output_directory}")
            
        except StorageConfigValidationError as e:
            logger.error(f"Storage configuration validation failed: {e}")
            self.storage_config = None
            self.output_directory = "recordings/raw"  # Fallback
            self.storage_status_changed.emit(False)
        except Exception as e:
            logger.error(f"Enhanced storage initialization failed: {e}")
            self.storage_config = None
            self.output_directory = "recordings/raw"  # Fallback
            self.storage_status_changed.emit(False)
    
    def _validate_storage_health(self):
        """Validate storage health and readiness"""
        try:
            if self.storage_config:
                # Check storage info
                storage_info = self.storage_config.get_storage_info()
                free_space_mb = storage_info.get('free_mb', 0)
                
                # Check if we have sufficient space (minimum 100MB for recording)
                min_space_required = 100
                if free_space_mb < min_space_required:
                    logger.warning(f"Low disk space: {free_space_mb}MB available, {min_space_required}MB required")
                    self.storage_status_changed.emit(False)
                else:
                    logger.info(f"Storage health OK: {free_space_mb}MB available")
                    self.storage_status_changed.emit(True)
                
                # Validate path permissions if enhanced features available
                if hasattr(self.storage_config, 'validate_path_permissions'):
                    perm_result = self.storage_config.validate_path_permissions()
                    raw_perms = perm_result.get('raw', {})
                    if not raw_perms.get('writable', False):
                        logger.error("Raw recordings directory is not writable")
                        self.storage_status_changed.emit(False)
            else:
                # Basic storage validation
                os.makedirs(self.output_directory, exist_ok=True)
                self.storage_status_changed.emit(True)
        
        except Exception as e:
            logger.error(f"Storage health validation failed: {e}")
            self.storage_status_changed.emit(False)
    
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
        """Start audio recording with enhanced storage validation"""
        if self.is_recording:
            self.recording_error.emit("Recording already in progress")
            return False
        
        # PHASE 3 INTEGRATION: Enhanced pre-flight checks
        if not self._validate_audio_devices():
            self.recording_error.emit("No audio input devices available")
            return False
        
        # Validate storage before recording
        if self.storage_config:
            try:
                # Check file constraints
                test_file_size = 10 * 1024 * 1024  # Estimate 10MB for recording
                storage_info = self.storage_config.get_storage_info()
                free_space_mb = storage_info.get('free_mb', 0)
                
                if free_space_mb * 1024 * 1024 < test_file_size * 2:  # 2x safety margin
                    self.recording_error.emit(f"Insufficient disk space: {free_space_mb}MB available")
                    return False
            
            except Exception as e:
                logger.warning(f"Storage validation failed, proceeding with basic checks: {e}")
        
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"recording_{timestamp}_{uuid.uuid4().hex[:8]}.wav"
            
            # Ensure .wav extension
            if not filename.lower().endswith('.wav'):
                filename += '.wav'
            
            output_path = os.path.join(self.output_directory, filename)
            
            # Create and start enhanced recorder thread
            self.recorder_thread = AudioRecorderThread(
                output_path, 
                sample_rate, 
                storage_config=self.storage_config
            )
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
    
    def get_storage_info(self) -> Dict[str, Any]:
        """Get enhanced storage information"""
        if self.storage_config:
            try:
                storage_info = self.storage_config.get_storage_info()
                storage_info['environment'] = self.environment
                storage_info['output_directory'] = self.output_directory
                
                # Add enhanced path info if available
                if hasattr(self.storage_config, 'get_enhanced_path_info'):
                    enhanced_info = self.storage_config.get_enhanced_path_info()
                    storage_info['enhanced_features'] = enhanced_info.get('available', False)
                
                return storage_info
            except Exception as e:
                logger.error(f"Failed to get enhanced storage info: {e}")
        
        # Fallback to basic info
        return {
            'environment': self.environment,
            'output_directory': self.output_directory,
            'enhanced_features': False
        }
    
    def _on_recording_started(self):
        """Handle recording start confirmation"""
        self.recording_started.emit()
    
    def _on_recording_completed(self, file_path: str, duration: float, metadata: Dict[str, Any]):
        """Handle recording completion with enhanced metadata"""
        self.is_recording = False
        # If running without a Qt application (headless script/test), persist the
        # recording metadata automatically so non-GUI callers get a DB row.
        try:
            from PySide6.QtWidgets import QApplication
            has_qt_app = QApplication.instance() is not None
        except Exception:
            has_qt_app = False

        if not has_qt_app:
            try:
                # Inject the application DB context so the service uses the same DB as the app
                from models.database import db_context as app_db_context
                svc = RecordingService(db_ctx=app_db_context)
                rec = svc.create_from_file(file_path)
                logger.info("Auto-created recording in DB (headless): %s", getattr(rec, 'id', None))
            except Exception:
                logger.exception("Failed to auto-persist recording metadata for %s", file_path)

        # Emit finished signal for any listeners (GUI or other)
        self.recording_stopped.emit(file_path, duration, metadata)
        
        # Log enhanced metadata
        logger.info(f"Recording completed: {file_path}")
        logger.info(f"Duration: {duration:.2f}s")
        logger.info(f"Metadata keys: {list(metadata.keys())}")
        
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


# Backward compatibility: Keep original class name as alias
AudioRecorderManager = EnhancedAudioRecorderManager
