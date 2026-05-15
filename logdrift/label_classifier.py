"""Classifies log lines into severity labels based on keyword patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Pattern


class Severity(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    UNKNOWN = "UNKNOWN"


_DEFAULT_PATTERNS: Dict[Severity, List[str]] = {
    Severity.CRITICAL: [r"\bcritical\b", r"\bfatal\b", r"\bpanic\b"],
    Severity.ERROR: [r"\berror\b", r"\bexception\b", r"\bfailed\b", r"\bfailure\b"],
    Severity.WARNING: [r"\bwarn(?:ing)?\b", r"\bdeprecated\b", r"\bretry\b"],
    Severity.INFO: [r"\binfo\b", r"\bstarted\b", r"\bstopped\b", r"\bready\b"],
    Severity.DEBUG: [r"\bdebug\b", r"\btrace\b", r"\bverbose\b"],
}

# Priority order: higher severity wins
_SEVERITY_ORDER = [
    Severity.CRITICAL,
    Severity.ERROR,
    Severity.WARNING,
    Severity.INFO,
    Severity.DEBUG,
]


@dataclass
class ClassifierConfig:
    case_sensitive: bool = False
    custom_patterns: Dict[str, List[str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for key in self.custom_patterns:
            try:
                Severity(key.upper())
            except ValueError:
                raise ValueError(
                    f"Invalid severity key in custom_patterns: {key!r}. "
                    f"Must be one of {[s.value for s in Severity]}."
                )


@dataclass(frozen=True)
class ClassificationResult:
    severity: Severity
    matched_pattern: Optional[str]


class LabelClassifier:
    """Assigns a Severity label to each log line."""

    def __init__(self, config: Optional[ClassifierConfig] = None) -> None:
        self._config = config or ClassifierConfig()
        flags = 0 if self._config.case_sensitive else re.IGNORECASE
        self._compiled: Dict[Severity, List[Pattern[str]]] = {}

        for severity in _SEVERITY_ORDER:
            raw_patterns = list(_DEFAULT_PATTERNS.get(severity, []))
            custom = self._config.custom_patterns.get(severity.value, [])
            raw_patterns.extend(custom)
            self._compiled[severity] = [
                re.compile(p, flags) for p in raw_patterns
            ]

    def classify(self, line: str) -> ClassificationResult:
        """Return the highest matching severity for *line*."""
        for severity in _SEVERITY_ORDER:
            for pattern in self._compiled[severity]:
                if pattern.search(line):
                    return ClassificationResult(
                        severity=severity, matched_pattern=pattern.pattern
                    )
        return ClassificationResult(severity=Severity.UNKNOWN, matched_pattern=None)
