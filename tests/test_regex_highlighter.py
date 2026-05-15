"""Tests for logdrift.regex_highlighter."""

import pytest

from logdrift.regex_highlighter import HighlightRule, HighlightResult, RegexHighlighter


# ---------------------------------------------------------------------------
# HighlightRule
# ---------------------------------------------------------------------------

class TestHighlightRule:
    def test_invalid_pattern_raises(self):
        with pytest.raises(ValueError, match="Invalid highlight pattern"):
            HighlightRule(pattern="[unclosed")

    def test_valid_pattern_compiles(self):
        rule = HighlightRule(pattern=r"ERROR", label="error")
        assert rule.label == "error"

    def test_find_spans_single_match(self):
        rule = HighlightRule(pattern=r"ERROR")
        spans = rule.find_spans("2024 ERROR something")
        assert spans == [(5, 10)]

    def test_find_spans_multiple_matches(self):
        rule = HighlightRule(pattern=r"\d+")
        spans = rule.find_spans("port 80 and 443")
        assert len(spans) == 2

    def test_find_spans_no_match(self):
        rule = HighlightRule(pattern=r"CRITICAL")
        assert rule.find_spans("all fine here") == []


# ---------------------------------------------------------------------------
# RegexHighlighter
# ---------------------------------------------------------------------------

def _no_color_highlighter(*patterns: str) -> RegexHighlighter:
    rules = [HighlightRule(pattern=p) for p in patterns]
    return RegexHighlighter(rules=rules, use_color=False)


class TestRegexHighlighter:
    def test_no_rules_returns_original(self):
        h = RegexHighlighter(use_color=False)
        result = h.highlight("hello world")
        assert result.highlighted == "hello world"
        assert not result.has_match

    def test_matching_rule_sets_matched_rules(self):
        h = _no_color_highlighter(r"ERROR")
        result = h.highlight("ERROR: disk full")
        assert result.has_match
        assert "ERROR" in result.matched_rules

    def test_non_matching_rule_no_match(self):
        h = _no_color_highlighter(r"CRITICAL")
        result = h.highlight("INFO: all good")
        assert not result.has_match

    def test_add_rule_after_init(self):
        h = RegexHighlighter(use_color=False)
        h.add_rule(HighlightRule(pattern=r"WARN", label="warning"))
        result = h.highlight("WARN: low memory")
        assert result.has_match
        assert "warning" in result.matched_rules

    def test_color_wraps_match(self):
        rule = HighlightRule(pattern=r"ERROR", color_code="\033[31m")
        h = RegexHighlighter(rules=[rule], use_color=True)
        result = h.highlight("ERROR: boom")
        assert "\033[31m" in result.highlighted
        assert "\033[0m" in result.highlighted
        assert result.original == "ERROR: boom"

    def test_overlapping_spans_skipped(self):
        # Two rules that match same region — second should be skipped
        r1 = HighlightRule(pattern=r"ERROR", color_code="\033[31m")
        r2 = HighlightRule(pattern=r"ERRO", color_code="\033[33m")
        h = RegexHighlighter(rules=[r1, r2], use_color=True)
        result = h.highlight("ERROR")
        # Should not raise and should contain at least one color code
        assert "\033[0m" in result.highlighted

    def test_multiple_non_overlapping_spans(self):
        rule = HighlightRule(pattern=r"\d+", color_code="\033[32m")
        h = RegexHighlighter(rules=[rule], use_color=True)
        result = h.highlight("port 80 and 443")
        assert result.highlighted.count("\033[32m") == 2
