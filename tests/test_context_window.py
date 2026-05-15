"""Tests for logdrift.context_window."""
import pytest

from logdrift.context_window import ContextCapture, ContextWindow, ContextWindowConfig


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

class TestContextWindowConfig:
    def test_negative_before_raises(self):
        with pytest.raises(ValueError, match="before"):
            ContextWindowConfig(before=-1)

    def test_negative_after_raises(self):
        with pytest.raises(ValueError, match="after"):
            ContextWindowConfig(after=-1)

    def test_zero_values_are_valid(self):
        cfg = ContextWindowConfig(before=0, after=0)
        assert cfg.before == 0 and cfg.after == 0


# ---------------------------------------------------------------------------
# ContextWindow behaviour
# ---------------------------------------------------------------------------

def _make_window(before: int = 2, after: int = 2) -> ContextWindow:
    return ContextWindow(ContextWindowConfig(before=before, after=after))


class TestContextWindow:
    def test_non_trigger_lines_produce_no_captures(self):
        cw = _make_window()
        for line in ["a", "b", "c"]:
            assert cw.feed(line) == []

    def test_trigger_with_zero_after_completes_immediately(self):
        cw = _make_window(before=1, after=0)
        cw.feed("x")
        results = cw.feed("trigger", is_trigger=True)
        assert len(results) == 1
        assert results[0].trigger_line == "trigger"
        assert results[0].before == ["x"]
        assert results[0].after == []

    def test_before_lines_captured_correctly(self):
        cw = _make_window(before=2, after=0)
        cw.feed("line1")
        cw.feed("line2")
        cw.feed("line3")
        results = cw.feed("TRIGGER", is_trigger=True)
        assert len(results) == 1
        assert results[0].before == ["line2", "line3"]

    def test_after_lines_captured_correctly(self):
        cw = _make_window(before=0, after=2)
        assert cw.feed("TRIGGER", is_trigger=True) == []
        assert cw.feed("post1") == []
        results = cw.feed("post2")
        assert len(results) == 1
        assert results[0].after == ["post1", "post2"]

    def test_all_lines_ordering(self):
        cw = _make_window(before=1, after=1)
        cw.feed("pre")
        cw.feed("TRIGGER", is_trigger=True)
        results = cw.feed("post")
        assert results[0].all_lines() == ["pre", "TRIGGER", "post"]

    def test_flush_returns_incomplete_captures(self):
        cw = _make_window(before=0, after=3)
        cw.feed("TRIGGER", is_trigger=True)
        cw.feed("a")
        # Only 1 of 3 after-lines delivered; flush should still return capture.
        flushed = cw.flush()
        assert len(flushed) == 1
        assert flushed[0].after == ["a"]

    def test_flush_clears_pending(self):
        cw = _make_window(before=0, after=2)
        cw.feed("TRIGGER", is_trigger=True)
        cw.flush()
        assert cw.flush() == []

    def test_multiple_triggers_tracked_independently(self):
        cw = _make_window(before=0, after=1)
        cw.feed("T1", is_trigger=True)
        cw.feed("T2", is_trigger=True)
        results = cw.feed("shared_after")
        # T1 completes; T2 still pending.
        assert len(results) == 1
        assert results[0].trigger_line == "T1"
        flushed = cw.flush()
        assert flushed[0].trigger_line == "T2"

    def test_before_buffer_respects_maxlen(self):
        cw = _make_window(before=2, after=0)
        for i in range(10):
            cw.feed(f"line{i}")
        results = cw.feed("T", is_trigger=True)
        assert results[0].before == ["line8", "line9"]
