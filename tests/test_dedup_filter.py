"""Tests for logdrift.dedup_filter."""

from __future__ import annotations

import pytest

from logdrift.dedup_filter import DedupConfig, DedupFilter


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


def _make_filter(window: float = 5.0, max_tracked: int = 512) -> tuple[DedupFilter, FakeClock]:
    clock = FakeClock()
    cfg = DedupConfig(window_seconds=window, max_tracked=max_tracked)
    return DedupFilter(config=cfg, clock=clock), clock


# ---------------------------------------------------------------------------
# DedupConfig validation
# ---------------------------------------------------------------------------

class TestDedupConfig:
    def test_invalid_window_raises(self):
        with pytest.raises(ValueError, match="window_seconds"):
            DedupConfig(window_seconds=0)

    def test_negative_window_raises(self):
        with pytest.raises(ValueError):
            DedupConfig(window_seconds=-1.0)

    def test_invalid_max_tracked_raises(self):
        with pytest.raises(ValueError, match="max_tracked"):
            DedupConfig(max_tracked=0)


# ---------------------------------------------------------------------------
# DedupFilter behaviour
# ---------------------------------------------------------------------------

class TestDedupFilter:
    def test_first_occurrence_passes(self):
        f, _ = _make_filter()
        assert f.should_pass("hello world") is True

    def test_immediate_duplicate_is_suppressed(self):
        f, _ = _make_filter()
        f.should_pass("hello world")
        assert f.should_pass("hello world") is False

    def test_different_lines_both_pass(self):
        f, _ = _make_filter()
        assert f.should_pass("line one") is True
        assert f.should_pass("line two") is True

    def test_line_passes_again_after_window_expires(self):
        f, clock = _make_filter(window=3.0)
        f.should_pass("repeated line")
        clock.advance(3.1)
        assert f.should_pass("repeated line") is True

    def test_line_still_suppressed_within_window(self):
        f, clock = _make_filter(window=3.0)
        f.should_pass("repeated line")
        clock.advance(2.9)
        assert f.should_pass("repeated line") is False

    def test_tracked_count_increments(self):
        f, _ = _make_filter()
        f.should_pass("a")
        f.should_pass("b")
        assert f.tracked_count == 2

    def test_tracked_count_decrements_after_eviction(self):
        f, clock = _make_filter(window=2.0)
        f.should_pass("a")
        clock.advance(2.1)
        f.should_pass("b")  # triggers eviction of "a"
        assert f.tracked_count == 1

    def test_max_tracked_evicts_oldest(self):
        f, _ = _make_filter(max_tracked=3)
        f.should_pass("x")
        f.should_pass("y")
        f.should_pass("z")
        # "x" should be evicted; "w" takes its slot
        assert f.should_pass("w") is True
        assert f.tracked_count == 3

    def test_reset_clears_all(self):
        f, _ = _make_filter()
        f.should_pass("a")
        f.should_pass("b")
        f.reset()
        assert f.tracked_count == 0
        assert f.should_pass("a") is True

    def test_default_config_used_when_none_provided(self):
        clock = FakeClock()
        f = DedupFilter(clock=clock)
        assert f.should_pass("line") is True
        assert f.should_pass("line") is False
