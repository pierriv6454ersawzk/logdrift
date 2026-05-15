"""Exports runtime metrics (rates, anomaly counts) to a simple in-memory or file-based sink."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional


@dataclass
class MetricSnapshot:
    timestamp: float
    lines_processed: int
    anomaly_count: int
    current_rate: float
    spike_count: int

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "lines_processed": self.lines_processed,
            "anomaly_count": self.anomaly_count,
            "current_rate": round(self.current_rate, 4),
            "spike_count": self.spike_count,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())


class MetricExporter:
    """Accumulates pipeline metrics and exports snapshots on demand or to a file."""

    def __init__(
        self,
        clock: Callable[[], float] = time.time,
        output_path: Optional[Path] = None,
    ) -> None:
        self._clock = clock
        self._output_path = output_path
        self._lines_processed: int = 0
        self._anomaly_count: int = 0
        self._spike_count: int = 0
        self._last_rate: float = 0.0

    def record_line(self) -> None:
        self._lines_processed += 1

    def record_anomaly(self, *, is_spike: bool = False) -> None:
        self._anomaly_count += 1
        if is_spike:
            self._spike_count += 1

    def update_rate(self, rate: float) -> None:
        self._last_rate = rate

    def snapshot(self) -> MetricSnapshot:
        return MetricSnapshot(
            timestamp=self._clock(),
            lines_processed=self._lines_processed,
            anomaly_count=self._anomaly_count,
            current_rate=self._last_rate,
            spike_count=self._spike_count,
        )

    def export(self) -> MetricSnapshot:
        snap = self.snapshot()
        if self._output_path is not None:
            self._output_path.write_text(snap.to_json() + "\n")
        return snap

    def reset(self) -> None:
        self._lines_processed = 0
        self._anomaly_count = 0
        self._spike_count = 0
        self._last_rate = 0.0
