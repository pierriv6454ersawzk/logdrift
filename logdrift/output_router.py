"""output_router.py — Routes processed log events to multiple output sinks.

Allows a single processed event stream to fan out to several OutputSink
instances (e.g. stdout, a file, a socket) without duplicating pipeline logic.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from logdrift.output_sink import OutputSink


@dataclass
class RouterConfig:
    """Configuration for the OutputRouter.

    Attributes:
        stop_on_error: If True, a write failure in any sink raises immediately.
                       If False, errors are collected and the router continues.
        error_callback: Optional callable invoked with (sink, exception) on
                        write failure when stop_on_error is False.
    """

    stop_on_error: bool = False
    error_callback: Optional[Callable[[OutputSink, Exception], None]] = None

    def __post_init__(self) -> None:
        if self.error_callback is not None and not callable(self.error_callback):
            raise TypeError("error_callback must be callable or None")


class OutputRouter:
    """Fan-out router that writes each line to a list of OutputSink targets.

    Thread-safe: sinks may be added from one thread while another calls write.

    Example::

        router = OutputRouter(RouterConfig())
        router.add_sink(StreamSink(sys.stdout))
        router.add_sink(StreamSink(log_file))
        router.write("[INFO] server started")
        router.close()
    """

    def __init__(self, config: Optional[RouterConfig] = None) -> None:
        self._config: RouterConfig = config or RouterConfig()
        self._sinks: List[OutputSink] = []
        self._lock = threading.Lock()
        self._lines_written: int = 0
        self._error_count: int = 0

    # ------------------------------------------------------------------
    # Sink management
    # ------------------------------------------------------------------

    def add_sink(self, sink: OutputSink) -> None:
        """Register a new sink.  Duplicate instances are allowed."""
        with self._lock:
            self._sinks.append(sink)

    def remove_sink(self, sink: OutputSink) -> bool:
        """Unregister the first occurrence of *sink*.  Returns True if found."""
        with self._lock:
            try:
                self._sinks.remove(sink)
                return True
            except ValueError:
                return False

    @property
    def sink_count(self) -> int:
        """Number of currently registered sinks."""
        with self._lock:
            return len(self._sinks)

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------

    def write(self, line: str) -> None:
        """Write *line* to every registered sink.

        Behaviour on error is controlled by ``RouterConfig.stop_on_error``.
        """
        with self._lock:
            sinks = list(self._sinks)

        for sink in sinks:
            try:
                sink.write(line)
            except Exception as exc:  # noqa: BLE001
                self._error_count += 1
                if self._config.stop_on_error:
                    raise
                if self._config.error_callback is not None:
                    self._config.error_callback(sink, exc)

        self._lines_written += 1

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close all registered sinks and clear the sink list."""
        with self._lock:
            sinks, self._sinks = list(self._sinks), []

        for sink in sinks:
            try:
                sink.close()
            except Exception:  # noqa: BLE001
                pass  # best-effort close

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    @property
    def lines_written(self) -> int:
        """Total lines successfully dispatched (incremented once per write call)."""
        return self._lines_written

    @property
    def error_count(self) -> int:
        """Total sink write errors encountered across all sinks."""
        return self._error_count
