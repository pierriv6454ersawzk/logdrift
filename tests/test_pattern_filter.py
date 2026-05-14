"""Tests for logdrift.pattern_filter."""
from __future__ import annotations

import pytest

from logdrift.pattern_filter import PatternFilter, PatternFilterConfig


class TestPatternFilter:
    def _make_filter(
        self,
        include=None,
        exclude=None,
        case_sensitive=False,
    ) -> PatternFilter:
        cfg = PatternFilterConfig(
            include_patterns=include or [],
            exclude_patterns=exclude or [],
            case_sensitive=case_sensitive,
        )
        return PatternFilter(cfg)

    # --- should_pass ---

    def test_no_rules_passes_everything(self):
        f = PatternFilter()
        assert f.should_pass("any line at all") is True

    def test_include_pattern_matches(self):
        f = self._make_filter(include=["ERROR"])
        assert f.should_pass("2024-01-01 ERROR something broke") is True

    def test_include_pattern_blocks_non_matching(self):
        f = self._make_filter(include=["ERROR"])
        assert f.should_pass("2024-01-01 INFO all good") is False

    def test_exclude_pattern_blocks_matching(self):
        f = self._make_filter(exclude=["DEBUG"])
        assert f.should_pass("DEBUG verbose output") is False

    def test_exclude_pattern_passes_non_matching(self):
        f = self._make_filter(exclude=["DEBUG"])
        assert f.should_pass("ERROR something bad") is True

    def test_include_and_exclude_both_applied(self):
        f = self._make_filter(include=["ERROR"], exclude=["timeout"])
        assert f.should_pass("ERROR connection timeout") is False
        assert f.should_pass("ERROR disk full") is True
        assert f.should_pass("INFO all good") is False

    def test_multiple_include_patterns_any_match(self):
        f = self._make_filter(include=["ERROR", "WARN"])
        assert f.should_pass("WARN low memory") is True
        assert f.should_pass("ERROR crash") is True
        assert f.should_pass("INFO startup") is False

    def test_case_insensitive_by_default(self):
        f = self._make_filter(include=["error"])
        assert f.should_pass("ERROR something") is True

    def test_case_sensitive_when_configured(self):
        f = self._make_filter(include=["error"], case_sensitive=True)
        assert f.should_pass("ERROR something") is False
        assert f.should_pass("error something") is True

    # --- filter ---

    def test_filter_returns_matching_lines(self):
        f = self._make_filter(include=["ERROR"])
        lines = ["INFO ok", "ERROR bad", "DEBUG verbose", "ERROR worse"]
        assert f.filter(lines) == ["ERROR bad", "ERROR worse"]

    def test_filter_empty_list(self):
        f = self._make_filter(include=["ERROR"])
        assert f.filter([]) == []

    def test_filter_no_rules_returns_all(self):
        f = PatternFilter()
        lines = ["a", "b", "c"]
        assert f.filter(lines) == lines

    # --- has_rules ---

    def test_has_rules_false_when_no_config(self):
        assert PatternFilter().has_rules is False

    def test_has_rules_true_with_include(self):
        f = self._make_filter(include=["ERROR"])
        assert f.has_rules is True

    def test_has_rules_true_with_exclude(self):
        f = self._make_filter(exclude=["DEBUG"])
        assert f.has_rules is True
