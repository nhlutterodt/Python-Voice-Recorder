# audio_processing.py
# Enhanced audio processing with asynchronous operations and memory efficiency

from PySide6.QtCore import QThread, Signal, QObject
from PySide6.QtWidgets import QProgressDialog, QApplication
from pydub import AudioSegment  # type: ignore
import wave
import os
import time
from typing import Optional, cast


class AudioLoaderThread(QThread):
    """Asynchronous audio file loader to prevent UI blocking"""
    audio_loaded = Signal(AudioSegment, str)
    error_occurred = Signal(str)
    progress_updated = Signal(int, str)
    
    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path
    
    def run(self):
        """Load audio file in background thread"""
        try:
            self.progress_updated.emit(10, "Opening audio file...")
            
            # Check file exists and is accessible
            if not os.path.exists(self.file_path):
                raise FileNotFoundError(f"Audio file not found: {self.file_path}")
                
            self.progress_updated.emit(30, "Reading audio data...")
            
            # Load audio segment with pydub
            audio_segment = cast(AudioSegment, AudioSegment.from_wav(self.file_path))
            
            self.progress_updated.emit(70, "Processing audio metadata...")
            
            # Simulate additional processing time for larger files
            file_size_mb = os.path.getsize(self.file_path) / (1024 * 1024)
            if file_size_mb > 10:  # Files larger than 10MB
                self.msleep(100)  # Small delay for large files
                
            self.progress_updated.emit(100, "Audio loaded successfully!")
            self.audio_loaded.emit(audio_segment, self.file_path)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class ChunkedAudioProcessor(QObject):
    """Memory-efficient audio processing for large files"""
    progress_updated = Signal(int, str)
    processing_completed = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, chunk_size_mb: int = 50):
        super().__init__()
        self.chunk_size = chunk_size_mb * 1024 * 1024  # Convert to bytes
    
    def process_trim_chunked(self, file_path: str, start_ms: int, end_ms: int, output_path: str):
        """Process trim operation in memory-efficient chunks"""
        try:
            self.progress_updated.emit(0, "Initializing chunked processing...")
            
            with wave.open(file_path, 'rb') as wav_file:
                # Get audio properties
                frame_rate = wav_file.getframerate()
                sample_width = wav_file.getsampwidth()
                channels = wav_file.getnchannels()
                
                # Calculate frame positions
                start_frame = int(start_ms * frame_rate / 1000)
                end_frame = int(end_ms * frame_rate / 1000)
                total_frames = end_frame - start_frame
                
                self.progress_updated.emit(10, "Calculating chunk sizes...")
                
                # Calculate optimal chunk size
                bytes_per_frame = sample_width * channels
                frames_per_chunk = self.chunk_size // bytes_per_frame
                
                # Prepare output file
                with wave.open(output_path, 'wb') as output_wav:
                    output_wav.setnchannels(channels)
                    output_wav.setsampwidth(sample_width)
                    output_wav.setframerate(frame_rate)
                    
                    # Position at start frame
                    wav_file.setpos(start_frame)
                    
                    remaining_frames = total_frames
                    processed_frames = 0
                    
                    self.progress_updated.emit(20, "Processing audio chunks...")
                    
                    while remaining_frames > 0:
                        # Calculate chunk size for this iteration
                        current_chunk_size = min(frames_per_chunk, remaining_frames)
                        
                        # Read chunk data
                        chunk_data = wav_file.readframes(current_chunk_size)
                        if not chunk_data:
                            break
                            
                        # Write chunk to output
                        output_wav.writeframes(chunk_data)
                        
                        # Update progress
                        processed_frames += current_chunk_size
                        remaining_frames -= current_chunk_size
                        progress = 20 + int((processed_frames / total_frames) * 70)
                        
                        self.progress_updated.emit(
                            progress, 
                            f"Processed {processed_frames / frame_rate:.1f}s of audio..."
                        )
                        
                        # Allow other processes to run
                        QApplication.processEvents()
                    
                    self.progress_updated.emit(95, "Finalizing output file...")
                    
            self.progress_updated.emit(100, "Chunked processing completed!")
            self.processing_completed.emit(output_path)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class AudioTrimProcessor(QThread):
    """Background audio trimming with progress feedback"""
    progress_updated = Signal(int, str)
    trim_completed = Signal(str)
    error_occurred = Signal(str)
    
    def __init__(self, audio_segment: AudioSegment, start_ms: int, end_ms: int, output_path: str):
        super().__init__()
        self.audio_segment = audio_segment
        self.start_ms = start_ms
        self.end_ms = end_ms
        self.output_path = output_path
    
    def run(self):
        """Process trim operation in background"""
        try:
            self.progress_updated.emit(10, "Starting trim operation...")
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            
            self.progress_updated.emit(30, "Trimming audio segment...")
            
            # Perform the trim
            trimmed = cast(AudioSegment, self.audio_segment[self.start_ms:self.end_ms])
            
            self.progress_updated.emit(60, "Applying fade effects...")
            
            # Apply fade effects
            trimmed = trimmed.fade_in(250).fade_out(250)  # type: ignore
            
            self.progress_updated.emit(80, "Exporting audio file...")
            
            # Export the trimmed audio
            trimmed.export(self.output_path, format="wav")  # type: ignore
            
            self.progress_updated.emit(100, "Trim operation completed!")
            self.trim_completed.emit(self.output_path)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class ProgressDialog(QProgressDialog):
    """Enhanced progress dialog with cancellation support"""
    
    def __init__(self, operation_name: str, parent=None):
        super().__init__(f"{operation_name}...", "Cancel", 0, 100, parent)
        self.setWindowTitle("Processing Audio")
        self.setModal(True)
        self.setAutoClose(True)
        self.setAutoReset(True)
        self.setMinimumDuration(500)  # Show after 500ms
        
    def update_progress(self, value: int, message: str = ""):
        """Update progress with optional message"""
        self.setValue(value)
        if message:
            self.setLabelText(f"{message}")
        QApplication.processEvents()  # Keep UI responsive
        
    def is_cancelled(self) -> bool:
        """Check if user cancelled the operation"""
        return self.wasCanceled()
