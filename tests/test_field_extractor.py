"""Tests for FieldExtractor, ExtractionResult, and FieldIntegration."""
import pytest

from logdrift.field_extractor import ExtractionResult, FieldExtractor, FieldExtractorConfig
from logdrift.field_integration import FieldIntegration


def _make_extractor(keys=None) -> FieldExtractor:
    return FieldExtractor(config=FieldExtractorConfig(keys=keys))


class TestFieldExtractorConfig:
    def test_invalid_keys_type_raises(self):
        with pytest.raises(TypeError):
            FieldExtractorConfig(keys="not-a-list")

    def test_valid_keys_list_does_not_raise(self):
        cfg = FieldExtractorConfig(keys=["level", "msg"])
        assert cfg.keys == ["level", "msg"]

    def test_none_keys_is_default(self):
        cfg = FieldExtractorConfig()
        assert cfg.keys is None


class TestExtractionResult:
    def test_has_fields_false_when_empty(self):
        r = ExtractionResult(line="hello")
        assert not r.has_fields

    def test_has_fields_true_when_populated(self):
        r = ExtractionResult(line="x", fields={"k": "v"})
        assert r.has_fields

    def test_get_returns_value(self):
        r = ExtractionResult(line="x", fields={"level": "error"})
        assert r.get("level") == "error"

    def test_get_returns_default_for_missing(self):
        r = ExtractionResult(line="x")
        assert r.get("missing", "fallback") == "fallback"


class TestFieldExtractor:
    def test_simple_kv_parsed(self):
        ex = _make_extractor()
        result = ex.extract("level=info msg=started")
        assert result.fields["level"] == "info"
        assert result.fields["msg"] == "started"

    def test_quoted_value_stripped(self):
        ex = _make_extractor()
        result = ex.extract('msg="hello world" status=ok')
        assert result.fields["msg"] == "hello world"

    def test_key_filter_excludes_unwanted(self):
        ex = _make_extractor(keys=["level"])
        result = ex.extract("level=warn msg=ignored")
        assert "level" in result.fields
        assert "msg" not in result.fields

    def test_no_kv_returns_empty_fields(self):
        ex = _make_extractor()
        result = ex.extract("plain log line without pairs")
        assert not result.has_fields

    def test_total_processed_increments(self):
        ex = _make_extractor()
        ex.extract("a=1")
        ex.extract("b=2")
        assert ex.total_processed == 2

    def test_total_matched_only_counts_with_fields(self):
        ex = _make_extractor()
        ex.extract("no pairs here")
        ex.extract("key=val")
        assert ex.total_matched == 1

    def test_batch_extract_returns_all(self):
        ex = _make_extractor()
        results = ex.extract_batch(["a=1", "plain", "b=2"])
        assert len(results) == 3
        assert results[0].fields["a"] == "1"
        assert not results[1].has_fields


class TestFieldIntegration:
    def test_process_returns_result(self):
        integ = FieldIntegration()
        result = integ.process("level=debug")
        assert result.fields["level"] == "debug"

    def test_callback_is_called(self):
        collected = []
        integ = FieldIntegration()
        integ.add_callback(collected.append)
        integ.process("x=1")
        assert len(collected) == 1
        assert collected[0].fields["x"] == "1"

    def test_total_processed_via_integration(self):
        integ = FieldIntegration()
        integ.process_batch(["a=1", "b=2", "plain"])
        assert integ.total_processed == 3

    def test_from_config_applies_key_filter(self):
        cfg = FieldExtractorConfig(keys=["status"])
        integ = FieldIntegration.from_config(cfg)
        result = integ.process("status=200 path=/api")
        assert "status" in result.fields
        assert "path" not in result.fields
