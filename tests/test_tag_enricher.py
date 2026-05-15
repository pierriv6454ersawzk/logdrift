"""Tests for logdrift.tag_enricher."""

import pytest

from logdrift.tag_enricher import (
    EnrichmentResult,
    TagEnricher,
    TagEnricherConfig,
    TagRule,
)


def _make_enricher(*rules, merge_strategy="last_wins"):
    tag_rules = [TagRule(pattern=p, tags=t) for p, t in rules]
    config = TagEnricherConfig(rules=tag_rules, merge_strategy=merge_strategy)
    return TagEnricher(config)


class TestTagRule:
    def test_invalid_pattern_raises(self):
        with pytest.raises(ValueError, match="Invalid pattern"):
            TagRule(pattern="[unclosed", tags={})

    def test_valid_pattern_compiles(self):
        rule = TagRule(pattern=r"ERROR", tags={"level": "error"})
        assert rule.matches("ERROR: something went wrong")

    def test_non_matching_line(self):
        rule = TagRule(pattern=r"CRITICAL", tags={"level": "critical"})
        assert not rule.matches("INFO: all good")


class TestTagEnricherConfig:
    def test_invalid_merge_strategy_raises(self):
        with pytest.raises(ValueError, match="merge_strategy"):
            TagEnricherConfig(merge_strategy="unknown")

    def test_valid_strategies_accepted(self):
        for strategy in ("last_wins", "first_wins"):
            cfg = TagEnricherConfig(merge_strategy=strategy)
            assert cfg.merge_strategy == strategy


class TestTagEnricher:
    def test_no_rules_returns_empty_tags(self):
        enricher = TagEnricher()
        result = enricher.enrich("some log line")
        assert result.tags == {}
        assert result.matched_rules == 0
        assert not result.has_tags

    def test_matching_rule_attaches_tags(self):
        enricher = _make_enricher((r"ERROR", {"severity": "high"}))
        result = enricher.enrich("ERROR: disk full")
        assert result.tags == {"severity": "high"}
        assert result.matched_rules == 1
        assert result.has_tags

    def test_non_matching_rule_no_tags(self):
        enricher = _make_enricher((r"CRITICAL", {"severity": "critical"}))
        result = enricher.enrich("INFO: startup complete")
        assert result.tags == {}
        assert result.matched_rules == 0

    def test_multiple_rules_merge_last_wins(self):
        enricher = _make_enricher(
            (r"ERROR", {"level": "error", "team": "platform"}),
            (r"disk", {"level": "disk-error"}),
            merge_strategy="last_wins",
        )
        result = enricher.enrich("ERROR: disk full")
        assert result.tags["level"] == "disk-error"
        assert result.tags["team"] == "platform"
        assert result.matched_rules == 2

    def test_multiple_rules_merge_first_wins(self):
        enricher = _make_enricher(
            (r"ERROR", {"level": "error"}),
            (r"disk", {"level": "disk-error"}),
            merge_strategy="first_wins",
        )
        result = enricher.enrich("ERROR: disk full")
        assert result.tags["level"] == "error"

    def test_enrich_batch_returns_all_results(self):
        enricher = _make_enricher((r"WARN", {"level": "warn"}))
        lines = ["WARN: low memory", "INFO: ok", "WARN: high cpu"]
        results = enricher.enrich_batch(lines)
        assert len(results) == 3
        assert results[0].has_tags
        assert not results[1].has_tags
        assert results[2].has_tags

    def test_from_rules_convenience_constructor(self):
        enricher = TagEnricher.from_rules([
            {"pattern": r"timeout", "tags": {"type": "network"}},
        ])
        result = enricher.enrich("connection timeout after 30s")
        assert result.tags == {"type": "network"}

    def test_result_preserves_original_line(self):
        enricher = _make_enricher((r"ERROR", {"x": "1"}))
        line = "ERROR: something"
        result = enricher.enrich(line)
        assert result.line is line
