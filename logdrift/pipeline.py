"""Wire together a LogSource, RateWindow, and AnomalyDetector into a pipeline."""

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from logdrift.anomaly_detector import AnomalyDetector, AnomalyResult
from logdrift.log_source import LogSource
from logdrift.rate_monitor import RateWindow


@dataclass
class PipelineEvent:
    """Emitted for every log line processed by the pipeline."""

    line: str
    rate: float
    anomaly: Optional[AnomalyResult] = None


EventCallback = Callable[[PipelineEvent], None]


class Pipeline:
    """Read lines from *source*, track rate, detect anomalies, call *on_event*."""

    def __init__(
        self,
        source: LogSource,
        window_seconds: float = 60.0,
        baseline_min_samples: int = 30,
        spike_threshold: float = 3.0,
        on_event: Optional[EventCallback] = None,
    ) -> None:
        self.source = source
        self._rate_window = RateWindow(window_seconds=window_seconds)
        self._detector = AnomalyDetector(
            min_baseline_samples=baseline_min_samples,
            spike_threshold=spike_threshold,
        )
        self._on_event: EventCallback = on_event or (lambda e: None)
        self._running = False

    def run(self) -> None:
        """Start consuming lines from the source.  Blocks until stopped or EOF."""
        self._running = True
        try:
            for line in self.source.lines():
                if not self._running:
                    break
                self._process(line)
        finally:
            self._running = False

    def stop(self) -> None:
        """Signal the pipeline to stop after the current line."""
        self._running = False
        self.source.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process(self, line: str) -> None:
        self._rate_window.record()
        rate = self._rate_window.current_rate()
        self._detector.record_baseline(rate)
        anomaly = self._detector.check(rate)
        self._on_event(PipelineEvent(line=line, rate=rate, anomaly=anomaly))
