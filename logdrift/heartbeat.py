"""Heartbeat monitor: detects silence (no log lines) over a configurable window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Optional


@dataclass
class HeartbeatConfig:
    silence_threshold_seconds: float = 10.0
    check_interval_seconds: float = 1.0

    def __post_init__(self) -> None:
        if self.silence_threshold_seconds <= 0:
            raise ValueError("silence_threshold_seconds must be positive")
        if self.check_interval_seconds <= 0:
            raise ValueError("check_interval_seconds must be positive")


@dataclass
class HeartbeatState:
    last_seen_at: float
    is_silent: bool = False
    silence_started_at: Optional[float] = None


class HeartbeatMonitor:
    """Tracks the last time a line was seen and fires callbacks on silence."""

    def __init__(
        self,
        config: HeartbeatConfig,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config
        self._clock = clock
        self._state = HeartbeatState(last_seen_at=clock())
        self._on_silence_callbacks: list[Callable[[float], None]] = []
        self._on_resume_callbacks: list[Callable[[float], None]] = []

    def add_on_silence(self, cb: Callable[[float], None]) -> None:
        """Register a callback fired when silence begins. Receives silence duration."""
        self._on_silence_callbacks.append(cb)

    def add_on_resume(self, cb: Callable[[float], None]) -> None:
        """Register a callback fired when log activity resumes."""
        self._on_resume_callbacks.append(cb)

    def record_line(self) -> None:
        """Call whenever a log line is received."""
        now = self._clock()
        if self._state.is_silent:
            self._state.is_silent = False
            self._state.silence_started_at = None
            for cb in self._on_resume_callbacks:
                cb(now)
        self._state.last_seen_at = now

    def check(self) -> bool:
        """Check for silence. Returns True if currently silent."""
        now = self._clock()
        elapsed = now - self._state.last_seen_at
        if elapsed >= self._config.silence_threshold_seconds:
            if not self._state.is_silent:
                self._state.is_silent = True
                self._state.silence_started_at = now
                for cb in self._on_silence_callbacks:
                    cb(elapsed)
            return True
        return False

    @property
    def is_silent(self) -> bool:
        return self._state.is_silent

    @property
    def seconds_since_last_line(self) -> float:
        return self._clock() - self._state.last_seen_at
