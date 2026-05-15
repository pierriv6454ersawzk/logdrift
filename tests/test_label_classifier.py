"""Tests for logdrift.label_classifier."""

from __future__ import annotations

import pytest

from logdrift.label_classifier import (
    ClassificationResult,
    ClassifierConfig,
    LabelClassifier,
    Severity,
)


def _make_classifier(**kwargs) -> LabelClassifier:
    return LabelClassifier(ClassifierConfig(**kwargs))


class TestClassifierConfig:
    def test_invalid_custom_key_raises(self):
        with pytest.raises(ValueError, match="Invalid severity key"):
            ClassifierConfig(custom_patterns={"BOGUS": [r"\bfoo\b"]})

    def test_valid_custom_key_does_not_raise(self):
        cfg = ClassifierConfig(custom_patterns={"ERROR": [r"\boops\b"]})
        assert "ERROR" in cfg.custom_patterns


class TestLabelClassifier:
    def test_unknown_when_no_match(self):
        clf = _make_classifier()
        result = clf.classify("everything is fine")
        assert result.severity == Severity.UNKNOWN
        assert result.matched_pattern is None

    def test_detects_error(self):
        clf = _make_classifier()
        result = clf.classify("connection failed")
        assert result.severity == Severity.ERROR

    def test_detects_critical(self):
        clf = _make_classifier()
        result = clf.classify("FATAL: out of memory")
        assert result.severity == Severity.CRITICAL

    def test_detects_warning(self):
        clf = _make_classifier()
        result = clf.classify("deprecated API called")
        assert result.severity == Severity.WARNING

    def test_detects_info(self):
        clf = _make_classifier()
        result = clf.classify("server started on port 8080")
        assert result.severity == Severity.INFO

    def test_detects_debug(self):
        clf = _make_classifier()
        result = clf.classify("trace: entering handler")
        assert result.severity == Severity.DEBUG

    def test_critical_beats_error(self):
        clf = _make_classifier()
        result = clf.classify("fatal error occurred")
        assert result.severity == Severity.CRITICAL

    def test_error_beats_warning(self):
        clf = _make_classifier()
        result = clf.classify("error: retry limit reached")
        assert result.severity == Severity.ERROR

    def test_case_insensitive_by_default(self):
        clf = _make_classifier()
        result = clf.classify("ERROR: something went wrong")
        assert result.severity == Severity.ERROR

    def test_case_sensitive_misses_uppercase(self):
        clf = _make_classifier(case_sensitive=True)
        # default patterns are lowercase; uppercase line should not match
        result = clf.classify("ERROR: something")
        assert result.severity == Severity.UNKNOWN

    def test_case_sensitive_matches_lowercase(self):
        clf = _make_classifier(case_sensitive=True)
        result = clf.classify("error: something")
        assert result.severity == Severity.ERROR

    def test_custom_pattern_applied(self):
        clf = _make_classifier(custom_patterns={"WARNING": [r"\boutage\b"]})
        result = clf.classify("partial outage detected")
        assert result.severity == Severity.WARNING

    def test_matched_pattern_returned(self):
        clf = _make_classifier()
        result = clf.classify("panic: nil pointer")
        assert result.matched_pattern is not None
        assert "panic" in result.matched_pattern

    def test_returns_classification_result_type(self):
        clf = _make_classifier()
        result = clf.classify("some log line")
        assert isinstance(result, ClassificationResult)
