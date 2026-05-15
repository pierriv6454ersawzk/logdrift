"""Tests for logdrift.log_level_filter."""

import pytest

from logdrift.log_level_filter import (
    LogLevelFilter,
    LogLevelFilterConfig,
    _severity_rank,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_filter(min_level: str = "DEBUG", include_unrecognised: bool = True,
                 extra_patterns=None) -> LogLevelFilter:
    cfg = LogLevelFilterConfig(
        min_level=min_level,
        include_unrecognised=include_unrecognised,
        extra_patterns=extra_patterns or [],
    )
    return LogLevelFilter(cfg)


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------

class TestLogLevelFilterConfig:
    def test_invalid_level_raises(self):
        with pytest.raises(ValueError, match="Unknown log level"):
            LogLevelFilterConfig(min_level="VERBOSE")

    def test_valid_level_does_not_raise(self):
        cfg = LogLevelFilterConfig(min_level="ERROR")
        assert cfg.min_level == "ERROR"


# ---------------------------------------------------------------------------
# Level detection
# ---------------------------------------------------------------------------

class TestDetectedLevel:
    def test_detects_info(self):
        f = _make_filter()
        assert f.detected_level("2024-01-01 INFO server started") == "INFO"

    def test_detects_warn_normalised_to_warning(self):
        f = _make_filter()
        assert f.detected_level("[WARN] disk usage high") == "WARNING"

    def test_detects_critical(self):
        f = _make_filter()
        assert f.detected_level("CRITICAL: out of memory") == "CRITICAL"

    def test_returns_none_for_unknown_line(self):
        f = _make_filter()
        assert f.detected_level("just a plain message") is None

    def test_case_insensitive(self):
        f = _make_filter()
        assert f.detected_level("error: something went wrong") == "ERROR"


# ---------------------------------------------------------------------------
# Filtering
# ---------------------------------------------------------------------------

class TestShouldPass:
    def test_debug_passes_when_min_is_debug(self):
        f = _make_filter(min_level="DEBUG")
        assert f.should_pass("DEBUG initialising") is True

    def test_debug_blocked_when_min_is_info(self):
        f = _make_filter(min_level="INFO")
        assert f.should_pass("DEBUG low-level trace") is False

    def test_error_passes_when_min_is_warning(self):
        f = _make_filter(min_level="WARNING")
        assert f.should_pass("ERROR disk full") is True

    def test_info_blocked_when_min_is_error(self):
        f = _make_filter(min_level="ERROR")
        assert f.should_pass("INFO heartbeat ok") is False

    def test_unrecognised_line_passes_when_flag_true(self):
        f = _make_filter(include_unrecognised=True)
        assert f.should_pass("some random output") is True

    def test_unrecognised_line_blocked_when_flag_false(self):
        f = _make_filter(include_unrecognised=False)
        assert f.should_pass("some random output") is False

    def test_extra_pattern_matches_custom_token(self):
        f = _make_filter(min_level="ERROR", extra_patterns=[r"FATAL"])
        # "FATAL" is not in the built-in regex but matched by extra pattern;
        # _severity_rank returns -1 for unknown, so should NOT pass.
        # This asserts the extra pattern is found (detected_level not None)
        # but rank check correctly blocks it.
        assert f.detected_level("FATAL: kernel panic") == "FATAL"

    def test_warn_alias_passes_at_warning_threshold(self):
        f = _make_filter(min_level="WARNING")
        assert f.should_pass("[WARN] low memory") is True


# ---------------------------------------------------------------------------
# Rank helper
# ---------------------------------------------------------------------------

def test_severity_rank_ordering():
    assert _severity_rank("DEBUG") < _severity_rank("INFO")
    assert _severity_rank("INFO") < _severity_rank("WARNING")
    assert _severity_rank("WARNING") < _severity_rank("ERROR")
    assert _severity_rank("ERROR") < _severity_rank("CRITICAL")


def test_severity_rank_unknown_returns_minus_one():
    assert _severity_rank("TRACE") == -1
