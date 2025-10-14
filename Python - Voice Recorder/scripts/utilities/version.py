# version.py
# Version management for Voice Recorder Pro

from dataclasses import dataclass
from typing import Dict, Any
import json
from pathlib import Path

@dataclass
class Version:
    """Version information for the application"""
    major: int
    minor: int
    patch: int
    build: str = ""
    
    def __str__(self) -> str:
        """String representation of version"""
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        if self.build:
            version_str += f"-{self.build}"
        return version_str
    
    @property
    def display_name(self) -> str:
        """Display name for the application"""
        return f"Voice Recorder Pro v{self}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "major": self.major,
            "minor": self.minor,
            "patch": self.patch,
            "build": self.build
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Version':
        """Create version from dictionary"""
        return cls(
            major=data["major"],
            minor=data["minor"], 
            patch=data["patch"],
            build=data.get("build", "")
        )

# Current application version
CURRENT_VERSION = Version(
    major=2,
    minor=0,
    patch=0,
    build="beta"
)

# Application metadata
APP_NAME = "Voice Recorder Pro"
APP_ORGANIZATION = "Voice Recorder Enhanced"
APP_DESCRIPTION = "Professional Audio Recording & Cloud Storage"

# UI Constants to avoid duplication
class UIConstants:
    """Constants for UI elements to avoid string duplication"""
    
    # Button text constants
    START_RECORDING = "🔴 Start Recording"
    STOP_RECORDING = "⏹️ Stop Recording"
    LOAD_AUDIO_FILE = "📁 Load Audio File"
    LOADING_AUDIO = "🔄 Loading..."
    TRIM_AND_SAVE = "✂️ Trim & Save"
    
    # Audio level constants
    AUDIO_LEVEL_EMPTY = "Level: -"
    AUDIO_LEVEL_PREFIX = "Level: "
    
    # Status messages
    READY_TO_RECORD = "Ready to record"
    RECORDING_IN_PROGRESS = "🔴 Recording in progress..."
    NO_DEVICES_FOUND = "⚠️ No audio input devices found"
    READY_TO_LOAD = "Ready to load audio file..."
    
    # Time format
    TIME_FORMAT_ZERO = "00:00"
    
    # File info format
    NO_FILE_LOADED = "No file loaded"

def get_version_info() -> Dict[str, Any]:
    """Get comprehensive version information"""
    return {
        "version": str(CURRENT_VERSION),
        "app_name": APP_NAME,
        "organization": APP_ORGANIZATION,
        "description": APP_DESCRIPTION,
        "build_info": CURRENT_VERSION.to_dict()
    }

def save_version_info(file_path: Path) -> None:
    """Save version information to file"""
    with open(file_path, 'w') as f:
        json.dump(get_version_info(), f, indent=2)

def load_version_info(file_path: Path) -> Dict[str, Any]:
    """Load version information from file"""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return get_version_info()
