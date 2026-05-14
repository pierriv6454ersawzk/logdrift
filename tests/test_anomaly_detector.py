"""Tests for logdrift.anomaly_detector."""

import pytest
from logdrift.anomaly_detector import AnomalyDetector, AnomalyResult


class TestAnomalyDetector:
    def _detector_with_baseline(self, rates: list[float], **kwargs) -> AnomalyDetector:
        """Helper: create a detector pre-loaded with baseline samples."""
        detector = AnomalyDetector(**kwargs)
        for r in rates:
            detector.record_baseline(r)
        return detector

    def test_no_anomaly_without_enough_baseline(self):
        detector = AnomalyDetector(min_baseline_samples=5)
        for _ in range(4):
            detector.record_baseline(10.0)
        result = detector.check(999.0)
        assert result is None

    def test_has_enough_baseline_false_initially(self):
        detector = AnomalyDetector(min_baseline_samples=3)
        assert not detector.has_enough_baseline()
        detector.record_baseline(1.0)
        detector.record_baseline(1.0)
        assert not detector.has_enough_baseline()
        detector.record_baseline(1.0)
        assert detector.has_enough_baseline()

    def test_baseline_rate_empty(self):
        detector = AnomalyDetector()
        assert detector.baseline_rate() == 0.0

    def test_baseline_rate_average(self):
        detector = self._detector_with_baseline([10.0, 20.0, 30.0])
        assert detector.baseline_rate() == 20.0

    def test_no_anomaly_for_normal_rate(self):
        baseline = [10.0] * 10
        detector = self._detector_with_baseline(baseline)
        result = detector.check(11.0)
        assert result is None

    def test_spike_detected(self):
        baseline = [10.0] * 10
        detector = self._detector_with_baseline(baseline, spike_multiplier=3.0)
        result = detector.check(50.0)
        assert result is not None
        assert result.is_anomaly is True
        assert "spike" in result.reason
        assert result.current_rate == 50.0
        assert result.baseline_rate == 10.0

    def test_spike_severity_high_for_extreme_spike(self):
        baseline = [10.0] * 10
        detector = self._detector_with_baseline(baseline, spike_multiplier=3.0)
        result = detector.check(200.0)  # 20x baseline, > 3.0 * 2 = 6x threshold
        assert result is not None
        assert result.severity == "high"

    def test_spike_severity_medium_for_moderate_spike(self):
        baseline = [10.0] * 10
        detector = self._detector_with_baseline(baseline, spike_multiplier=3.0)
        result = detector.check(35.0)  # 3.5x baseline, just over threshold
        assert result is not None
        assert result.severity == "medium"

    def test_drop_detected(self):
        baseline = [100.0] * 10
        detector = self._detector_with_baseline(baseline, drop_multiplier=0.2)
        result = detector.check(5.0)
        assert result is not None
        assert result.is_anomaly is True
        assert "drop" in result.reason

    def test_no_drop_at_boundary(self):
        baseline = [100.0] * 10
        detector = self._detector_with_baseline(baseline, drop_multiplier=0.2)
        result = detector.check(20.0)  # exactly at boundary, not below
        assert result is None

    def test_spike_from_zero_baseline(self):
        baseline = [0.0] * 10
        detector = self._detector_with_baseline(baseline)
        result = detector.check(5.0)
        assert result is not None
        assert result.is_anomaly is True
        assert result.severity == "high"

    def test_no_anomaly_at_zero_baseline_and_zero_rate(self):
        baseline = [0.0] * 10
        detector = self._detector_with_baseline(baseline)
        result = detector.check(0.0)
        assert result is None

    def test_reset_clears_baseline(self):
        detector = self._detector_with_baseline([10.0] * 10)
        detector.reset()
        assert not detector.has_enough_baseline()
        assert detector.baseline_rate() == 0.0

    def test_invalid_spike_multiplier_raises(self):
        with pytest.raises(ValueError):
            AnomalyDetector(spike_multiplier=0.5)

    def test_invalid_drop_multiplier_raises(self):
        with pytest.raises(ValueError):
            AnomalyDetector(drop_multiplier=1.5)

    def test_negative_rate_record_raises(self):
        detector = AnomalyDetector()
        with pytest.raises(ValueError):
            detector.record_baseline(-1.0)
