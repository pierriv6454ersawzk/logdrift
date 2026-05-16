"""Tests for HeartbeatIntegration."""

from __future__ import annotations

from logdrift.heartbeat import HeartbeatConfig
from logdrift.heartbeat_integration import HeartbeatIntegration


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


def _make_integration(threshold: float = 5.0) -> tuple[HeartbeatIntegration, FakeClock]:
    clock = FakeClock()
    cfg = HeartbeatConfig(silence_threshold_seconds=threshold)
    return HeartbeatIntegration(cfg, clock=clock), clock


class TestHeartbeatIntegration:
    def test_process_returns_line_unchanged(self):
        integ, _ = _make_integration()
        assert integ.process("hello") == "hello"

    def test_lines_seen_increments(self):
        integ, _ = _make_integration()
        integ.process("a")
        integ.process("b")
        assert integ.lines_seen == 2

    def test_tick_false_before_threshold(self):
        integ, clock = _make_integration(threshold=5.0)
        clock.advance(3.0)
        assert integ.tick() is False

    def test_tick_true_after_threshold(self):
        integ, clock = _make_integration(threshold=5.0)
        clock.advance(6.0)
        assert integ.tick() is True

    def test_is_silent_after_tick(self):
        integ, clock = _make_integration(threshold=5.0)
        clock.advance(6.0)
        integ.tick()
        assert integ.is_silent

    def test_not_silent_after_line(self):
        integ, clock = _make_integration(threshold=5.0)
        clock.advance(6.0)
        integ.tick()
        clock.advance(0.1)
        integ.process("recovered")
        assert not integ.is_silent

    def test_silence_callback_via_integration(self):
        integ, clock = _make_integration(threshold=5.0)
        fired: list[float] = []
        integ.add_on_silence(fired.append)
        clock.advance(6.0)
        integ.tick()
        assert len(fired) == 1

    def test_resume_callback_via_integration(self):
        integ, clock = _make_integration(threshold=5.0)
        resumed: list[float] = []
        integ.add_on_resume(resumed.append)
        clock.advance(6.0)
        integ.tick()
        clock.advance(0.1)
        integ.process("back")
        assert len(resumed) == 1

    def test_seconds_since_last_line(self):
        integ, clock = _make_integration()
        clock.advance(4.0)
        assert integ.seconds_since_last_line == pytest.approx(4.0)

    def test_from_config_factory(self):
        clock = FakeClock()
        integ = HeartbeatIntegration.from_config(
            threshold=3.0, check_interval=0.5, clock=clock
        )
        assert integ.lines_seen == 0
        clock.advance(4.0)
        assert integ.tick() is True


import pytest  # noqa: E402 – placed after test class to keep class readable
