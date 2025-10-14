from typing import Any, Callable, Optional, Protocol


class QThread:
    def start(self) -> None: ...


class Signal:
    def __init__(self, *args: Any): ...
    def connect(self, slot: Callable[..., Any]) -> None: ...
    def emit(self, *args: Any) -> None: ...


class QObject:
    pass
