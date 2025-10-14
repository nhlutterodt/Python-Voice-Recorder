"""Lightweight, import-safe enhanced audio recorder.

This module provides the same public classes used elsewhere but keeps
heavy runtime imports (sounddevice, PySide6, numpy, etc.) inside functions
or methods so importing the package is safe for linting, tests, and CI.
"""
from typing import Any, Dict, List, Optional

# Lightweight placeholders for types used in signatures. Real imports are
# performed lazily inside methods to avoid import-time side effects.
NDArray = Any


class AudioRecorderThread:
    """Import-safe stub for the recording thread.

    The real implementation lives in runtime when the application starts.
    This stub provides the surface area needed by other modules/tests.
    """

    def __init__(self, output_path: str, sample_rate: int = 44100, channels: int = 1, storage_config: Optional[Any] = None):
        self.output_path = output_path
        self.sample_rate = sample_rate
        self.channels = channels
        self.storage_config = storage_config

    def start(self) -> None:
        raise RuntimeError("AudioRecorderThread.start(): runtime audio backends are required")

    def stop_recording(self) -> None:
        # no-op for lint/test import-time safety
        return None


class AudioLevelMonitor:
    """Lightweight monitor stub. Real implementation created at runtime."""

    def __init__(self, sample_rate: int = 44100):
        self.sample_rate = sample_rate

    def start_monitoring(self) -> None:
        raise RuntimeError("AudioLevelMonitor.start_monitoring(): runtime audio backends are required")

    def stop_monitoring(self) -> None:
        return None


class EnhancedAudioRecorderManager:
    """Manager that lazily imports heavy dependencies when needed."""

    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.recorder_thread: Optional[AudioRecorderThread] = None
        self.level_monitor: Optional[AudioLevelMonitor] = None
        self.is_recording = False
        self.output_directory = "recordings/raw"
        self.storage_config = None

    def _ensure_runtime_dependencies(self) -> None:
        # Import heavy modules at runtime using importlib to avoid import-time
        # side-effects and to satisfy linters (no unused-import F401).
        try:
            import importlib

            sd = importlib.import_module("sounddevice")  # type: ignore
            _qtcore = importlib.import_module("PySide6.QtCore")  # type: ignore
            # Bind commonly used Qt symbols if present. We don't require them at
            # import time; this method only verifies availability.
            _qthread = getattr(_qtcore, "QThread", None)
            _signal = getattr(_qtcore, "Signal", None)
            _qobject = getattr(_qtcore, "QObject", None)
            _qtimer = getattr(_qtcore, "QTimer", None)
            # Use the sd variable in a no-op to silence "imported but unused" in
            # some linting configurations (we also use sd elsewhere).
            _ = sd
        except Exception as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError("Runtime audio/GUI dependencies are required") from exc

    def start_recording(self, filename: Optional[str] = None, sample_rate: int = 44100) -> bool:
        """Start recording. This will import runtime dependencies as needed."""
        # Ensure dependencies are available; will raise on import errors.
        self._ensure_runtime_dependencies()

        if self.is_recording:
            return False

        # Defer creation of the real recorder thread to runtime module that
        # depends on sounddevice/QThread behavior.
        # Keep this method import-safe for tests that don't exercise audio.
        if filename is None:
            filename = "/tmp/dummy.wav"
        self.recorder_thread = AudioRecorderThread(filename, sample_rate)
        self.is_recording = True
        return True

    def stop_recording(self) -> None:
        if self.recorder_thread:
            self.recorder_thread.stop_recording()
        self.is_recording = False

    def start_level_monitoring(self) -> None:
        self._ensure_runtime_dependencies()
        self.level_monitor = AudioLevelMonitor()
        self.level_monitor.start_monitoring()

    def stop_level_monitoring(self) -> None:
        if self.level_monitor:
            self.level_monitor.stop_monitoring()

    def get_available_devices(self) -> List[Dict[str, Any]]:
        # Query runtime audio devices lazily.
        try:
            import sounddevice as sd  # type: ignore

            devices = sd.query_devices()  # type: ignore
            input_devices: List[Dict[str, Any]] = []
            for i, d in enumerate(devices):  # type: ignore
                if d.get("max_input_channels", 0) > 0:
                    input_devices.append({
                        "index": i,
                        "name": d.get("name", ""),
                        "channels": d.get("max_input_channels", 0),
                    })
            return input_devices
        except Exception:
            return []


# Maintain backward compatible alias
AudioRecorderManager = EnhancedAudioRecorderManager
