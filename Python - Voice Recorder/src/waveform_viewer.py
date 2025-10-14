# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false
"""
WaveformViewer: Modular widget for displaying audio waveforms using Matplotlib in PySide6.

Improvements:
- Python 3.12/venv-friendly: version check + clear import error guidance.
- Robust audio handling: stereo->mono, amplitude normalization to [-1, 1].
- Performance: downsampling to cap plotted points for large files.
- Reliability: explicit exceptions, logging, and no global pyplot state.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional, cast

import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from numpy.typing import NDArray

# Defer pydub imports to runtime to avoid import-time failures when native
# audio libraries (audioop/pyaudioop) are missing. Tests that need full
# waveform functionality should run with pydub installed.
AudioSegment = None
_HAS_PYDUB = False
try:
    from pydub import AudioSegment  # type: ignore
    _HAS_PYDUB = True
except Exception:
    AudioSegment = None
    _HAS_PYDUB = False

# ---- Logging -----------------------------------------------------------------
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class WaveformViewer(QWidget):
    """
    A lightweight waveform preview widget.

    Parameters
    ----------
    file_path : str
        Path to an audio file readable by pydub/ffmpeg.
    parent : QWidget | None
        Optional Qt parent.
    max_points : int
        Maximum number of samples to plot (downsamples if exceeded).
    theme_color : str | None
        Matplotlib color for the line. If None, uses default cycle.
    """

    def __init__(
        self,
        file_path: str,
        parent: Optional[QWidget] = None,
        *,
        max_points: int = 200_000,
        theme_color: Optional[str] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Waveform Preview")

        # Python 3.12 guidance (non-fatal)
        if sys.version_info < (3, 12):
            logger.warning(
                "Detected Python %s.%s; recommend Python 3.12 in a virtual environment for this app.",
                sys.version_info.major, sys.version_info.minor
            )

        self._max_points = max_points
        self._theme_color = theme_color

        layout = QVBoxLayout(self)
        self._figure: Figure = Figure(figsize=(8, 3), tight_layout=True)
        self._canvas = FigureCanvas(self._figure)
        layout.addWidget(self._canvas)
        # Create and reuse a single Axes
        self._ax: Axes = self._figure.add_subplot(111)

        if _HAS_PYDUB:
            try:
                self._plot_waveform(Path(file_path))
            except Exception as exc:
                logger.exception("Failed to render waveform: %s", exc)
                # Render a friendly error state on the canvas
                self._ax.clear()
                self._ax.text(0.5, 0.5, f"Error loading audio:\n{exc}", ha="center", va="center")
                self._ax.set_axis_off()
                self._canvas.draw()
        else:
            logger.info("pydub not available; WaveformViewer will be a placeholder.")
            self._ax.clear()
            self._ax.text(0.5, 0.5, "Waveform unavailable (pydub missing)", ha="center", va="center")
            self._ax.set_axis_off()
            self._canvas.draw()

    # ---- Core logic ----------------------------------------------------------

    def _plot_waveform(self, file_path: Path) -> None:
        self._validate_path(file_path)
        audio = self._load_audio(file_path)
        samples, rate = self._extract_normalized_mono_samples(audio)

        if samples.size == 0:
            raise ValueError("Audio contained no samples.")

        times = self._build_time_axis(samples.size, rate)
        x, y = self._downsample(times, samples, self._max_points)
        self._ax.clear()
        if self._theme_color:
            self._ax.plot(x, y, linewidth=0.8, color=self._theme_color)
        else:
            self._ax.plot(x, y, linewidth=0.8)
        self._ax.set_title("Waveform")
        self._ax.set_xlabel("Time (s)")
        self._ax.set_ylabel("Amplitude (normalized)")
        self._ax.grid(True, alpha=0.2)
        self._canvas.draw()

    @staticmethod
    def _validate_path(path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        if not path.is_file():
            raise ValueError(f"Not a file: {path}")

    @staticmethod
    def _load_audio(path: Path) -> "AudioSegment":
        # pydub uses ffmpeg under the hood; ensure ffmpeg is available in PATH
        logger.info("Loading audio: %s", path)
        if not _HAS_PYDUB or AudioSegment is None:
            raise ImportError("pydub not available; cannot load audio")
        return cast("AudioSegment", AudioSegment.from_file(path.as_posix()))

    @staticmethod
    def _extract_normalized_mono_samples(audio: "AudioSegment") -> tuple[NDArray[np.float32], int]:
        """
        Returns (samples_float32, sample_rate). Samples normalized to [-1, 1].
        If stereo+, averages channels into mono for a clean, quick preview.
        """
        rate = int(audio.frame_rate)
        array = np.array(audio.get_array_of_samples(), dtype=np.int32)

        # If multi-channel, reshape and average to mono:
        channels = int(audio.channels)
        if channels > 1:
            # shape: (num_frames, channels) -> mean across channels
            frames = array.reshape(-1, channels)
            array = frames.mean(axis=1)

        # Normalize by sample width (8/16/24/32-bit)
        # pydub sample_width is in bytes
        sw = int(audio.sample_width)
        max_int = float(2 ** (8 * sw - 1))
        samples = np.asarray(array, dtype=np.float32) / max_int
        # Clip to guard against any rounding overflow
        np.clip(samples, -1.0, 1.0, out=samples)
        return samples, rate

    @staticmethod
    def _build_time_axis(n: int, rate: int) -> NDArray[np.float32]:
        duration = n / rate
        return np.linspace(0.0, duration, num=n, dtype=np.float32, endpoint=False)

    @staticmethod
    def _downsample(
        x: NDArray[np.float32],
        y: NDArray[np.float32],
        max_points: int,
    ) -> tuple[NDArray[np.float32], NDArray[np.float32]]:
        """
        Simple decimation to cap points for plotting responsiveness.
        For production, consider min/max aggregation per bucket for more detail.
        """
        n = x.size
        if n <= max_points:
            return x, y
        step = max(1, n // max_points)
        return x[::step], y[::step]
