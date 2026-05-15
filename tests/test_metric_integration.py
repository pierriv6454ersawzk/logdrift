"""Tests for logdrift.metric_integration."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pytest

from logdrift.anomaly_detector import AnomalyResult
from logdrift.metric_exporter import MetricExporter, MetricSnapshot
from logdrift.metric_integration import MetricIntegration


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, delta: float) -> None:
        self._t += delta


def _make_integration(clock: Optional[FakeClock] = None) -> MetricIntegration:
    c = clock or FakeClock()
    exporter = MetricExporter(clock=c)
    return MetricIntegration(exporter)


def _anomaly(score: float = 1.0, is_anomaly: bool = True) -> AnomalyResult:
    return AnomalyResult(is_anomaly=is_anomaly, score=score, baseline_rate=1.0, current_rate=score)


class TestMetricIntegration:
    def test_process_increments_line_count(self):
        integ = _make_integration()
        integ.process("hello", None, rate=1.0)
        integ.process("world", None, rate=1.0)
        snap = integ.flush()
        assert snap.lines_processed == 2

    def test_no_anomaly_result_does_not_count(self):
        integ = _make_integration()
        integ.process("ok", None, rate=0.5)
        snap = integ.flush()
        assert snap.anomaly_count == 0

    def test_anomaly_result_increments_anomaly_count(self):
        integ = _make_integration()
        integ.process("err", _anomaly(score=1.5), rate=2.0)
        snap = integ.flush()
        assert snap.anomaly_count == 1
        assert snap.spike_count == 0

    def test_high_score_anomaly_increments_spike(self):
        integ = _make_integration()
        integ.process("err", _anomaly(score=3.0), rate=5.0)
        snap = integ.flush()
        assert snap.spike_count == 1

    def test_non_anomaly_result_is_ignored(self):
        integ = _make_integration()
        integ.process("info", _anomaly(score=0.1, is_anomaly=False), rate=1.0)
        snap = integ.flush()
        assert snap.anomaly_count == 0

    def test_rate_is_updated(self):
        integ = _make_integration()
        integ.process("line", None, rate=7.25)
        snap = integ.flush()
        assert snap.current_rate == 7.25

    def test_flush_calls_callbacks(self):
        integ = _make_integration()
        received: list[MetricSnapshot] = []
        integ.add_callback(received.append)
        integ.process("x", None, rate=1.0)
        integ.flush()
        assert len(received) == 1
        assert received[0].lines_processed == 1

    def test_multiple_callbacks_all_called(self):
        integ = _make_integration()
        results_a: list[MetricSnapshot] = []
        results_b: list[MetricSnapshot] = []
        integ.add_callback(results_a.append)
        integ.add_callback(results_b.append)
        integ.flush()
        assert len(results_a) == 1
        assert len(results_b) == 1

    def test_from_config_creates_integration(self):
        clock = FakeClock()
        integ = MetricIntegration.from_config(clock=clock)
        assert isinstance(integ, MetricIntegration)

    def test_from_config_with_output_path(self, tmp_path: Path):
        out = str(tmp_path / "m.json")
        clock = FakeClock()
        integ = MetricIntegration.from_config(output_path=out, clock=clock)
        integ.process("line", None, rate=1.0)
        snap = integ.flush()
        assert Path(out).exists()
        assert snap.lines_processed == 1
