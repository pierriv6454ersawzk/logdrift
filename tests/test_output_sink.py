"""Tests for logdrift.output_sink."""

from __future__ import annotations

import io
import os
import tempfile

import pytest

from logdrift.output_sink import FileSink, MultiSink, StreamSink


class TestStreamSink:
    def _make_sink(self) -> tuple[StreamSink, io.StringIO]:
        buf = io.StringIO()
        return StreamSink(stream=buf), buf

    def test_write_appends_newline(self) -> None:
        sink, buf = self._make_sink()
        sink.write("hello")
        assert buf.getvalue() == "hello\n"

    def test_multiple_writes(self) -> None:
        sink, buf = self._make_sink()
        sink.write("line1")
        sink.write("line2")
        assert buf.getvalue() == "line1\nline2\n"

    def test_close_does_not_raise(self) -> None:
        sink, _ = self._make_sink()
        sink.close()  # should not raise

    def test_write_empty_string(self) -> None:
        sink, buf = self._make_sink()
        sink.write("")
        assert buf.getvalue() == "\n"


class TestFileSink:
    def test_write_creates_file_content(self) -> None:
        with tempfile.NamedTemporaryFile(mode="r", suffix=".log", delete=False) as f:
            path = f.name
        try:
            sink = FileSink(path)
            sink.write("entry one")
            sink.write("entry two")
            sink.close()
            content = open(path).read()
            assert content == "entry one\nentry two\n"
        finally:
            os.unlink(path)

    def test_close_marks_file_closed(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            path = f.name
        try:
            sink = FileSink(path)
            sink.close()
            assert sink._file.closed
        finally:
            os.unlink(path)

    def test_double_close_does_not_raise(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".log", delete=False) as f:
            path = f.name
        try:
            sink = FileSink(path)
            sink.close()
            sink.close()  # should not raise
        finally:
            os.unlink(path)


class TestMultiSink:
    def test_write_reaches_all_sinks(self) -> None:
        buf1, buf2 = io.StringIO(), io.StringIO()
        multi = MultiSink(StreamSink(buf1), StreamSink(buf2))
        multi.write("broadcast")
        assert buf1.getvalue() == "broadcast\n"
        assert buf2.getvalue() == "broadcast\n"

    def test_close_calls_all_sinks(self) -> None:
        closed: list[int] = []

        class _TrackingSink(StreamSink):
            def __init__(self, idx: int) -> None:
                super().__init__(io.StringIO())
                self._idx = idx

            def close(self) -> None:
                closed.append(self._idx)

        multi = MultiSink(_TrackingSink(0), _TrackingSink(1))
        multi.close()
        assert closed == [0, 1]

    def test_empty_multi_sink_write_does_not_raise(self) -> None:
        multi = MultiSink()
        multi.write("no sinks")  # should not raise
