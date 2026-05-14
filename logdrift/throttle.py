"""Rate-based throttle to suppress repeated anomaly alerts within a cooldown window."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional


@dataclass
class ThrottleConfig:
    cooldown_seconds: float = 60.0
    max_per_window: int = 3
    window_seconds: float = 300.0

    def __post_init__(self) -> None:
        if self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        if self.max_per_window < 1:
            raise ValueError("max_per_window must be at least 1")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


class AlertThrottle:
    """Decides whether an alert for a given key should be suppressed."""

    def __init__(
        self,
        config: Optional[ThrottleConfig] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._config = config or ThrottleConfig()
        self._clock = clock
        # key -> list of emit timestamps within the current window
        self._emit_times: Dict[str, list] = {}
        # key -> timestamp of last emitted alert
        self._last_emit: Dict[str, float] = {}

    def should_suppress(self, key: str) -> bool:
        """Return True if the alert for *key* should be suppressed."""
        now = self._clock()
        self._evict_old(key, now)

        last = self._last_emit.get(key)
        if last is not None and (now - last) < self._config.cooldown_seconds:
            return True

        times = self._emit_times.get(key, [])
        if len(times) >= self._config.max_per_window:
            return True

        return False

    def record_emit(self, key: str) -> None:
        """Record that an alert for *key* was emitted right now."""
        now = self._clock()
        self._evict_old(key, now)
        self._emit_times.setdefault(key, []).append(now)
        self._last_emit[key] = now

    def reset(self, key: str) -> None:
        """Clear throttle state for *key*."""
        self._emit_times.pop(key, None)
        self._last_emit.pop(key, None)

    def _evict_old(self, key: str, now: float) -> None:
        cutoff = now - self._config.window_seconds
        times = self._emit_times.get(key)
        if times:
            self._emit_times[key] = [t for t in times if t > cutoff]
