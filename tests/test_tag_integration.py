"""Tests for logdrift.tag_integration."""

from logdrift.tag_enricher import EnrichmentResult
from logdrift.tag_integration import TagIntegration


def _make_integration(*rules, merge_strategy="last_wins"):
    rule_dicts = [{"pattern": p, "tags": t} for p, t in rules]
    return TagIntegration.from_config(rules=rule_dicts, merge_strategy=merge_strategy)


class TestTagIntegration:
    def test_process_returns_enrichment_result(self):
        integration = _make_integration((r"ERROR", {"level": "error"}))
        result = integration.process("ERROR: boom")
        assert isinstance(result, EnrichmentResult)
        assert result.tags == {"level": "error"}

    def test_total_enriched_increments(self):
        integration = _make_integration()
        integration.process("line one")
        integration.process("line two")
        assert integration.total_enriched == 2

    def test_total_tagged_only_counts_matched(self):
        integration = _make_integration((r"ERROR", {"x": "1"}))
        integration.process("INFO: ok")
        integration.process("ERROR: bad")
        integration.process("DEBUG: verbose")
        assert integration.total_tagged == 1

    def test_callback_invoked_for_tagged_lines(self):
        integration = _make_integration((r"WARN", {"severity": "warn"}))
        received = []
        integration.add_callback(received.append)
        integration.process("WARN: low disk")
        integration.process("INFO: all fine")
        assert len(received) == 1
        assert received[0].tags == {"severity": "warn"}

    def test_callback_not_invoked_for_untagged_lines(self):
        integration = _make_integration((r"CRITICAL", {"x": "1"}))
        called = []
        integration.add_callback(called.append)
        integration.process("INFO: startup")
        assert called == []

    def test_multiple_callbacks_all_invoked(self):
        integration = _make_integration((r"ERROR", {"a": "1"}))
        sink_a, sink_b = [], []
        integration.add_callback(sink_a.append)
        integration.add_callback(sink_b.append)
        integration.process("ERROR: oops")
        assert len(sink_a) == 1
        assert len(sink_b) == 1

    def test_process_batch_processes_all_lines(self):
        integration = _make_integration((r"ERROR", {"level": "error"}))
        results = integration.process_batch(["ERROR: a", "INFO: b", "ERROR: c"])
        assert len(results) == 3
        assert integration.total_enriched == 3
        assert integration.total_tagged == 2

    def test_from_config_empty_rules(self):
        integration = TagIntegration.from_config()
        result = integration.process("anything")
        assert not result.has_tags

    def test_from_config_merge_strategy_forwarded(self):
        integration = TagIntegration.from_config(
            rules=[
                {"pattern": r"ERROR", "tags": {"level": "error"}},
                {"pattern": r"disk", "tags": {"level": "disk"}},
            ],
            merge_strategy="first_wins",
        )
        result = integration.process("ERROR: disk full")
        assert result.tags["level"] == "error"
