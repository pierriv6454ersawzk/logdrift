"""Tests for ReplayIntegration and ReplaySource."""

from __future__ import annotations

import os
import tempfile
from typing import List

import pytest

from logdrift.replay_integration import ReplayIntegration, ReplaySource
from logdrift.replay_reader import ReplayConfig, ReplayReader


def _write_tmp(lines: List[str]) -> str:
    fd, path = tempfile.mkstemp(suffix=".log")
    with os.fdopen(fd, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


class TestReplaySource:
    def test_yields_lines(self):
        path = _write_tmp(["foo", "bar"])
        reader = ReplayReader(path, ReplayConfig(rate_multiplier=0))
        source = ReplaySource(reader)
        assert list(source.lines()) == ["foo", "bar"]

    def test_close_stops_reader(self):
        path = _write_tmp(["a"] * 50)
        reader = ReplayReader(path, ReplayConfig(rate_multiplier=0))
        source = ReplaySource(reader)
        collected: List[str] = []
        for line in source.lines():
            collected.append(line)
            if len(collected) == 2:
                source.close()
        assert len(collected) == 2


class TestReplayIntegration:
    def test_from_config_creates_source(self):
        path = _write_tmp(["hello", "world"])
        integration = ReplayIntegration.from_config(path, rate_multiplier=0)
        result = list(integration.source.lines())
        assert result == ["hello", "world"]

    def test_lines_emitted_tracks_count(self):
        path = _write_tmp(["a", "b", "c"])
        integration = ReplayIntegration.from_config(path, rate_multiplier=0)
        list(integration.source.lines())
        assert integration.lines_emitted == 3

    def test_max_lines_respected(self):
        path = _write_tmp(["a", "b", "c", "d", "e"])
        integration = ReplayIntegration.from_config(
            path, rate_multiplier=0, max_lines=3
        )
        result = list(integration.source.lines())
        assert len(result) == 3

    def test_stop_halts_source(self):
        path = _write_tmp(["x"] * 100)
        integration = ReplayIntegration.from_config(path, rate_multiplier=0)
        collected: List[str] = []
        for line in integration.source.lines():
            collected.append(line)
            if len(collected) == 4:
                integration.stop()
        assert len(collected) == 4

    def test_loop_option_passed_through(self):
        path = _write_tmp(["z"])
        integration = ReplayIntegration.from_config(
            path, rate_multiplier=0, max_lines=3, loop=True
        )
        result = list(integration.source.lines())
        assert result == ["z", "z", "z"]
