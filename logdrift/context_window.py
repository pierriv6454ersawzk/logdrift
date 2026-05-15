"""Context window: keeps N lines before/after a matching event for richer output."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ContextWindowConfig:
    before: int = 2
    after: int = 2

    def __post_init__(self) -> None:
        if self.before < 0:
            raise ValueError("before must be >= 0")
        if self.after < 0:
            raise ValueError("after must be >= 0")


@dataclass
class ContextCapture:
    trigger_line: str
    before: List[str]
    after: List[str]

    def all_lines(self) -> List[str]:
        """Return before + trigger + after as a flat list."""
        return list(self.before) + [self.trigger_line] + list(self.after)


class ContextWindow:
    """Buffers lines and emits ContextCapture objects when a trigger fires."""

    def __init__(self, config: Optional[ContextWindowConfig] = None) -> None:
        self._cfg = config or ContextWindowConfig()
        self._before: deque[str] = deque(maxlen=self._cfg.before)
        self._pending: List[_PendingCapture] = []

    def feed(self, line: str, is_trigger: bool = False) -> List[ContextCapture]:
        """Feed a line; returns any completed ContextCapture objects."""
        completed: List[ContextCapture] = []

        # Deliver line to all pending captures that still need after-lines.
        still_pending: List[_PendingCapture] = []
        for pc in self._pending:
            pc.after.append(line)
            if len(pc.after) >= self._cfg.after:
                completed.append(pc.to_capture())
            else:
                still_pending.append(pc)
        self._pending = still_pending

        if is_trigger:
            pc = _PendingCapture(
                trigger_line=line,
                before=list(self._before),
                after=[],
                needed=self._cfg.after,
            )
            if self._cfg.after == 0:
                completed.append(pc.to_capture())
            else:
                self._pending.append(pc)

        self._before.append(line)
        return completed

    def flush(self) -> List[ContextCapture]:
        """Flush any pending captures that have not received enough after-lines."""
        flushed = [pc.to_capture() for pc in self._pending]
        self._pending.clear()
        return flushed


@dataclass
class _PendingCapture:
    trigger_line: str
    before: List[str]
    after: List[str] = field(default_factory=list)
    needed: int = 0

    def to_capture(self) -> ContextCapture:
        return ContextCapture(
            trigger_line=self.trigger_line,
            before=self.before,
            after=list(self.after),
        )
