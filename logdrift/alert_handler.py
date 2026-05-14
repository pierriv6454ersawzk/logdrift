"""Alert handler for emitting notifications when anomalies are detected."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from logdrift.anomaly_detector import AnomalyResult


@dataclass
class AlertConfig:
    min_score: float = 2.0
    cooldown_seconds: float = 5.0
    label: str = "ALERT"


AlertCallback = Callable[[str, AnomalyResult], None]


class AlertHandler:
    """Fires alert callbacks when an anomaly result exceeds a score threshold.

    A cooldown period prevents the same alert from firing repeatedly within
    a short window.
    """

    def __init__(
        self,
        config: AlertConfig,
        callbacks: Optional[List[AlertCallback]] = None,
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        self._config = config
        self._callbacks: List[AlertCallback] = callbacks or []
        self._clock: Callable[[], float] = clock or __import__("time").monotonic
        self._last_fired: float = -float("inf")

    def add_callback(self, cb: AlertCallback) -> None:
        """Register an additional callback."""
        self._callbacks.append(cb)

    def evaluate(self, line: str, result: AnomalyResult) -> bool:
        """Check *result* and fire callbacks if threshold is exceeded.

        Returns True if an alert was fired, False otherwise.
        """
        if not result.is_anomaly:
            return False
        if result.score < self._config.min_score:
            return False

        now = self._clock()
        if now - self._last_fired < self._config.cooldown_seconds:
            return False

        self._last_fired = now
        for cb in self._callbacks:
            cb(line, result)
        return True

    @staticmethod
    def stderr_callback(line: str, result: AnomalyResult) -> None:  # pragma: no cover
        """Built-in callback that writes a summary to stderr."""
        print(
            f"[ALERT] score={result.score:.2f} rate={result.current_rate:.2f}/s | {line}",
            file=sys.stderr,
        )
