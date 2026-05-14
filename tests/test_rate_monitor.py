"""Tests for logdrift.rate_monitor."""

import time
import pytest
from logdrift.rate_monitor import RateWindow, RateMonitor


class TestRateWindow:
    def test_empty_rate_is_zero(self):
        w = RateWindow()
        assert w.current_rate == 0.0
        assert w.count == 0

    def test_records_increment_count(self):
        w = RateWindow(window_seconds=10.0)
        now = time.monotonic()
        for i in range(5):
            w.record(now + i * 0.1)
        assert w.count == 5

    def test_old_events_are_evicted(self):
        w = RateWindow(window_seconds=5.0)
        old_time = time.monotonic() - 10.0
        w.record(old_time)
        w.record(old_time + 1)
        # Trigger eviction by recording a current event
        w.record(time.monotonic())
        assert w.count == 1

    def test_rate_is_positive_with_events(self):
        w = RateWindow(window_seconds=60.0)
        now = time.monotonic()
        for i in range(10):
            w.record(now - (9 - i) * 0.5)
        assert w.current_rate > 0.0


class TestRateMonitor:
    def _warm_up(self, monitor: RateMonitor, n: int = 12) -> None:
        """Feed enough events to pass the warm-up phase."""
        now = time.monotonic()
        for i in range(n):
            monitor.ingest(now - (n - i) * 0.5)

    def test_no_spike_during_warmup(self):
        m = RateMonitor()
        now = time.monotonic()
        spikes = [m.ingest(now + i * 0.1) for i in range(9)]
        assert not any(spikes)

    def test_baseline_established_after_warmup(self):
        m = RateMonitor()
        self._warm_up(m)
        assert m.baseline_rate > 0.0

    def test_spike_detected(self):
        m = RateMonitor(window_seconds=10.0, spike_multiplier=2.0)
        # Warm up with slow rate (1 event / 2 seconds)
        now = time.monotonic()
        for i in range(15):
            m.ingest(now - (15 - i) * 2.0)

        # Inject a burst: many events in rapid succession
        burst_start = time.monotonic()
        spikes = [m.ingest(burst_start + i * 0.01) for i in range(50)]
        assert any(spikes), "Expected at least one spike to be detected"

    def test_no_false_spike_on_steady_rate(self):
        m = RateMonitor(window_seconds=30.0, spike_multiplier=3.0)
        now = time.monotonic()
        spikes = []
        for i in range(60):
            spikes.append(m.ingest(now - (60 - i) * 0.5))
        # After warm-up, steady rate should not trigger spikes
        post_warmup_spikes = spikes[10:]
        assert not any(post_warmup_spikes)

    def test_current_rate_reflects_recent_activity(self):
        m = RateMonitor()
        now = time.monotonic()
        for i in range(20):
            m.ingest(now - (20 - i) * 0.1)
        assert m.current_rate > 0.0
