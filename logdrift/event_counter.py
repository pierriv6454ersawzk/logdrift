"""Tracks per-label or per-pattern event counts over a rolling window."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class CounterConfig:
    window_seconds: float = 60.0
    top_n: int = 10

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.top_n < 1:
            raise ValueError("top_n must be at least 1")


@dataclass
class CounterSnapshot:
    counts: Dict[str, int]
    timestamp: float

    def top(self, n: int) -> List[tuple]:
        """Return the top-n keys by count, descending."""
        return sorted(self.counts.items(), key=lambda kv: kv[1], reverse=True)[:n]

    def to_dict(self) -> dict:
        return {"timestamp": self.timestamp, "counts": dict(self.counts)}


class EventCounter:
    """Counts labelled events within a sliding time window."""

    def __init__(
        self,
        config: Optional[CounterConfig] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        import time

        self._config = config or CounterConfig()
        self._clock = clock or time.time
        # key -> list of timestamps
        self._events: Dict[str, List[float]] = defaultdict(list)

    def record(self, label: str) -> None:
        """Record an event for *label* at the current time."""
        now = self._clock()
        self._events[label].append(now)
        self._evict(label, now)

    def _evict(self, label: str, now: float) -> None:
        cutoff = now - self._config.window_seconds
        timestamps = self._events[label]
        # drop entries older than the window
        idx = 0
        while idx < len(timestamps) and timestamps[idx] < cutoff:
            idx += 1
        self._events[label] = timestamps[idx:]

    def count(self, label: str) -> int:
        """Return the number of events for *label* within the window."""
        now = self._clock()
        self._evict(label, now)
        return len(self._events[label])

    def snapshot(self) -> CounterSnapshot:
        """Return a snapshot of all current counts."""
        now = self._clock()
        for label in list(self._events):
            self._evict(label, now)
        counts = {k: len(v) for k, v in self._events.items() if v}
        return CounterSnapshot(counts=counts, timestamp=now)

    def reset(self) -> None:
        """Clear all recorded events."""
        self._events.clear()
