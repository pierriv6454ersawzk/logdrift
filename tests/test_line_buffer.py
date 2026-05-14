"""Tests for logdrift.line_buffer."""

import pytest

from logdrift.line_buffer import LineBuffer, LineBufferConfig


def _make_buffer(capacity: int = 5) -> LineBuffer:
    return LineBuffer(LineBufferConfig(capacity=capacity))


class TestLineBufferConfig:
    def test_invalid_capacity_raises(self) -> None:
        with pytest.raises(ValueError, match="capacity"):
            LineBufferConfig(capacity=0)

    def test_negative_capacity_raises(self) -> None:
        with pytest.raises(ValueError):
            LineBufferConfig(capacity=-3)


class TestLineBuffer:
    def test_empty_on_init(self) -> None:
        buf = _make_buffer()
        assert len(buf) == 0

    def test_append_increases_length(self) -> None:
        buf = _make_buffer()
        buf.append("line one")
        assert len(buf) == 1

    def test_capacity_respected(self) -> None:
        buf = _make_buffer(capacity=3)
        for i in range(10):
            buf.append(f"line {i}")
        assert len(buf) == 3

    def test_oldest_evicted_when_full(self) -> None:
        buf = _make_buffer(capacity=3)
        buf.append("a")
        buf.append("b")
        buf.append("c")
        buf.append("d")  # evicts "a"
        assert list(buf) == ["b", "c", "d"]

    def test_snapshot_all(self) -> None:
        buf = _make_buffer()
        buf.append("x")
        buf.append("y")
        assert buf.snapshot() == ["x", "y"]

    def test_snapshot_n_returns_last_n(self) -> None:
        buf = _make_buffer()
        for ch in "abcde":
            buf.append(ch)
        assert buf.snapshot(n=2) == ["d", "e"]

    def test_snapshot_n_zero_returns_empty(self) -> None:
        buf = _make_buffer()
        buf.append("a")
        assert buf.snapshot(n=0) == []

    def test_snapshot_n_negative_raises(self) -> None:
        buf = _make_buffer()
        with pytest.raises(ValueError):
            buf.snapshot(n=-1)

    def test_snapshot_n_larger_than_size(self) -> None:
        buf = _make_buffer()
        buf.append("only")
        assert buf.snapshot(n=10) == ["only"]

    def test_is_full_false_initially(self) -> None:
        assert not _make_buffer(capacity=2).is_full()

    def test_is_full_true_when_at_capacity(self) -> None:
        buf = _make_buffer(capacity=2)
        buf.append("a")
        buf.append("b")
        assert buf.is_full()

    def test_clear_empties_buffer(self) -> None:
        buf = _make_buffer()
        buf.append("a")
        buf.clear()
        assert len(buf) == 0

    def test_iteration_order(self) -> None:
        buf = _make_buffer(capacity=4)
        lines = ["first", "second", "third"]
        for ln in lines:
            buf.append(ln)
        assert list(buf) == lines
