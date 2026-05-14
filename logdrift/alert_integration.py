"""Wires AlertHandler into the Pipeline via a post-process hook."""

from __future__ import annotations

from typing import Callable, Optional

from logdrift.alert_handler import AlertConfig, AlertHandler
from logdrift.anomaly_detector import AnomalyDetector, AnomalyResult
from logdrift.pipeline import PipelineEvent


class AlertIntegration:
    """Stateful helper that evaluates each PipelineEvent and triggers alerts.

    Intended to be used as a post-process callback in Pipeline.run():

        integration = AlertIntegration(detector, handler)
        for event in pipeline.run():
            integration.process(event)
    """

    def __init__(
        self,
        detector: AnomalyDetector,
        handler: AlertHandler,
        on_alert: Optional[Callable[[PipelineEvent, AnomalyResult], None]] = None,
    ) -> None:
        self._detector = detector
        self._handler = handler
        self._on_alert = on_alert

    def process(self, event: PipelineEvent) -> Optional[AnomalyResult]:
        """Record *event* in the detector and evaluate for alerts.

        Returns the AnomalyResult if an alert fired, otherwise None.
        """
        result = self._detector.evaluate(event.timestamp)
        fired = self._handler.evaluate(event.line, result)
        if fired and self._on_alert is not None:
            self._on_alert(event, result)
            return result
        return None

    @classmethod
    def from_config(
        cls,
        alert_config: AlertConfig,
        window_seconds: float = 60.0,
        baseline_periods: int = 10,
        on_alert: Optional[Callable[[PipelineEvent, AnomalyResult], None]] = None,
    ) -> "AlertIntegration":
        """Convenience factory that builds detector and handler from config."""
        detector = AnomalyDetector(
            window_seconds=window_seconds,
            min_baseline_periods=baseline_periods,
        )
        handler = AlertHandler(alert_config)
        return cls(detector, handler, on_alert=on_alert)
