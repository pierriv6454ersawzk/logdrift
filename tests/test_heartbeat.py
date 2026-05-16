"""Tests for HeartbeatMonitor."""

from __future__ import annotations

import pytest
from logdrift.heartbeat import HeartbeatConfig, HeartbeatMonitor


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_monitor(threshold: float = 5.0) -> tuple[HeartbeatMonitor, FakeClock]:
    clock = FakeClock()
    config = HeartbeatConfig(silence_threshold_seconds=threshold)
    return HeartbeatMonitor(config, clock=clock), clock


class TestHeartbeatConfig:
    def test_zero_threshold_raises(self):
        with pytest.raises(ValueError, match="silence_threshold_seconds"):
            HeartbeatConfig(silence_threshold_seconds=0)

    def test_negative_interval_raises(self):
        with pytest.raises(ValueError, match="check_interval_seconds"):
            HeartbeatConfig(check_interval_seconds=-1)

    def test_valid_config_does_not_raise(self):
        cfg = HeartbeatConfig(silence_threshold_seconds=3.0, check_interval_seconds=0.5)
        assert cfg.silence_threshold_seconds == 3.0


class TestHeartbeatMonitor:
    def test_not_silent_initially(self):
        monitor, _ = _make_monitor()
        assert not monitor.is_silent

    def test_check_returns_false_before_threshold(self):
        monitor, clock = _make_monitor(threshold=5.0)
        clock.advance(4.9)
        assert monitor.check() is False

    def test_check_returns_true_at_threshold(self):
        monitor, clock = _make_monitor(threshold=5.0)
        clock.advance(5.0)
        assert monitor.check() is True

    def test_is_silent_after_threshold(self):
        monitor, clock = _make_monitor(threshold=5.0)
        clock.advance(6.0)
        monitor.check()
        assert monitor.is_silent

    def test_silence_callback_fires_once(self):
        monitor, clock = _make_monitor(threshold=5.0)
        fired: list[float] = []
        monitor.add_on_silence(fired.append)
        clock.advance(6.0)
        monitor.check()
        monitor.check()
        assert len(fired) == 1

    def test_silence_callback_receives_elapsed(self):
        monitor, clock = _make_monitor(threshold=5.0)
        fired: list[float] = []
        monitor.add_on_silence(fired.append)
        clock.advance(7.0)
        monitor.check()
        assert fired[0] == pytest.approx(7.0)

    def test_record_line_resets_silence(self):
        monitor, clock = _make_monitor(threshold=5.0)
        clock.advance(6.0)
        monitor.check()
        assert monitor.is_silent
        clock.advance(1.0)
        monitor.record_line()
        assert not monitor.is_silent

    def test_resume_callback_fires_after_record_line(self):
        monitor, clock = _make_monitor(threshold=5.0)
        resumed: list[float] = []
        monitor.add_on_resume(resumed.append)
        clock.advance(6.0)
        monitor.check()
        clock.advance(1.0)
        monitor.record_line()
        assert len(resumed) == 1

    def test_seconds_since_last_line(self):
        monitor, clock = _make_monitor()
        clock.advance(3.0)
        assert monitor.seconds_since_last_line == pytest.approx(3.0)
