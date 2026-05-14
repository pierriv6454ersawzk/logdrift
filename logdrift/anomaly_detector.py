"""Anomaly detection for log rate spikes and drops."""

from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class AnomalyResult:
    """Result of an anomaly check."""
    is_anomaly: bool
    reason: str
    current_rate: float
    baseline_rate: float
    severity: str  # 'low', 'medium', 'high'


class AnomalyDetector:
    """Detects rate anomalies by comparing current rate to a rolling baseline.

    Uses a simple z-score-like threshold approach: flags when the current
    rate deviates from the baseline by more than a configurable multiplier.
    """

    def __init__(
        self,
        spike_multiplier: float = 3.0,
        drop_multiplier: float = 0.2,
        min_baseline_samples: int = 5,
    ):
        """
        Args:
            spike_multiplier: Flag as spike if current_rate > baseline * multiplier.
            drop_multiplier: Flag as drop if current_rate < baseline * multiplier.
            min_baseline_samples: Minimum number of samples before anomaly detection starts.
        """
        if spike_multiplier <= 1.0:
            raise ValueError("spike_multiplier must be greater than 1.0")
        if not (0.0 < drop_multiplier < 1.0):
            raise ValueError("drop_multiplier must be between 0.0 and 1.0")

        self.spike_multiplier = spike_multiplier
        self.drop_multiplier = drop_multiplier
        self.min_baseline_samples = min_baseline_samples

        self._baseline_samples: list[float] = []

    def record_baseline(self, rate: float) -> None:
        """Record a rate sample for baseline calculation."""
        if rate < 0:
            raise ValueError("Rate cannot be negative")
        self._baseline_samples.append(rate)

    def baseline_rate(self) -> float:
        """Return the mean of all recorded baseline samples."""
        if not self._baseline_samples:
            return 0.0
        return sum(self._baseline_samples) / len(self._baseline_samples)

    def has_enough_baseline(self) -> bool:
        """Return True if enough samples exist for reliable detection."""
        return len(self._baseline_samples) >= self.min_baseline_samples

    def check(self, current_rate: float) -> Optional[AnomalyResult]:
        """Check whether the current rate is anomalous.

        Returns an AnomalyResult if an anomaly is detected, else None.
        """
        if not self.has_enough_baseline():
            return None

        baseline = self.baseline_rate()

        if baseline == 0.0:
            if current_rate > 0:
                return AnomalyResult(
                    is_anomaly=True,
                    reason="spike: activity detected from zero baseline",
                    current_rate=current_rate,
                    baseline_rate=baseline,
                    severity="high",
                )
            return None

        if current_rate > baseline * self.spike_multiplier:
            ratio = current_rate / baseline
            severity = "high" if ratio > self.spike_multiplier * 2 else "medium"
            return AnomalyResult(
                is_anomaly=True,
                reason=f"spike: rate {current_rate:.2f} is {ratio:.1f}x baseline",
                current_rate=current_rate,
                baseline_rate=baseline,
                severity=severity,
            )

        if current_rate < baseline * self.drop_multiplier:
            ratio = current_rate / baseline
            return AnomalyResult(
                is_anomaly=True,
                reason=f"drop: rate {current_rate:.2f} is {ratio:.1%} of baseline",
                current_rate=current_rate,
                baseline_rate=baseline,
                severity="medium",
            )

        return None

    def reset(self) -> None:
        """Clear all baseline samples."""
        self._baseline_samples.clear()
