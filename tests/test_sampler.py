"""Tests for logdrift.sampler."""

from __future__ import annotations

import pytest

from logdrift.sampler import LogSampler, SamplerConfig


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeClock:
    """Monotonic clock whose value can be advanced manually."""

    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _make_sampler(max_rate: float = 10.0, sample_fraction: float = 0.5, window: float = 5.0):
    clock = FakeClock(start=100.0)
    config = SamplerConfig(max_rate=max_rate, sample_fraction=sample_fraction, window_seconds=window)
    sampler = LogSampler(config, clock=clock)
    return sampler, clock


# ---------------------------------------------------------------------------
# SamplerConfig validation
# ---------------------------------------------------------------------------

class TestSamplerConfig:
    def test_invalid_sample_fraction_zero(self):
        with pytest.raises(ValueError, match="sample_fraction"):
            SamplerConfig(max_rate=10.0, sample_fraction=0.0)

    def test_invalid_sample_fraction_above_one(self):
        with pytest.raises(ValueError, match="sample_fraction"):
            SamplerConfig(max_rate=10.0, sample_fraction=1.5)

    def test_invalid_max_rate(self):
        with pytest.raises(ValueError, match="max_rate"):
            SamplerConfig(max_rate=0.0)

    def test_invalid_window(self):
        with pytest.raises(ValueError, match="window_seconds"):
            SamplerConfig(max_rate=5.0, window_seconds=-1.0)


# ---------------------------------------------------------------------------
# LogSampler behaviour
# ---------------------------------------------------------------------------

class TestLogSampler:
    def test_passes_all_lines_below_max_rate(self):
        sampler, clock = _make_sampler(max_rate=100.0, window=5.0)
        # Send 10 lines in 5 s => rate = 2 lines/s, well below 100
        results = []
        for _ in range(10):
            clock.advance(0.5)
            results.append(sampler.should_pass("line"))
        assert all(results)

    def test_total_seen_increments(self):
        sampler, _ = _make_sampler()
        for _ in range(5):
            sampler.should_pass("x")
        assert sampler.total_seen == 5

    def test_total_passed_lte_total_seen(self):
        sampler, _ = _make_sampler(max_rate=1.0, sample_fraction=0.5, window=5.0)
        for _ in range(20):
            sampler.should_pass("x")
        assert sampler.total_passed <= sampler.total_seen

    def test_sampling_reduces_throughput_when_over_rate(self):
        # 50 lines in 5 s => rate = 10 lines/s; max_rate=5, fraction=0.5
        sampler, _ = _make_sampler(max_rate=5.0, sample_fraction=0.5, window=5.0)
        passed = sum(1 for _ in range(50) if sampler.should_pass("line"))
        # Should pass roughly 50% once rate exceeds max
        assert passed < 50

    def test_is_sampling_false_initially(self):
        sampler, _ = _make_sampler(max_rate=100.0)
        assert not sampler.is_sampling()

    def test_is_sampling_true_when_over_rate(self):
        sampler, _ = _make_sampler(max_rate=2.0, window=5.0)
        # Flood 50 events without advancing clock so rate is very high
        for _ in range(50):
            sampler.should_pass("x")
        assert sampler.is_sampling()

    def test_old_events_do_not_inflate_rate(self):
        sampler, clock = _make_sampler(max_rate=5.0, window=5.0)
        # Record 20 lines, then advance past the window
        for _ in range(20):
            sampler.should_pass("x")
        clock.advance(10.0)  # move past window
        # One new line; rate should be low again
        sampler.should_pass("x")
        assert not sampler.is_sampling()
