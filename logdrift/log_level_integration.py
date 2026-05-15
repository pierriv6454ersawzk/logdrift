"""Thin integration layer that wires LogLevelFilter into the Pipeline."""

from __future__ import annotations

from typing import List, Optional

from logdrift.log_level_filter import LogLevelFilter, LogLevelFilterConfig


class LogLevelIntegration:
    """Wraps :class:`LogLevelFilter` and exposes pipeline-compatible helpers.

    Typical usage inside a pipeline step::

        integration = LogLevelIntegration.from_config(
            min_level="WARNING",
            include_unrecognised=False,
        )
        for line in source_lines:
            if integration.process(line) is not None:
                downstream.write(line)
    """

    def __init__(self, filter_: LogLevelFilter) -> None:
        self._filter = filter_
        self._passed = 0
        self._dropped = 0

    # ------------------------------------------------------------------
    # Pipeline API
    # ------------------------------------------------------------------

    def process(self, line: str) -> Optional[str]:
        """Return *line* if it passes the level filter, else *None*."""
        if self._filter.should_pass(line):
            self._passed += 1
            return line
        self._dropped += 1
        return None

    def process_batch(self, lines: List[str]) -> List[str]:
        """Filter a list of lines and return only those that pass."""
        return [line for line in lines if self.process(line) is not None]

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    @property
    def passed(self) -> int:
        """Total lines forwarded downstream since creation."""
        return self._passed

    @property
    def dropped(self) -> int:
        """Total lines suppressed since creation."""
        return self._dropped

    def stats(self) -> dict:
        total = self._passed + self._dropped
        return {
            "passed": self._passed,
            "dropped": self._dropped,
            "total": total,
            "pass_rate": self._passed / total if total else 0.0,
        }

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_config(
        cls,
        min_level: str = "DEBUG",
        include_unrecognised: bool = True,
        extra_patterns: Optional[List[str]] = None,
    ) -> "LogLevelIntegration":
        """Convenience constructor that builds config and filter together."""
        config = LogLevelFilterConfig(
            min_level=min_level,
            include_unrecognised=include_unrecognised,
            extra_patterns=extra_patterns or [],
        )
        return cls(LogLevelFilter(config))
