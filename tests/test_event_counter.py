"""Tests for logdrift.event_counter."""

from __future__ import annotations

import pytest

from logdrift.event_counter import CounterConfig, CounterSnapshot, EventCounter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_counter(window: float = 60.0, top_n: int = 5, start: float = 100.0):
    clock = FakeClock(start)
    cfg = CounterConfig(window_seconds=window, top_n=top_n)
    counter = EventCounter(config=cfg, clock=clock)
    return counter, clock


# ---------------------------------------------------------------------------
# CounterConfig validation
# ---------------------------------------------------------------------------

class TestCounterConfig:
    def test_invalid_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            CounterConfig(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError):
            CounterConfig(window_seconds=-5)

    def test_invalid_top_n_raises(self):
        with pytest.raises(ValueError, match="top_n"):
            CounterConfig(top_n=0)

    def test_valid_config_does_not_raise(self):
        cfg = CounterConfig(window_seconds=30.0, top_n=3)
        assert cfg.window_seconds == 30.0


# ---------------------------------------------------------------------------
# EventCounter behaviour
# ---------------------------------------------------------------------------

class TestEventCounter:
    def test_empty_count_is_zero(self):
        counter, _ = _make_counter()
        assert counter.count("error") == 0

    def test_record_increments_count(self):
        counter, _ = _make_counter()
        counter.record("error")
        counter.record("error")
        assert counter.count("error") == 2

    def test_different_labels_tracked_independently(self):
        counter, _ = _make_counter()
        counter.record("warn")
        counter.record("error")
        counter.record("error")
        assert counter.count("warn") == 1
        assert counter.count("error") == 2

    def test_old_events_evicted(self):
        counter, clock = _make_counter(window=10.0)
        counter.record("info")
        counter.record("info")
        clock.advance(11.0)  # past window
        assert counter.count("info") == 0

    def test_partial_eviction(self):
        counter, clock = _make_counter(window=10.0)
        counter.record("info")  # t=100
        clock.advance(6.0)
        counter.record("info")  # t=106
        clock.advance(6.0)       # now t=112, first event outside window
        assert counter.count("info") == 1

    def test_snapshot_returns_all_labels(self):
        counter, _ = _make_counter()
        counter.record("a")
        counter.record("b")
        counter.record("b")
        snap = counter.snapshot()
        assert snap.counts["a"] == 1
        assert snap.counts["b"] == 2

    def test_snapshot_top_sorted(self):
        counter, _ = _make_counter()
        for _ in range(3):
            counter.record("x")
        counter.record("y")
        snap = counter.snapshot()
        top = snap.top(2)
        assert top[0] == ("x", 3)
        assert top[1] == ("y", 1)

    def test_reset_clears_all(self):
        counter, _ = _make_counter()
        counter.record("z")
        counter.reset()
        assert counter.count("z") == 0

    def test_snapshot_to_dict_has_timestamp(self):
        counter, clock = _make_counter(start=500.0)
        counter.record("k")
        d = counter.snapshot().to_dict()
        assert d["timestamp"] == 500.0
        assert "counts" in d
