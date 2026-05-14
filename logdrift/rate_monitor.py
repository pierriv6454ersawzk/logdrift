"""Rate monitor module for detecting log line spikes in real-time."""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RateWindow:
    """Sliding window for tracking log event timestamps."""
    window_seconds: float = 60.0
    spike_multiplier: float = 3.0
    _timestamps: deque = field(default_factory=deque, init=False, repr=False)

    def record(self, timestamp: Optional[float] = None) -> None:
        """Record a new log event at the given (or current) timestamp."""
        ts = timestamp if timestamp is not None else time.monotonic()
        self._timestamps.append(ts)
        self._evict(ts)

    def _evict(self, now: float) -> None:
        """Remove timestamps outside the sliding window."""
        cutoff = now - self.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.popleft()

    @property
    def current_rate(self) -> float:
        """Return events-per-second over the current window."""
        if not self._timestamps:
            return 0.0
        now = time.monotonic()
        self._evict(now)
        elapsed = min(self.window_seconds, now - self._timestamps[0]) if self._timestamps else self.window_seconds
        if elapsed == 0:
            return 0.0
        return len(self._timestamps) / elapsed

    @property
    def count(self) -> int:
        """Return the number of events in the current window."""
        return len(self._timestamps)


class RateMonitor:
    """Monitors log ingestion rate and emits spike alerts."""

    def __init__(self, window_seconds: float = 60.0, spike_multiplier: float = 3.0):
        self.window = RateWindow(window_seconds=window_seconds, spike_multiplier=spike_multiplier)
        self._baseline_rate: float = 0.0
        self._samples: int = 0
        self._alpha: float = 0.1  # EMA smoothing factor

    def ingest(self, timestamp: Optional[float] = None) -> bool:
        """Record a log line and return True if a rate spike is detected."""
        self.window.record(timestamp)
        current = self.window.current_rate

        if self._samples < 10:
            # Warm-up phase: build baseline without alerting
            self._baseline_rate = current
            self._samples += 1
            return False

        is_spike = (
            self._baseline_rate > 0
            and current > self._baseline_rate * self.window.spike_multiplier
        )

        # Update baseline via exponential moving average
        self._baseline_rate = (
            self._alpha * current + (1 - self._alpha) * self._baseline_rate
        )
        self._samples += 1
        return is_spike

    @property
    def baseline_rate(self) -> float:
        return self._baseline_rate

    @property
    def current_rate(self) -> float:
        return self.window.current_rate
