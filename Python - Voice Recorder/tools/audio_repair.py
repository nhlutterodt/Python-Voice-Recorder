#!/usr/bin/env python3
"""
Audio file repair utility for fixing corrupted or unsupported WAV files.

This script re-encodes problematic audio files into a standard format
that's compatible with the audio processing pipeline.
"""

import os
import subprocess
import sys
from pathlib import Path


def repair_audio_file(input_path: str, output_path: str = None, force: bool = False) -> bool:
    """
    Re-encode an audio file to standard WAV format.
    
    Args:
        input_path: Path to the problematic audio file
        output_path: Path for the output file (defaults to input_path with .repaired.wav extension)
        force: If True, overwrite existing output file
        
    Returns:
        True if repair succeeded, False otherwise
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        print(f"❌ Error: Input file not found: {input_path}")
        return False
    
    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}.repaired.wav"
    else:
        output_path = Path(output_path)
    
    if output_path.exists() and not force:
        print(f"❌ Error: Output file already exists: {output_path}")
        print(f"   Use --force to overwrite")
        return False
    
    print(f"🔧 Repairing audio file...")
    print(f"   Input:  {input_path}")
    print(f"   Output: {output_path}")
    
    # FFmpeg command to re-encode to standard PCM WAV
    # - acodec pcm_s16le: 16-bit signed little-endian PCM (universal format)
    # - ar 44100: 44.1kHz sample rate (standard)
    # - ac 2: Stereo (2 channels)
    cmd = [
        "ffmpeg",
        "-i", str(input_path),
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "2",
        "-y",  # Overwrite output file
        str(output_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if result.returncode == 0:
            size_kb = output_path.stat().st_size / 1024
            print(f"✅ Success! File repaired: {size_kb:.1f} KB")
            return True
        else:
            print(f"❌ FFmpeg error:")
            print(result.stderr)
            return False
            
    except FileNotFoundError:
        print("❌ Error: FFmpeg not found. Please install FFmpeg:")
        print("   Windows: choco install ffmpeg  (or download from ffmpeg.org)")
        print("   macOS:   brew install ffmpeg")
        print("   Linux:   sudo apt-get install ffmpeg")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def repair_directory(directory: str, pattern: str = "*.wav") -> int:
    """
    Repair all audio files in a directory matching a pattern.
    
    Args:
        directory: Path to directory containing audio files
        pattern: File pattern to match (default: *.wav)
        
    Returns:
        Number of files successfully repaired
    """
    dir_path = Path(directory)
    
    if not dir_path.is_dir():
        print(f"❌ Error: Directory not found: {directory}")
        return 0
    
    audio_files = list(dir_path.glob(pattern))
    
    if not audio_files:
        print(f"ℹ️  No audio files found matching pattern: {pattern}")
        return 0
    
    print(f"🔧 Found {len(audio_files)} audio file(s) to repair...\n")
    
    repaired_count = 0
    
    for i, audio_file in enumerate(audio_files, 1):
        print(f"[{i}/{len(audio_files)}] Processing: {audio_file.name}")
        output_path = audio_file.parent / f"{audio_file.stem}.repaired.wav"
        
        if repair_audio_file(str(audio_file), str(output_path), force=False):
            repaired_count += 1
        print()
    
    return repaired_count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Audio File Repair Utility")
        print("=" * 50)
        print("\nUsage:")
        print("  python audio_repair.py <input_file> [output_file]")
        print("  python audio_repair.py --dir <directory> [--pattern *.wav]")
        print("\nExamples:")
        print("  python audio_repair.py corrupted.wav")
        print("  python audio_repair.py corrupted.wav fixed.wav")
        print("  python audio_repair.py --dir recordings/raw")
        sys.exit(0)
    
    if sys.argv[1] == "--dir":
        if len(sys.argv) < 3:
            print("Error: --dir requires a directory path")
            sys.exit(1)
        directory = sys.argv[2]
        pattern = sys.argv[3] if len(sys.argv) > 3 else "*.wav"
        count = repair_directory(directory, pattern)
        print(f"✅ Repaired {count} audio file(s)")
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else None
        success = repair_audio_file(input_file, output_file)
        sys.exit(0 if success else 1)
