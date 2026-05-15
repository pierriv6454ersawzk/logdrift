"""Tracks per-pattern or per-label line rates over a sliding window."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

from logdrift.rate_monitor import RateWindow


@dataclass
class LineRateTrackerConfig:
    window_seconds: float = 60.0
    max_keys: int = 256

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.max_keys < 1:
            raise ValueError("max_keys must be at least 1")


@dataclass
class RateEntry:
    window: RateWindow
    total: int = 0


class LineRateTracker:
    """Maintains a RateWindow per key (e.g. label, tag, or pattern)."""

    def __init__(
        self,
        config: Optional[LineRateTrackerConfig] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self._config = config or LineRateTrackerConfig()
        self._clock = clock
        self._entries: Dict[str, RateEntry] = {}

    def record(self, key: str) -> None:
        """Record one event for the given key."""
        if key not in self._entries:
            if len(self._entries) >= self._config.max_keys:
                return
            window = (
                RateWindow(self._config.window_seconds, clock=self._clock)
                if self._clock is not None
                else RateWindow(self._config.window_seconds)
            )
            self._entries[key] = RateEntry(window=window)
        entry = self._entries[key]
        entry.window.record()
        entry.total += 1

    def rate(self, key: str) -> float:
        """Return the current events-per-second rate for the given key."""
        if key not in self._entries:
            return 0.0
        return self._entries[key].window.current_rate()

    def total(self, key: str) -> int:
        """Return the total number of events ever recorded for the given key."""
        if key not in self._entries:
            return 0
        return self._entries[key].total

    def all_rates(self) -> Dict[str, float]:
        """Return a snapshot of current rates for all tracked keys."""
        return {key: entry.window.current_rate() for key, entry in self._entries.items()}

    def keys(self) -> list:
        return list(self._entries.keys())

    @classmethod
    def from_config(cls, config: LineRateTrackerConfig, clock: Optional[Callable[[], float]] = None) -> "LineRateTracker":
        return cls(config=config, clock=clock)
