from typing import Any, Callable, Protocol


class _SignalLike(Protocol):
    def connect(self, slot: Callable[..., Any]) -> None: ...
    def emit(self, *args: Any, **kwargs: Any) -> None: ...


class AudioLoaderThread(Protocol):
    """Minimal stub for AudioLoaderThread used by enhanced_editor.

    Exposes signal attributes and a start() method.
    """
    audio_loaded: _SignalLike
    error_occurred: _SignalLike
    progress_updated: _SignalLike
    finished: _SignalLike

    def start(self) -> None: ...


class AudioTrimProcessor(Protocol):
    """Minimal stub for AudioTrimProcessor used by enhanced_editor.

    Exposes signal attributes and a start() method.
    """
    progress_updated: _SignalLike
    finished: _SignalLike

    def start(self) -> None: ...
