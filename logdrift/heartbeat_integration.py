"""Integrates HeartbeatMonitor into the log pipeline."""

from __future__ import annotations

import time
from typing import Callable, Optional

from logdrift.heartbeat import HeartbeatConfig, HeartbeatMonitor


class HeartbeatIntegration:
    """Wraps HeartbeatMonitor for use in a processing pipeline.

    Call ``process(line)`` for every incoming log line, and
    ``tick()`` periodically (e.g. from a background thread or event loop)
    to trigger silence detection.
    """

    def __init__(
        self,
        config: HeartbeatConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._monitor = HeartbeatMonitor(config, clock=clock)
        self._lines_seen: int = 0

    # ------------------------------------------------------------------
    # Pipeline interface
    # ------------------------------------------------------------------

    def process(self, line: str) -> str:
        """Record a line and return it unchanged."""
        self._monitor.record_line()
        self._lines_seen += 1
        return line

    def tick(self) -> bool:
        """Check for silence. Returns True if currently silent."""
        return self._monitor.check()

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def add_on_silence(self, cb: Callable[[float], None]) -> None:
        self._monitor.add_on_silence(cb)

    def add_on_resume(self, cb: Callable[[float], None]) -> None:
        self._monitor.add_on_resume(cb)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def is_silent(self) -> bool:
        return self._monitor.is_silent

    @property
    def lines_seen(self) -> int:
        return self._lines_seen

    @property
    def seconds_since_last_line(self) -> float:
        return self._monitor.seconds_since_last_line

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(
        cls,
        threshold: float = 10.0,
        check_interval: float = 1.0,
        clock: Optional[Callable[[], float]] = None,
    ) -> "HeartbeatIntegration":
        cfg = HeartbeatConfig(
            silence_threshold_seconds=threshold,
            check_interval_seconds=check_interval,
        )
        kw = {"clock": clock} if clock is not None else {}
        return cls(cfg, **kw)
