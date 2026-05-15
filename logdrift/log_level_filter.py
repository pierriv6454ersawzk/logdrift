"""Filter log lines by severity level (e.g. DEBUG, INFO, WARNING, ERROR)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

# Canonical ordering — higher index == higher severity
_LEVELS = ["DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"]

# Regex that tries to find a level token in a log line
_LEVEL_RE = re.compile(
    r"\b(DEBUG|INFO|WARN(?:ING)?|ERROR|CRITICAL)\b", re.IGNORECASE
)


def _severity_rank(level: str) -> int:
    """Return a comparable integer rank for *level*; unknown levels get 0."""
    upper = level.upper()
    if upper == "WARN":
        upper = "WARNING"
    try:
        return _LEVELS.index(upper)
    except ValueError:
        return -1


@dataclass
class LogLevelFilterConfig:
    min_level: str = "DEBUG"
    include_unrecognised: bool = True
    extra_patterns: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.min_level.upper() not in [l.upper() for l in _LEVELS]:
            raise ValueError(
                f"Unknown log level: {self.min_level!r}. "
                f"Valid options: {_LEVELS}"
            )


class LogLevelFilter:
    """Pass only log lines whose detected level is >= *min_level*."""

    def __init__(self, config: LogLevelFilterConfig) -> None:
        self._min_rank = _severity_rank(config.min_level)
        self._include_unrecognised = config.include_unrecognised
        self._extra: List[re.Pattern] = [
            re.compile(p, re.IGNORECASE) for p in config.extra_patterns
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_pass(self, line: str) -> bool:
        """Return *True* if *line* should be forwarded downstream."""
        level = self._detect_level(line)
        if level is None:
            return self._include_unrecognised
        return _severity_rank(level) >= self._min_rank

    def detected_level(self, line: str) -> Optional[str]:
        """Return the normalised level string found in *line*, or *None*."""
        raw = self._detect_level(line)
        if raw is None:
            return None
        upper = raw.upper()
        return "WARNING" if upper == "WARN" else upper

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_level(self, line: str) -> Optional[str]:
        for pattern in self._extra:
            m = pattern.search(line)
            if m:
                return m.group(0)
        m = _LEVEL_RE.search(line)
        return m.group(0) if m else None
