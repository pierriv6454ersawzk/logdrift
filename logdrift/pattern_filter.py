"""Pattern-based log line filtering with include/exclude rules."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class PatternFilterConfig:
    """Configuration for pattern-based filtering."""
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)
    case_sensitive: bool = False

    def __post_init__(self) -> None:
        flags = 0 if self.case_sensitive else re.IGNORECASE
        self._include_re: List[re.Pattern[str]] = [
            re.compile(p, flags) for p in self.include_patterns
        ]
        self._exclude_re: List[re.Pattern[str]] = [
            re.compile(p, flags) for p in self.exclude_patterns
        ]


class PatternFilter:
    """Filters log lines based on include/exclude regex patterns.

    Rules:
    - If include patterns are defined, a line must match at least one.
    - If exclude patterns are defined, a line must not match any.
    - If no patterns are defined, all lines pass.
    """

    def __init__(self, config: Optional[PatternFilterConfig] = None) -> None:
        self._config = config or PatternFilterConfig()

    def should_pass(self, line: str) -> bool:
        """Return True if the line passes the filter."""
        cfg = self._config

        if cfg._include_re:
            if not any(p.search(line) for p in cfg._include_re):
                return False

        if cfg._exclude_re:
            if any(p.search(line) for p in cfg._exclude_re):
                return False

        return True

    def filter(self, lines: List[str]) -> List[str]:
        """Return only lines that pass the filter."""
        return [line for line in lines if self.should_pass(line)]

    @property
    def has_rules(self) -> bool:
        """Return True if any patterns are configured."""
        cfg = self._config
        return bool(cfg._include_re or cfg._exclude_re)
