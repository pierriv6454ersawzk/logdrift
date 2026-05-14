"""Tests for logdrift.snapshot module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from logdrift.snapshot import SnapshotData, SnapshotWriter


class FakeClock:
    def __init__(self, start: float = 0.0):
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_snapshot(**kwargs) -> SnapshotData:
    defaults = dict(
        timestamp=1000.0,
        current_rate=5.0,
        baseline_rate=4.0,
        event_count=50,
        anomaly_count=1,
    )
    defaults.update(kwargs)
    return SnapshotData(**defaults)


class TestSnapshotData:
    def test_to_dict_contains_all_fields(self):
        s = _make_snapshot(last_anomaly_score=2.3)
        d = s.to_dict()
        assert d["current_rate"] == 5.0
        assert d["last_anomaly_score"] == 2.3
        assert d["anomaly_count"] == 1

    def test_to_json_is_valid_json(self):
        s = _make_snapshot()
        parsed = json.loads(s.to_json())
        assert parsed["event_count"] == 50

    def test_extra_field_defaults_empty(self):
        s = _make_snapshot()
        assert s.extra == {}


class TestSnapshotWriter:
    def test_no_write_before_interval(self):
        clock = FakeClock(0.0)
        writer = SnapshotWriter(interval_seconds=10.0, clock=clock)
        snap = _make_snapshot()
        written = writer.record(snap)
        assert not written
        assert writer.latest() is None

    def test_writes_after_interval(self):
        clock = FakeClock(0.0)
        writer = SnapshotWriter(interval_seconds=10.0, clock=clock)
        clock.advance(11.0)
        snap = _make_snapshot()
        written = writer.record(snap)
        assert written
        assert writer.latest() is snap

    def test_does_not_write_twice_within_interval(self):
        clock = FakeClock(0.0)
        writer = SnapshotWriter(interval_seconds=10.0, clock=clock)
        clock.advance(11.0)
        writer.record(_make_snapshot())
        clock.advance(3.0)
        written = writer.record(_make_snapshot(event_count=99))
        assert not written
        assert len(writer.all_snapshots()) == 1

    def test_writes_to_file(self):
        clock = FakeClock(0.0)
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)
        writer = SnapshotWriter(path=path, interval_seconds=5.0, clock=clock)
        clock.advance(6.0)
        writer.record(_make_snapshot(event_count=7))
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["event_count"] == 7
        path.unlink(missing_ok=True)

    def test_multiple_writes_appended_to_file(self):
        clock = FakeClock(0.0)
        with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False) as f:
            path = Path(f.name)
        writer = SnapshotWriter(path=path, interval_seconds=5.0, clock=clock)
        for i in range(3):
            clock.advance(6.0)
            writer.record(_make_snapshot(event_count=i))
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 3
        path.unlink(missing_ok=True)

    def test_reset_clears_snapshots(self):
        clock = FakeClock(0.0)
        writer = SnapshotWriter(interval_seconds=5.0, clock=clock)
        clock.advance(6.0)
        writer.record(_make_snapshot())
        writer.reset()
        assert writer.latest() is None
        assert writer.all_snapshots() == []
