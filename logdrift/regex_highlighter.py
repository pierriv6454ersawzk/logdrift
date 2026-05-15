"""Regex-based line highlighter that marks matching segments in log output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class HighlightRule:
    pattern: str
    label: str = ""
    color_code: str = "\033[33m"  # yellow by default

    def __post_init__(self) -> None:
        try:
            self._compiled = re.compile(self.pattern)
        except re.error as exc:
            raise ValueError(f"Invalid highlight pattern {self.pattern!r}: {exc}") from exc

    def find_spans(self, line: str) -> List[Tuple[int, int]]:
        """Return (start, end) spans for all matches in *line*."""
        return [m.span() for m in self._compiled.finditer(line)]


@dataclass
class HighlightResult:
    original: str
    highlighted: str
    matched_rules: List[str] = field(default_factory=list)

    @property
    def has_match(self) -> bool:
        return bool(self.matched_rules)


RESET = "\033[0m"


class RegexHighlighter:
    """Applies a list of HighlightRules to individual log lines."""

    def __init__(self, rules: Optional[List[HighlightRule]] = None, use_color: bool = True) -> None:
        self._rules: List[HighlightRule] = list(rules or [])
        self._use_color = use_color

    def add_rule(self, rule: HighlightRule) -> None:
        self._rules.append(rule)

    def highlight(self, line: str) -> HighlightResult:
        """Return a HighlightResult with ANSI-annotated text where rules match."""
        if not self._rules:
            return HighlightResult(original=line, highlighted=line)

        matched: List[str] = []
        # Collect all (start, end, color) intervals across all rules
        intervals: List[Tuple[int, int, str]] = []
        for rule in self._rules:
            spans = rule.find_spans(line)
            if spans:
                matched.append(rule.label or rule.pattern)
                if self._use_color:
                    for start, end in spans:
                        intervals.append((start, end, rule.color_code))

        if not intervals or not self._use_color:
            return HighlightResult(original=line, highlighted=line, matched_rules=matched)

        # Sort by start position; apply non-overlapping highlights
        intervals.sort(key=lambda t: t[0])
        result: List[str] = []
        cursor = 0
        for start, end, color in intervals:
            if start < cursor:
                continue
            result.append(line[cursor:start])
            result.append(f"{color}{line[start:end]}{RESET}")
            cursor = end
        result.append(line[cursor:])
        return HighlightResult(original=line, highlighted="".join(result), matched_rules=matched)
