"""Deduplication filter that suppresses repeated identical log lines within a time window."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from time import monotonic
from typing import Callable, Optional


@dataclass
class DedupConfig:
    window_seconds: float = 5.0
    max_tracked: int = 512

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.max_tracked < 1:
            raise ValueError("max_tracked must be at least 1")


class DedupFilter:
    """Suppresses duplicate log lines seen within a sliding time window.

    Uses an OrderedDict to track the last-seen timestamp for each unique line.
    When the cache exceeds *max_tracked* entries the oldest entry is evicted
    regardless of its age, preventing unbounded memory growth.
    """

    def __init__(
        self,
        config: Optional[DedupConfig] = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._config = config or DedupConfig()
        self._clock = clock
        # Maps line -> timestamp of first occurrence in current window
        self._seen: OrderedDict[str, float] = OrderedDict()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_pass(self, line: str) -> bool:
        """Return True if *line* should be forwarded, False if it is a duplicate."""
        now = self._clock()
        self._evict_expired(now)

        if line in self._seen:
            return False

        # Enforce max_tracked cap before inserting
        if len(self._seen) >= self._config.max_tracked:
            self._seen.popitem(last=False)

        self._seen[line] = now
        return True

    def reset(self) -> None:
        """Clear all tracked lines immediately."""
        self._seen.clear()

    @property
    def tracked_count(self) -> int:
        """Number of unique lines currently tracked."""
        return len(self._seen)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _evict_expired(self, now: float) -> None:
        cutoff = now - self._config.window_seconds
        # OrderedDict preserves insertion order; oldest entries are first
        while self._seen:
            oldest_line, ts = next(iter(self._seen.items()))
            if ts <= cutoff:
                del self._seen[oldest_line]
            else:
                break
