"""Tests for logdrift.formatter."""

import pytest

from logdrift.anomaly_detector import AnomalyResult
from logdrift.formatter import Color, FormatOptions, LogFormatter


class TestLogFormatter:
    def _no_color_formatter(self) -> LogFormatter:
        return LogFormatter(FormatOptions(color=False, show_rate=True))

    def test_ok_label_when_no_anomaly(self):
        fmt = self._no_color_formatter()
        result = fmt.format_line("hello world", anomaly=None, current_rate=1.0)
        assert "[OK]" in result
        assert "hello world" in result

    def test_anomaly_label_when_is_anomaly(self):
        fmt = self._no_color_formatter()
        anomaly = AnomalyResult(is_anomaly=True, score=2.5, reason="rate spike")
        result = fmt.format_line("boom", anomaly=anomaly, current_rate=50.0)
        assert "[ANOMALY]" in result
        assert "boom" in result

    def test_spike_label_when_score_above_threshold(self):
        fmt = self._no_color_formatter()
        anomaly = AnomalyResult(is_anomaly=False, score=0.8, reason="mild spike")
        result = fmt.format_line("warn", anomaly=anomaly, current_rate=10.0)
        assert "[SPIKE]" in result

    def test_rate_shown_in_output(self):
        fmt = self._no_color_formatter()
        result = fmt.format_line("msg", anomaly=None, current_rate=42.0)
        assert "42.0/s" in result

    def test_rate_hidden_when_disabled(self):
        fmt = LogFormatter(FormatOptions(color=False, show_rate=False))
        result = fmt.format_line("msg", anomaly=None, current_rate=42.0)
        assert "/s" not in result

    def test_anomaly_score_hidden_by_default(self):
        fmt = self._no_color_formatter()
        anomaly = AnomalyResult(is_anomaly=True, score=3.1, reason="x")
        result = fmt.format_line("msg", anomaly=anomaly, current_rate=5.0)
        assert "score=" not in result

    def test_anomaly_score_shown_when_enabled(self):
        fmt = LogFormatter(FormatOptions(color=False, show_rate=False, show_anomaly_score=True))
        anomaly = AnomalyResult(is_anomaly=True, score=3.14, reason="x")
        result = fmt.format_line("msg", anomaly=anomaly, current_rate=0.0)
        assert "score=3.14" in result

    def test_color_codes_present_when_enabled(self):
        fmt = LogFormatter(FormatOptions(color=True))
        result = fmt.format_line("msg", anomaly=None, current_rate=1.0)
        assert Color.RESET.value in result

    def test_no_color_codes_when_disabled(self):
        fmt = self._no_color_formatter()
        result = fmt.format_line("msg", anomaly=None, current_rate=1.0)
        assert "\033[" not in result

    def test_format_summary_contains_key_fields(self):
        fmt = self._no_color_formatter()
        summary = fmt.format_summary(total_lines=200, anomaly_count=3, elapsed=10.0)
        assert "200" in summary
        assert "3" in summary
        assert "20.0/s" in summary
        assert "10.0s" in summary

    def test_format_summary_zero_elapsed_no_division_error(self):
        fmt = self._no_color_formatter()
        summary = fmt.format_summary(total_lines=0, anomaly_count=0, elapsed=0.0)
        assert "0.0/s" in summary
