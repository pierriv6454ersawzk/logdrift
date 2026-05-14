"""Tests for logdrift.pipeline."""

from unittest.mock import MagicMock, patch

import pytest

from logdrift.pipeline import Pipeline, PipelineEvent
from logdrift.log_source import StdinLogSource


class _FakeSource:
    """Emits a fixed list of lines then stops."""

    def __init__(self, lines):
        self._lines = lines
        self.closed = False

    def lines(self):
        yield from self._lines

    def close(self):
        self.closed = True


class TestPipeline:
    def _make_pipeline(self, log_lines, **kwargs):
        source = _FakeSource(log_lines)
        events = []
        pipeline = Pipeline(source, on_event=events.append, **kwargs)
        return pipeline, events

    def test_emits_event_per_line(self):
        pipeline, events = self._make_pipeline(["a", "b", "c"])
        pipeline.run()
        assert len(events) == 3

    def test_event_contains_line(self):
        pipeline, events = self._make_pipeline(["hello world"])
        pipeline.run()
        assert events[0].line == "hello world"

    def test_event_rate_is_non_negative(self):
        pipeline, events = self._make_pipeline(["x"] * 5)
        pipeline.run()
        for event in events:
            assert event.rate >= 0.0

    def test_no_anomaly_without_enough_baseline(self):
        pipeline, events = self._make_pipeline(
            ["line"] * 5,
            baseline_min_samples=30,
        )
        pipeline.run()
        for event in events:
            assert event.anomaly is None or not event.anomaly.is_anomaly

    def test_anomaly_detected_on_spike(self):
        """Force a spike by patching the detector's check method."""
        from logdrift.anomaly_detector import AnomalyResult

        fake_anomaly = AnomalyResult(is_anomaly=True, rate=999.0, baseline=1.0, z_score=10.0)
        pipeline, events = self._make_pipeline(["spike!"])

        with patch.object(
            pipeline._detector, "check", return_value=fake_anomaly
        ):
            pipeline.run()

        assert events[0].anomaly is fake_anomaly
        assert events[0].anomaly.is_anomaly

    def test_stop_halts_pipeline(self):
        """Stopping mid-run should not process further lines."""
        collected = []

        def on_event(event):
            collected.append(event)

        source = _FakeSource(["a", "b", "c", "d", "e"])
        pipeline = Pipeline(source, on_event=on_event)

        original_process = pipeline._process

        def stop_after_first(line):
            original_process(line)
            pipeline.stop()

        pipeline._process = stop_after_first
        pipeline.run()

        assert len(collected) == 1

    def test_empty_source_emits_no_events(self):
        pipeline, events = self._make_pipeline([])
        pipeline.run()
        assert events == []
