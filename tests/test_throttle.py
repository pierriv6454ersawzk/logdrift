"""Tests for logdrift.throttle."""

from __future__ import annotations

import pytest

from logdrift.throttle import AlertThrottle, ThrottleConfig


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


def _make_throttle(
    cooldown: float = 10.0,
    max_per_window: int = 3,
    window: float = 60.0,
    start: float = 0.0,
) -> tuple[AlertThrottle, FakeClock]:
    clock = FakeClock(start)
    config = ThrottleConfig(
        cooldown_seconds=cooldown,
        max_per_window=max_per_window,
        window_seconds=window,
    )
    return AlertThrottle(config=config, clock=clock), clock


class TestThrottleConfig:
    def test_negative_cooldown_raises(self) -> None:
        with pytest.raises(ValueError):
            ThrottleConfig(cooldown_seconds=-1.0)

    def test_zero_max_per_window_raises(self) -> None:
        with pytest.raises(ValueError):
            ThrottleConfig(max_per_window=0)

    def test_zero_window_raises(self) -> None:
        with pytest.raises(ValueError):
            ThrottleConfig(window_seconds=0.0)


class TestAlertThrottle:
    def test_first_alert_not_suppressed(self) -> None:
        throttle, _ = _make_throttle()
        assert throttle.should_suppress("err") is False

    def test_suppressed_within_cooldown(self) -> None:
        throttle, clock = _make_throttle(cooldown=10.0)
        throttle.record_emit("err")
        clock.advance(5.0)
        assert throttle.should_suppress("err") is True

    def test_not_suppressed_after_cooldown(self) -> None:
        throttle, clock = _make_throttle(cooldown=10.0)
        throttle.record_emit("err")
        clock.advance(11.0)
        assert throttle.should_suppress("err") is False

    def test_suppressed_when_max_per_window_reached(self) -> None:
        throttle, clock = _make_throttle(cooldown=0.0, max_per_window=2, window=60.0)
        throttle.record_emit("err")
        clock.advance(1.0)
        throttle.record_emit("err")
        clock.advance(1.0)
        assert throttle.should_suppress("err") is True

    def test_old_emits_evicted_from_window(self) -> None:
        throttle, clock = _make_throttle(cooldown=0.0, max_per_window=2, window=30.0)
        throttle.record_emit("err")
        clock.advance(1.0)
        throttle.record_emit("err")
        # advance past the window so both emits are evicted
        clock.advance(31.0)
        assert throttle.should_suppress("err") is False

    def test_different_keys_are_independent(self) -> None:
        throttle, _ = _make_throttle(cooldown=10.0)
        throttle.record_emit("key_a")
        assert throttle.should_suppress("key_b") is False

    def test_reset_clears_state(self) -> None:
        throttle, clock = _make_throttle(cooldown=10.0)
        throttle.record_emit("err")
        clock.advance(1.0)
        throttle.reset("err")
        assert throttle.should_suppress("err") is False

    def test_reset_does_not_affect_other_keys(self) -> None:
        """Resetting one key must not clear throttle state for other keys."""
        throttle, clock = _make_throttle(cooldown=10.0)
        throttle.record_emit("key_a")
        throttle.record_emit("key_b")
        clock.advance(1.0)
        throttle.reset("key_a")
        assert throttle.should_suppress("key_b") is True
