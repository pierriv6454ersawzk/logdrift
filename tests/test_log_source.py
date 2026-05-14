"""Tests for logdrift.log_source."""

import io
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from logdrift.log_source import FileLogSource, StdinLogSource, open_source


class TestFileLogSource:
    def _write_lines(self, path: Path, lines):
        with open(path, "a") as fh:
            for line in lines:
                fh.write(line + "\n")
                fh.flush()

    def test_reads_appended_lines(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("")  # create empty file

        source = FileLogSource(str(log_file), poll_interval=0.01)
        self._write_lines(log_file, ["hello", "world"])

        collected = []
        for line in source.lines():
            collected.append(line)
            if len(collected) == 2:
                source.close()
                break

        assert collected == ["hello", "world"]

    def test_close_stops_iteration(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        source = FileLogSource(str(log_file), poll_interval=0.01)
        source.close()
        result = list(source.lines())
        assert result == []

    def test_strips_newline(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("")

        source = FileLogSource(str(log_file), poll_interval=0.01)
        self._write_lines(log_file, ["line1"])

        for line in source.lines():
            assert "\n" not in line
            source.close()
            break


class TestStdinLogSource:
    def test_yields_stdin_lines(self):
        fake_stdin = io.StringIO("alpha\nbeta\n")
        source = StdinLogSource()
        with patch("sys.stdin", fake_stdin):
            result = list(source.lines())
        assert result == ["alpha", "beta"]

    def test_close_stops_mid_iteration(self):
        source = StdinLogSource()
        source.close()
        fake_stdin = io.StringIO("should\nnot\nyield\n")
        with patch("sys.stdin", fake_stdin):
            result = list(source.lines())
        assert result == []


class TestOpenSource:
    def test_none_returns_stdin_source(self):
        src = open_source(None)
        assert isinstance(src, StdinLogSource)

    def test_dash_returns_stdin_source(self):
        src = open_source("-")
        assert isinstance(src, StdinLogSource)

    def test_path_returns_file_source(self, tmp_path):
        log_file = tmp_path / "app.log"
        log_file.write_text("")
        src = open_source(str(log_file))
        assert isinstance(src, FileLogSource)
        src.close()
