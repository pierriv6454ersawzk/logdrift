"""Tests for ClassifierIntegration."""

from __future__ import annotations

from typing import List

import pytest

from logdrift.label_classifier import ClassificationResult, ClassifierConfig, Severity
from logdrift.line_classifier_integration import ClassifierIntegration


def _make_integration(**kwargs) -> ClassifierIntegration:
    config = ClassifierConfig(**kwargs)
    return ClassifierIntegration(config)


class TestClassifierIntegration:
    def test_initial_total_processed_is_zero(self):
        integ = _make_integration()
        assert integ.total_processed == 0

    def test_process_increments_total(self):
        integ = _make_integration()
        integ.process("INFO starting up")
        assert integ.total_processed == 1

    def test_process_returns_classification_result(self):
        integ = _make_integration()
        result = integ.process("ERROR something failed")
        assert isinstance(result, ClassificationResult)

    def test_error_line_classified_as_error(self):
        integ = _make_integration()
        result = integ.process("ERROR disk full")
        assert result.severity == Severity.ERROR

    def test_info_line_classified_as_info(self):
        integ = _make_integration()
        result = integ.process("INFO all good")
        assert result.severity == Severity.INFO

    def test_severity_count_tracks_errors(self):
        integ = _make_integration()
        integ.process("ERROR one")
        integ.process("ERROR two")
        integ.process("INFO three")
        assert integ.severity_count(Severity.ERROR) == 2
        assert integ.severity_count(Severity.INFO) == 1

    def test_callback_is_invoked(self):
        integ = _make_integration()
        collected: List[ClassificationResult] = []
        integ.add_callback(collected.append)
        integ.process("WARNING low memory")
        assert len(collected) == 1
        assert collected[0].severity == Severity.WARNING

    def test_multiple_callbacks_all_invoked(self):
        integ = _make_integration()
        calls_a: List[ClassificationResult] = []
        calls_b: List[ClassificationResult] = []
        integ.add_callback(calls_a.append)
        integ.add_callback(calls_b.append)
        integ.process("DEBUG verbose")
        assert len(calls_a) == 1
        assert len(calls_b) == 1

    def test_process_batch_returns_all_results(self):
        integ = _make_integration()
        lines = ["INFO a", "ERROR b", "WARNING c"]
        results = integ.process_batch(lines)
        assert len(results) == 3
        assert integ.total_processed == 3

    def test_process_batch_empty_list(self):
        integ = _make_integration()
        results = integ.process_batch([])
        assert results == []
        assert integ.total_processed == 0

    def test_from_config_uses_defaults(self):
        integ = ClassifierIntegration.from_config()
        result = integ.process("CRITICAL system crash")
        assert result.severity == Severity.CRITICAL

    def test_from_config_accepts_custom_config(self):
        config = ClassifierConfig()
        integ = ClassifierIntegration.from_config(config)
        assert integ.total_processed == 0
