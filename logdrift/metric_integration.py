"""Wires MetricExporter into the pipeline via a simple integration layer."""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

from logdrift.anomaly_detector import AnomalyResult
from logdrift.metric_exporter import MetricExporter, MetricSnapshot


class MetricIntegration:
    """Receives pipeline events and forwards relevant data to MetricExporter."""

    def __init__(self, exporter: MetricExporter) -> None:
        self._exporter = exporter
        self._callbacks: list[Callable[[MetricSnapshot], None]] = []

    def add_callback(self, cb: Callable[[MetricSnapshot], None]) -> None:
        """Register a callback invoked after each export."""
        self._callbacks.append(cb)

    def process(self, line: str, result: Optional[AnomalyResult], rate: float) -> None:
        """Record a single processed line and its anomaly result."""
        self._exporter.record_line()
        self._exporter.update_rate(rate)
        if result is not None and result.is_anomaly:
            self._exporter.record_anomaly(is_spike=result.score > 2.0)

    def flush(self) -> MetricSnapshot:
        """Export current metrics and notify callbacks."""
        snap = self._exporter.export()
        for cb in self._callbacks:
            cb(snap)
        return snap

    @classmethod
    def from_config(
        cls,
        output_path: Optional[str] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> "MetricIntegration":
        import time

        kwargs: dict = {}
        if clock is not None:
            kwargs["clock"] = clock
        if output_path is not None:
            kwargs["output_path"] = Path(output_path)
        exporter = MetricExporter(**kwargs)
        return cls(exporter)
