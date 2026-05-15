"""Tests for logdrift.line_rate_tracker."""

from __future__ import annotations

import pytest

from logdrift.line_rate_tracker import LineRateTracker, LineRateTrackerConfig


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_tracker(window: float = 10.0, max_keys: int = 256) -> tuple:
    clock = FakeClock(start=100.0)
    config = LineRateTrackerConfig(window_seconds=window, max_keys=max_keys)
    tracker = LineRateTracker(config=config, clock=clock)
    return tracker, clock


class TestLineRateTrackerConfig:
    def test_invalid_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            LineRateTrackerConfig(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            LineRateTrackerConfig(window_seconds=-1.0)

    def test_invalid_max_keys_raises(self):
        with pytest.raises(ValueError, match="max_keys"):
            LineRateTrackerConfig(max_keys=0)

    def test_valid_config_does_not_raise(self):
        cfg = LineRateTrackerConfig(window_seconds=30.0, max_keys=100)
        assert cfg.window_seconds == 30.0
        assert cfg.max_keys == 100


class TestLineRateTracker:
    def test_unknown_key_rate_is_zero(self):
        tracker, _ = _make_tracker()
        assert tracker.rate("missing") == 0.0

    def test_unknown_key_total_is_zero(self):
        tracker, _ = _make_tracker()
        assert tracker.total("missing") == 0

    def test_record_increments_total(self):
        tracker, _ = _make_tracker()
        tracker.record("error")
        tracker.record("error")
        assert tracker.total("error") == 2

    def test_rate_positive_after_record(self):
        tracker, _ = _make_tracker()
        tracker.record("warn")
        assert tracker.rate("warn") > 0.0

    def test_old_events_expire_from_rate(self):
        tracker, clock = _make_tracker(window=5.0)
        tracker.record("info")
        clock.advance(10.0)
        assert tracker.rate("info") == 0.0

    def test_total_does_not_decrease_after_expiry(self):
        tracker, clock = _make_tracker(window=5.0)
        tracker.record("info")
        tracker.record("info")
        clock.advance(20.0)
        assert tracker.total("info") == 2

    def test_multiple_keys_tracked_independently(self):
        tracker, _ = _make_tracker()
        tracker.record("a")
        tracker.record("a")
        tracker.record("b")
        assert tracker.total("a") == 2
        assert tracker.total("b") == 1

    def test_all_rates_returns_all_keys(self):
        tracker, _ = _make_tracker()
        tracker.record("x")
        tracker.record("y")
        rates = tracker.all_rates()
        assert "x" in rates
        assert "y" in rates

    def test_max_keys_limit_prevents_new_keys(self):
        tracker, _ = _make_tracker(max_keys=2)
        tracker.record("a")
        tracker.record("b")
        tracker.record("c")  # should be silently dropped
        assert "c" not in tracker.keys()
        assert len(tracker.keys()) == 2

    def test_from_config_returns_tracker(self):
        config = LineRateTrackerConfig(window_seconds=20.0)
        tracker = LineRateTracker.from_config(config)
        assert isinstance(tracker, LineRateTracker)
