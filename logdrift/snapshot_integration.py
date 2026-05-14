"""Integrates SnapshotWriter with the Pipeline for periodic metric dumps."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from logdrift.snapshot import SnapshotData, SnapshotWriter
from logdrift.rate_monitor import RateWindow
from logdrift.anomaly_detector import AnomalyDetector


class SnapshotIntegration:
    """Collects pipeline metrics and periodically emits snapshots."""

    def __init__(
        self,
        rate_window: RateWindow,
        detector: AnomalyDetector,
        writer: SnapshotWriter,
        clock=None,
    ):
        self._rate_window = rate_window
        self._detector = detector
        self._writer = writer
        self._clock = clock or time.time
        self._event_count: int = 0
        self._anomaly_count: int = 0
        self._last_score: Optional[float] = None

    def process(self, line: str, anomaly_score: Optional[float] = None) -> None:
        """Called for each processed log line with its optional anomaly score."""
        self._event_count += 1
        if anomaly_score is not None and anomaly_score > 1.0:
            self._anomaly_count += 1
            self._last_score = anomaly_score

        snapshot = SnapshotData(
            timestamp=self._clock(),
            current_rate=self._rate_window.current_rate(),
            baseline_rate=self._detector.baseline_rate(),
            event_count=self._event_count,
            anomaly_count=self._anomaly_count,
            last_anomaly_score=self._last_score,
        )
        self._writer.record(snapshot)

    def latest_snapshot(self) -> Optional[SnapshotData]:
        return self._writer.latest()

    @classmethod
    def from_config(
        cls,
        rate_window: RateWindow,
        detector: AnomalyDetector,
        output_path: Optional[str] = None,
        interval_seconds: float = 10.0,
        clock=None,
    ) -> "SnapshotIntegration":
        path = Path(output_path) if output_path else None
        writer = SnapshotWriter(
            path=path,
            interval_seconds=interval_seconds,
            clock=clock,
        )
        return cls(
            rate_window=rate_window,
            detector=detector,
            writer=writer,
            clock=clock,
        )
