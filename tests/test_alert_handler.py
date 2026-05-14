"""Tests for logdrift.alert_handler."""

from __future__ import annotations

from typing import List, Tuple

import pytest

from logdrift.anomaly_detector import AnomalyResult
from logdrift.alert_handler import AlertConfig, AlertHandler


def _make_anomaly(score: float = 3.0, is_anomaly: bool = True) -> AnomalyResult:
    return AnomalyResult(
        is_anomaly=is_anomaly,
        score=score,
        current_rate=10.0,
        baseline_rate=3.0,
    )


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start

    def __call__(self) -> float:
        return self._t

    def advance(self, seconds: float) -> None:
        self._t += seconds


class TestAlertHandler:
    def _make_handler(
        self, min_score: float = 2.0, cooldown: float = 5.0
    ) -> Tuple[AlertHandler, FakeClock, List]:
        clock = FakeClock()
        fired: List[Tuple[str, AnomalyResult]] = []
        config = AlertConfig(min_score=min_score, cooldown_seconds=cooldown)
        handler = AlertHandler(config, callbacks=[lambda l, r: fired.append((l, r))], clock=clock)
        return handler, clock, fired

    def test_no_alert_when_not_anomaly(self):
        handler, _, fired = self._make_handler()
        result = _make_anomaly(is_anomaly=False)
        assert handler.evaluate("line", result) is False
        assert fired == []

    def test_no_alert_when_score_below_threshold(self):
        handler, _, fired = self._make_handler(min_score=5.0)
        result = _make_anomaly(score=3.0, is_anomaly=True)
        assert handler.evaluate("line", result) is False
        assert fired == []

    def test_alert_fires_when_threshold_exceeded(self):
        handler, _, fired = self._make_handler()
        result = _make_anomaly(score=3.0)
        assert handler.evaluate("log line", result) is True
        assert len(fired) == 1
        assert fired[0][0] == "log line"

    def test_cooldown_suppresses_repeated_alerts(self):
        handler, clock, fired = self._make_handler(cooldown=5.0)
        result = _make_anomaly(score=3.0)
        handler.evaluate("line", result)
        clock.advance(3.0)
        assert handler.evaluate("line", result) is False
        assert len(fired) == 1

    def test_alert_fires_again_after_cooldown(self):
        handler, clock, fired = self._make_handler(cooldown=5.0)
        result = _make_anomaly(score=3.0)
        handler.evaluate("line", result)
        clock.advance(6.0)
        assert handler.evaluate("line", result) is True
        assert len(fired) == 2

    def test_multiple_callbacks_all_invoked(self):
        clock = FakeClock()
        hits: List[int] = []
        config = AlertConfig(min_score=1.0, cooldown_seconds=0.0)
        handler = AlertHandler(
            config,
            callbacks=[lambda l, r: hits.append(1), lambda l, r: hits.append(2)],
            clock=clock,
        )
        handler.evaluate("x", _make_anomaly(score=2.0))
        assert hits == [1, 2]

    def test_add_callback_registers_new_callback(self):
        handler, _, fired = self._make_handler()
        extra: List[str] = []
        handler.add_callback(lambda l, r: extra.append(l))
        handler.evaluate("hello", _make_anomaly())
        assert "hello" in extra
