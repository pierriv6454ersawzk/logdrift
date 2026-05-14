"""Tests for logdrift.snapshot_integration module."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from logdrift.snapshot import SnapshotWriter
from logdrift.snapshot_integration import SnapshotIntegration


class FakeClock:
    def __init__(self, start: float = 1000.0):
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_integration(interval: float = 5.0):
    clock = FakeClock()
    rate_window = MagicMock()
    rate_window.current_rate.return_value = 3.5
    detector = MagicMock()
    detector.baseline_rate.return_value = 3.0
    writer = SnapshotWriter(interval_seconds=interval, clock=clock)
    integration = SnapshotIntegration(
        rate_window=rate_window,
        detector=detector,
        writer=writer,
        clock=clock,
    )
    return integration, clock


class TestSnapshotIntegration:
    def test_latest_snapshot_none_before_interval(self):
        integration, _ = _make_integration()
        integration.process("some log line")
        assert integration.latest_snapshot() is None

    def test_snapshot_written_after_interval(self):
        integration, clock = _make_integration(interval=5.0)
        clock.advance(6.0)
        integration.process("some log line")
        snap = integration.latest_snapshot()
        assert snap is not None
        assert snap.current_rate == 3.5
        assert snap.baseline_rate == 3.0
        assert snap.event_count == 1

    def test_event_count_increments(self):
        integration, clock = _make_integration(interval=5.0)
        clock.advance(6.0)
        integration.process("line 1")
        clock.advance(6.0)
        integration.process("line 2")
        snap = integration.latest_snapshot()
        assert snap.event_count == 2

    def test_anomaly_count_increments_on_high_score(self):
        integration, clock = _make_integration(interval=5.0)
        clock.advance(6.0)
        integration.process("line", anomaly_score=2.5)
        snap = integration.latest_snapshot()
        assert snap.anomaly_count == 1
        assert snap.last_anomaly_score == 2.5

    def test_anomaly_count_not_incremented_on_low_score(self):
        integration, clock = _make_integration(interval=5.0)
        clock.advance(6.0)
        integration.process("line", anomaly_score=0.5)
        snap = integration.latest_snapshot()
        assert snap.anomaly_count == 0
        assert snap.last_anomaly_score is None

    def test_no_anomaly_score_does_not_raise(self):
        integration, clock = _make_integration(interval=5.0)
        clock.advance(6.0)
        integration.process("line")  # no anomaly_score argument
        snap = integration.latest_snapshot()
        assert snap.last_anomaly_score is None

    def test_from_config_creates_integration(self):
        from logdrift.rate_monitor import RateWindow
        from logdrift.anomaly_detector import AnomalyDetector

        clock = FakeClock()
        rw = RateWindow(window_seconds=60)
        det = AnomalyDetector()
        integration = SnapshotIntegration.from_config(
            rate_window=rw,
            detector=det,
            output_path=None,
            interval_seconds=10.0,
            clock=clock,
        )
        assert integration is not None
        clock.advance(11.0)
        integration.process("hello")
        snap = integration.latest_snapshot()
        assert snap is not None
        assert snap.event_count == 1
