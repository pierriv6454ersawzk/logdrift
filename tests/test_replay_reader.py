"""Tests for ReplayReader and ReplayConfig."""

from __future__ import annotations

import os
import tempfile
from typing import List

import pytest

from logdrift.replay_reader import ReplayConfig, ReplayReader


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _write_tmp(lines: List[str]) -> str:
    fd, path = tempfile.mkstemp(suffix=".log")
    with os.fdopen(fd, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


class _FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._t = start
        self.calls: int = 0

    def __call__(self) -> float:
        self.calls += 1
        return self._t

    def advance(self, delta: float) -> None:
        self._t += delta


class _CaptureSleep:
    def __init__(self) -> None:
        self.delays: List[float] = []

    def __call__(self, delay: float) -> None:
        self.delays.append(delay)


# ---------------------------------------------------------------------------
# ReplayConfig
# ---------------------------------------------------------------------------


class TestReplayConfig:
    def test_negative_multiplier_raises(self):
        with pytest.raises(ValueError, match="rate_multiplier"):
            ReplayConfig(rate_multiplier=-1.0)

    def test_zero_max_lines_raises(self):
        with pytest.raises(ValueError, match="max_lines"):
            ReplayConfig(max_lines=0)

    def test_valid_config_does_not_raise(self):
        cfg = ReplayConfig(rate_multiplier=2.0, max_lines=10, loop=True)
        assert cfg.rate_multiplier == 2.0
        assert cfg.max_lines == 10
        assert cfg.loop is True


# ---------------------------------------------------------------------------
# ReplayReader
# ---------------------------------------------------------------------------


class TestReplayReader:
    def test_reads_all_lines(self):
        path = _write_tmp(["alpha", "beta", "gamma"])
        reader = ReplayReader(path, ReplayConfig(rate_multiplier=0))
        result = list(reader.lines())
        assert result == ["alpha", "beta", "gamma"]

    def test_strips_newline(self):
        path = _write_tmp(["hello"])
        reader = ReplayReader(path, ReplayConfig(rate_multiplier=0))
        assert list(reader.lines()) == ["hello"]

    def test_lines_emitted_counter(self):
        path = _write_tmp(["a", "b", "c"])
        reader = ReplayReader(path, ReplayConfig(rate_multiplier=0))
        list(reader.lines())
        assert reader.lines_emitted == 3

    def test_max_lines_limits_output(self):
        path = _write_tmp(["a", "b", "c", "d"])
        reader = ReplayReader(path, ReplayConfig(rate_multiplier=0, max_lines=2))
        result = list(reader.lines())
        assert result == ["a", "b"]

    def test_stop_halts_iteration(self):
        path = _write_tmp(["x"] * 100)
        reader = ReplayReader(path, ReplayConfig(rate_multiplier=0))
        collected: List[str] = []
        for line in reader.lines():
            collected.append(line)
            if len(collected) == 3:
                reader.stop()
        assert len(collected) == 3

    def test_no_sleep_when_multiplier_zero(self):
        path = _write_tmp(["a", "b"])
        sleep = _CaptureSleep()
        reader = ReplayReader(
            path, ReplayConfig(rate_multiplier=0), sleep=sleep
        )
        list(reader.lines())
        assert sleep.delays == []

    def test_loop_repeats_content(self):
        path = _write_tmp(["line1", "line2"])
        reader = ReplayReader(
            path, ReplayConfig(rate_multiplier=0, max_lines=5, loop=True)
        )
        result = list(reader.lines())
        assert len(result) == 5
        assert result[0] == "line1"
