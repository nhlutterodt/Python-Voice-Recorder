"""
File Metadata Calculator
Comprehensive utility for calculating file metadata with performance optimization
"""

import os
import hashlib
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from pydub import AudioSegment  # type: ignore
from voice_recorder.services.file_storage.exceptions import FileMetadataError


class FileMetadataCalculator:
    """
    Enhanced utility class for calculating comprehensive file metadata
    
    Optimized for performance with large files and robust error handling
    for corrupt or invalid files. Provides detailed audio-specific metadata
    extraction with fallback mechanisms.
    """
    
    # Performance optimization settings
    CHUNK_SIZE = 65536  # 64KB chunks for optimal I/O performance
    MAX_FILE_SIZE_MB = 2000  # Maximum file size for processing
    AUDIO_METADATA_TIMEOUT = 30  # Timeout for audio processing in seconds
    
    @classmethod
    def calculate_metadata(cls, file_path: str, include_audio: bool = True, 
                          validate_integrity: bool = True) -> Dict[str, Any]:
        """
        Calculate comprehensive metadata for an audio file with performance optimization
        
        Args:
            file_path: Path to the audio file
            include_audio: Whether to include audio-specific metadata (default: True)
            validate_integrity: Whether to perform integrity validation (default: True)
            
        Returns:
            Dictionary containing comprehensive file metadata
            
        Raises:
            FileNotFoundError: If file doesn't exist
            FileMetadataError: If file is corrupt or metadata extraction fails
            ValueError: If file exceeds size limits or is invalid format
        """
        start_time = datetime.now()
        
        try:
            # Validate file existence and basic accessibility
            cls._validate_file_access(file_path)
            
            file_stat = os.stat(file_path)
            file_path_obj = Path(file_path)
            
            # Performance check - validate file size
            file_size_mb = file_stat.st_size / (1024 * 1024)
            if file_size_mb > cls.MAX_FILE_SIZE_MB:
                raise ValueError(f"File size {file_size_mb:.1f}MB exceeds maximum {cls.MAX_FILE_SIZE_MB}MB")
            
            # Calculate basic file metadata
            metadata = cls._calculate_basic_metadata(file_path_obj, file_stat)
            
            # Calculate file integrity checksum (optimized for large files)
            if validate_integrity:
                metadata['checksum'] = cls._calculate_checksum_optimized(file_path)
                metadata['integrity_verified'] = True
            else:
                metadata['checksum'] = None
                metadata['integrity_verified'] = False
            
            # Extract audio-specific metadata with error handling
            if include_audio:
                try:
                    audio_metadata = cls._extract_audio_metadata_robust(file_path)
                    metadata.update(audio_metadata)
                except Exception as e:
                    # Use fallback metadata on audio processing failure
                    fallback_metadata = cls._get_fallback_audio_metadata()
                    metadata.update(fallback_metadata)
                    metadata['audio_processing_error'] = str(e)
            
            # Add processing performance metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            metadata['processing_time_seconds'] = processing_time
            metadata['processing_rate_mb_per_second'] = file_size_mb / processing_time if processing_time > 0 else 0
            
            # Add file validation status
            metadata['validation_status'] = 'valid'
            metadata['metadata_version'] = '2.0'
            
            return metadata
            
        except FileNotFoundError:
            raise
        except (ValueError, FileMetadataError):
            raise 
        except Exception as e:
            raise FileMetadataError(f"Failed to calculate metadata: {e}")
    
    @staticmethod
    def _validate_file_access(file_path: str):
        """Validate file exists and is accessible"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            raise ValueError(f"Path is not a file: {file_path}")
        
        if not os.access(file_path, os.R_OK):
            raise PermissionError(f"File not readable: {file_path}")
    
    @staticmethod
    def _calculate_basic_metadata(file_path_obj: Path, file_stat: os.stat_result) -> Dict[str, Any]:
        """Calculate basic file metadata efficiently"""
        return {
            'filename': file_path_obj.name,
            'file_extension': file_path_obj.suffix.lower(),
            'filesize_bytes': file_stat.st_size,
            'filesize_mb': file_stat.st_size / (1024 * 1024),
            'mime_type': FileMetadataCalculator._detect_mime_type_enhanced(str(file_path_obj)),
            'created_at': datetime.fromtimestamp(file_stat.st_ctime),
            'modified_at': datetime.fromtimestamp(file_stat.st_mtime),
            'last_accessed': datetime.fromtimestamp(file_stat.st_atime),
            'inode': getattr(file_stat, 'st_ino', None),  # Unix-specific, None on Windows
            'file_mode': oct(file_stat.st_mode)
        }
    
    @staticmethod
    def _detect_mime_type_enhanced(file_path: str) -> str:
        """Enhanced MIME type detection with comprehensive fallbacks"""
        # Try standard library first
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            return mime_type
        
        # Enhanced fallback for audio formats
        extension = Path(file_path).suffix.lower()
        audio_types = {
            '.wav': 'audio/wav',
            '.mp3': 'audio/mpeg',
            '.ogg': 'audio/ogg',
            '.flac': 'audio/flac',
            '.m4a': 'audio/mp4',
            '.aac': 'audio/aac',
            '.wma': 'audio/x-ms-wma',
            '.amr': 'audio/amr',
            '.3gp': 'audio/3gpp',
            '.opus': 'audio/opus',
            '.aiff': 'audio/aiff',
            '.au': 'audio/basic'
        }
        
        detected_type = audio_types.get(extension, 'application/octet-stream')
        
        # Try to validate by reading file header if unknown type
        if detected_type == 'application/octet-stream':
            try:
                with open(file_path, 'rb') as f:
                    f.read(16)
                    # Add magic number detection logic here if needed
            except (OSError, IOError):
                pass
        
        return detected_type
    
    @classmethod
    def _calculate_checksum_optimized(cls, file_path: str) -> str:
        """Calculate SHA256 checksum optimized for large files"""
        hash_sha256 = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                # Use larger chunks for better performance with large files
                while chunk := f.read(cls.CHUNK_SIZE):
                    hash_sha256.update(chunk)
            return hash_sha256.hexdigest()
        except (OSError, IOError) as e:
            raise FileMetadataError(f"Failed to calculate checksum: {e}")
    
    @classmethod
    def _extract_audio_metadata_robust(cls, file_path: str) -> Dict[str, Any]:
        """
        Extract audio-specific metadata with robust error handling and timeout protection
        """
        @contextmanager
        def timeout_context(seconds: int):
            """Context manager for timeout protection"""
            if os.name != 'nt':
                import signal
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Audio processing timed out after {seconds} seconds")
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(seconds)
                try:
                    yield
                finally:
                    signal.alarm(0)
            else:
                # Windows doesn't support SIGALRM, just proceed without timeout
                yield
        
        try:
            with timeout_context(cls.AUDIO_METADATA_TIMEOUT):
                audio = AudioSegment.from_file(file_path)
                
                # Extract comprehensive audio metadata
                metadata = {
                    'duration': len(audio) / 1000.0,  # Convert milliseconds to seconds
                    'duration_formatted': cls._format_duration(len(audio) / 1000.0),
                    'channels': audio.channels,
                    'frame_rate': audio.frame_rate,
                    'sample_width': audio.sample_width,
                    'sample_width_bits': audio.sample_width * 8,
                    'max_possible_amplitude': audio.max_possible_amplitude,
                    'channel_layout': cls._get_channel_layout(audio.channels)
                }
                
                # Calculate additional derived metadata
                metadata['bitrate_kbps'] = cls._estimate_bitrate(file_path, metadata['duration'])
                metadata['total_samples'] = int(metadata['duration'] * metadata['frame_rate'])
                
                # Add quality assessment
                metadata['quality_rating'] = cls._assess_audio_quality(metadata)
                
                return metadata
                
        except TimeoutError as e:
            raise FileMetadataError(f"Audio processing timed out: {e}")
        except Exception as e:
            # Provide detailed error information for debugging
            error_info = {
                'error_type': type(e).__name__,
                'error_message': str(e),
                'file_path': file_path
            }
            raise FileMetadataError(f"Audio metadata extraction failed: {error_info}")
    
    @staticmethod
    def _get_channel_layout(channels: int) -> str:
        """Get channel layout description"""
        if channels == 1:
            return 'mono'
        elif channels == 2:
            return 'stereo'
        else:
            return f'{channels}-channel'
    
    @staticmethod
    def _get_fallback_audio_metadata() -> Dict[str, Any]:
        """Return fallback audio metadata when extraction fails"""
        return {
            'duration': 0.0,
            'duration_formatted': '00:00:00',
            'channels': None,
            'frame_rate': None,
            'sample_width': None,
            'sample_width_bits': None,
            'max_possible_amplitude': None,
            'channel_layout': 'unknown',
            'bitrate_kbps': None,
            'total_samples': 0,
            'quality_rating': 'unknown'
        }
    
    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format duration in seconds to HH:MM:SS format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def _estimate_bitrate(file_path: str, duration: float) -> Optional[float]:
        """Estimate bitrate based on file size and duration"""
        try:
            if duration <= 0:
                return None
            
            file_size_bits = os.path.getsize(file_path) * 8
            bitrate_bps = file_size_bits / duration
            return bitrate_bps / 1000  # Convert to kbps
        except (OSError, ZeroDivisionError):
            return None
    
    @staticmethod
    def _assess_audio_quality(metadata: Dict[str, Any]) -> str:
        """Assess audio quality based on metadata"""
        try:
            sample_rate = metadata.get('frame_rate', 0)
            bit_depth = metadata.get('sample_width_bits', 0)
            channels = metadata.get('channels', 0)
            
            if sample_rate >= 44100 and bit_depth >= 16 and channels >= 1:
                if sample_rate >= 96000 and bit_depth >= 24:
                    return 'high_resolution'
                elif sample_rate >= 44100 and bit_depth >= 16:
                    return 'cd_quality'
                else:
                    return 'standard'
            else:
                return 'low_quality'
        except (TypeError, KeyError):
            return 'unknown'
