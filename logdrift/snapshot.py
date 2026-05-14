"""Periodic snapshot writer for logdrift pipeline metrics."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class SnapshotData:
    timestamp: float
    current_rate: float
    baseline_rate: float
    event_count: int
    anomaly_count: int
    last_anomaly_score: Optional[float] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class SnapshotWriter:
    """Writes periodic metric snapshots to a file or callable sink."""

    def __init__(
        self,
        path: Optional[Path] = None,
        interval_seconds: float = 10.0,
        clock=None,
    ):
        self._path = path
        self._interval = interval_seconds
        self._clock = clock or time.monotonic
        self._last_written: float = 0.0
        self._snapshots: list[SnapshotData] = []

    def record(self, snapshot: SnapshotData) -> bool:
        """Record a snapshot if the interval has elapsed. Returns True if written."""
        now = self._clock()
        if now - self._last_written < self._interval:
            return False
        self._last_written = now
        self._snapshots.append(snapshot)
        if self._path is not None:
            self._flush_to_file(snapshot)
        return True

    def _flush_to_file(self, snapshot: SnapshotData) -> None:
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(snapshot.to_json() + "\n")

    def latest(self) -> Optional[SnapshotData]:
        return self._snapshots[-1] if self._snapshots else None

    def all_snapshots(self) -> list[SnapshotData]:
        return list(self._snapshots)

    def reset(self) -> None:
        self._snapshots.clear()
        self._last_written = 0.0
