"""Tests for logdrift.metric_exporter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from logdrift.metric_exporter import MetricExporter, MetricSnapshot


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, delta: float) -> None:
        self._t += delta


def _make_exporter(clock: FakeClock | None = None) -> MetricExporter:
    return MetricExporter(clock=clock or FakeClock())


class TestMetricSnapshot:
    def test_to_dict_contains_all_keys(self):
        snap = MetricSnapshot(timestamp=1.0, lines_processed=5, anomaly_count=2, current_rate=3.5, spike_count=1)
        d = snap.to_dict()
        assert set(d.keys()) == {"timestamp", "lines_processed", "anomaly_count", "current_rate", "spike_count"}

    def test_to_json_is_valid_json(self):
        snap = MetricSnapshot(timestamp=1.0, lines_processed=5, anomaly_count=2, current_rate=3.5, spike_count=1)
        parsed = json.loads(snap.to_json())
        assert parsed["lines_processed"] == 5

    def test_rate_is_rounded(self):
        snap = MetricSnapshot(timestamp=1.0, lines_processed=1, anomaly_count=0, current_rate=1.23456789, spike_count=0)
        assert snap.to_dict()["current_rate"] == 1.2346


class TestMetricExporter:
    def test_initial_snapshot_is_zeroed(self):
        clock = FakeClock()
        exp = _make_exporter(clock)
        snap = exp.snapshot()
        assert snap.lines_processed == 0
        assert snap.anomaly_count == 0
        assert snap.spike_count == 0
        assert snap.current_rate == 0.0

    def test_record_line_increments(self):
        exp = _make_exporter()
        exp.record_line()
        exp.record_line()
        assert exp.snapshot().lines_processed == 2

    def test_record_anomaly_increments(self):
        exp = _make_exporter()
        exp.record_anomaly()
        assert exp.snapshot().anomaly_count == 1
        assert exp.snapshot().spike_count == 0

    def test_record_spike_increments_both(self):
        exp = _make_exporter()
        exp.record_anomaly(is_spike=True)
        snap = exp.snapshot()
        assert snap.anomaly_count == 1
        assert snap.spike_count == 1

    def test_update_rate_reflected_in_snapshot(self):
        exp = _make_exporter()
        exp.update_rate(42.5)
        assert exp.snapshot().current_rate == 42.5

    def test_snapshot_uses_clock(self):
        clock = FakeClock(start=500.0)
        exp = _make_exporter(clock)
        assert exp.snapshot().timestamp == 500.0
        clock.advance(10.0)
        assert exp.snapshot().timestamp == 510.0

    def test_reset_clears_counters(self):
        exp = _make_exporter()
        exp.record_line()
        exp.record_anomaly(is_spike=True)
        exp.update_rate(9.9)
        exp.reset()
        snap = exp.snapshot()
        assert snap.lines_processed == 0
        assert snap.anomaly_count == 0
        assert snap.spike_count == 0
        assert snap.current_rate == 0.0

    def test_export_writes_to_file(self, tmp_path: Path):
        out = tmp_path / "metrics.json"
        clock = FakeClock()
        exp = MetricExporter(clock=clock, output_path=out)
        exp.record_line()
        exp.record_anomaly()
        snap = exp.export()
        assert out.exists()
        data = json.loads(out.read_text())
        assert data["lines_processed"] == 1
        assert data["anomaly_count"] == 1

    def test_export_returns_snapshot(self):
        exp = _make_exporter()
        exp.record_line()
        snap = exp.export()
        assert isinstance(snap, MetricSnapshot)
        assert snap.lines_processed == 1
