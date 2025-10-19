"""Audio repair service for fixing corrupted audio files.

This service provides the core repair functionality used by both the CLI tool
and the GUI interface. It handles validation, repair, and batch processing.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Callable, Dict, Any

logger = logging.getLogger(__name__)


class AudioRepairService:
    """Service for detecting and repairing corrupted audio files."""

    DEFAULT_SAMPLE_RATE = 44100
    DEFAULT_CHANNELS = 2
    DEFAULT_CODEC = "pcm_s16le"

    @staticmethod
    def repair_audio_file(
        input_path: str,
        output_path: str,
        force: bool = False,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        channels: int = DEFAULT_CHANNELS,
    ) -> Dict[str, Any]:
        """
        Repair a corrupted audio file by re-encoding to standard format.

        Args:
            input_path: Path to the corrupted audio file
            output_path: Where to save the repaired file
            force: If True, overwrite existing output file
            sample_rate: Output sample rate (default: 44100 Hz)
            channels: Output channels (default: 2 stereo)

        Returns:
            Dictionary with keys:
                - success: bool - Whether repair succeeded
                - input_file: str - Input file path
                - output_file: str - Output file path
                - original_size: int - Original file size in bytes
                - repaired_size: int - Repaired file size in bytes
                - error: Optional[str] - Error message if failed
                - format_info: Dict - Audio format details
        """
        input_path = Path(input_path)
        output_path = Path(output_path)

        result = {
            "success": False,
            "input_file": str(input_path),
            "output_file": str(output_path),
            "original_size": 0,
            "repaired_size": 0,
            "error": None,
            "format_info": {},
        }

        # Validate input file
        if not input_path.exists():
            result["error"] = f"Input file not found: {input_path}"
            logger.error(result["error"])
            return result

        result["original_size"] = input_path.stat().st_size

        # Check if output exists
        if output_path.exists() and not force:
            result["error"] = f"Output file already exists: {output_path}"
            logger.warning(result["error"])
            return result

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build FFmpeg command
        cmd = [
            "ffmpeg",
            "-i",
            str(input_path),
            "-acodec",
            AudioRepairService.DEFAULT_CODEC,
            "-ar",
            str(sample_rate),
            "-ac",
            str(channels),
            "-y",  # Overwrite output
            str(output_path),
        ]

        try:
            logger.info(f"Repairing audio file: {input_path}")
            logger.debug(f"FFmpeg command: {' '.join(cmd)}")

            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            if process.returncode != 0:
                error_output = process.stderr or process.stdout
                result["error"] = f"FFmpeg error: {error_output[:200]}"
                logger.error(result["error"])
                return result

            # Check if output file was created
            if not output_path.exists():
                result["error"] = "Output file was not created"
                logger.error(result["error"])
                return result

            result["repaired_size"] = output_path.stat().st_size
            result["success"] = True
            result["format_info"] = {
                "codec": AudioRepairService.DEFAULT_CODEC,
                "sample_rate": sample_rate,
                "channels": channels,
            }

            logger.info(
                f"Successfully repaired: {input_path} → {output_path} "
                f"({result['repaired_size'] / 1024:.1f} KB)"
            )

            return result

        except FileNotFoundError:
            result["error"] = (
                "FFmpeg not found. Install with: "
                "choco install ffmpeg (Windows) or brew install ffmpeg (macOS)"
            )
            logger.error(result["error"])
            return result
        except Exception as e:
            result["error"] = f"Unexpected error: {str(e)}"
            logger.exception(result["error"])
            return result

    @staticmethod
    def validate_audio_file(file_path: str) -> Dict[str, Any]:
        """
        Check if an audio file is valid without attempting repair.

        Args:
            file_path: Path to audio file to validate

        Returns:
            Dictionary with keys:
                - is_valid: bool - Whether file is valid
                - error: Optional[str] - Error message if invalid
                - file_size: int - File size in bytes
        """
        file_path = Path(file_path)

        result = {"is_valid": False, "error": None, "file_size": 0}

        if not file_path.exists():
            result["error"] = "File not found"
            return result

        result["file_size"] = file_path.stat().st_size

        # Try to get audio info with ffprobe (or ffmpeg)
        cmd = [
            "ffmpeg",
            "-v",
            "error",
            "-select_streams",
            "a:0",
            "-show_entries",
            "stream=codec_type,codec_name,channels,sample_rate",
            "-of",
            "default=noprint_wrappers=1:nokey=1:noinputlist=1",
            str(file_path),
        ]

        try:
            process = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )

            if process.returncode == 0 and process.stdout.strip():
                result["is_valid"] = True
                return result

            result["error"] = "File appears to be corrupted or unsupported format"
            return result

        except FileNotFoundError:
            result["error"] = "FFmpeg not found"
            return result
        except Exception as e:
            result["error"] = str(e)
            return result

    @staticmethod
    def batch_repair(
        file_paths: list[str],
        output_dir: Optional[str] = None,
        use_suffix: bool = True,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Repair multiple audio files with progress reporting.

        Args:
            file_paths: List of audio file paths to repair
            output_dir: Directory to save repaired files (default: same as input)
            use_suffix: If True, append .repaired.wav to filename
            on_progress: Callback function(current, total, current_file)
            force: If True, overwrite existing files

        Returns:
            Dictionary with keys:
                - total: int - Total files processed
                - success: int - Successfully repaired
                - skipped: int - Files skipped (already valid)
                - failed: int - Files that failed to repair
                - results: List[Dict] - Individual file results
        """
        results = {
            "total": len(file_paths),
            "success": 0,
            "skipped": 0,
            "failed": 0,
            "results": [],
        }

        for index, file_path in enumerate(file_paths, 1):
            file_path = Path(file_path)

            # Progress callback
            if on_progress:
                on_progress(index, len(file_paths), file_path.name)

            # Check if file is already valid
            validation = AudioRepairService.validate_audio_file(str(file_path))
            if validation["is_valid"]:
                results["skipped"] += 1
                results["results"].append(
                    {
                        "file": str(file_path),
                        "status": "skipped",
                        "reason": "File is already valid",
                    }
                )
                logger.info(f"Skipped (valid): {file_path}")
                continue

            # Determine output path
            if use_suffix:
                output_path = file_path.parent / f"{file_path.stem}.repaired.wav"
            else:
                output_dir_path = Path(output_dir or file_path.parent)
                output_path = output_dir_path / f"{file_path.stem}.wav"

            # Repair file
            repair_result = AudioRepairService.repair_audio_file(
                str(file_path), str(output_path), force=force
            )

            if repair_result["success"]:
                results["success"] += 1
                results["results"].append(
                    {
                        "file": str(file_path),
                        "status": "repaired",
                        "output": str(output_path),
                        "size_before": repair_result["original_size"],
                        "size_after": repair_result["repaired_size"],
                    }
                )
            else:
                results["failed"] += 1
                results["results"].append(
                    {
                        "file": str(file_path),
                        "status": "failed",
                        "error": repair_result["error"],
                    }
                )

        return results

    @staticmethod
    def get_wav_files(directory: str, recursive: bool = True) -> list[str]:
        """
        Get list of WAV files in a directory.

        Args:
            directory: Directory path to scan
            recursive: If True, scan subdirectories

        Returns:
            List of WAV file paths
        """
        dir_path = Path(directory)

        if not dir_path.is_dir():
            logger.warning(f"Directory not found: {directory}")
            return []

        pattern = "**/*.wav" if recursive else "*.wav"
        files = [str(f) for f in dir_path.glob(pattern)]

        logger.info(f"Found {len(files)} WAV file(s) in {directory}")
        return files
