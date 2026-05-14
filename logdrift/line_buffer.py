"""Rolling line buffer that retains the last N log lines for context."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Iterator, List


@dataclass
class LineBufferConfig:
    capacity: int = 100

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("capacity must be at least 1")


class LineBuffer:
    """Fixed-capacity ring buffer for recent log lines.

    Useful for attaching context to anomaly alerts — callers can
    snapshot the last *n* lines at the moment a spike is detected.
    """

    def __init__(self, config: LineBufferConfig | None = None) -> None:
        cfg = config or LineBufferConfig()
        self._capacity: int = cfg.capacity
        self._buf: Deque[str] = deque(maxlen=self._capacity)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def append(self, line: str) -> None:
        """Add *line* to the buffer, evicting the oldest entry if full."""
        self._buf.append(line)

    def clear(self) -> None:
        """Remove all stored lines."""
        self._buf.clear()

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    @property
    def capacity(self) -> int:
        return self._capacity

    def __len__(self) -> int:
        return len(self._buf)

    def __iter__(self) -> Iterator[str]:
        return iter(self._buf)

    def snapshot(self, n: int | None = None) -> List[str]:
        """Return up to *n* most-recent lines (all lines when *n* is None)."""
        lines = list(self._buf)
        if n is None:
            return lines
        if n < 0:
            raise ValueError("n must be non-negative")
        return lines[-n:] if n else []

    def is_full(self) -> bool:
        return len(self._buf) == self._capacity
