"""Tag enrichment: attach key-value metadata tags to log lines based on regex patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class TagRule:
    """A single pattern-to-tag mapping."""

    pattern: str
    tags: Dict[str, str]
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            self._compiled = re.compile(self.pattern)
        except re.error as exc:
            raise ValueError(f"Invalid pattern {self.pattern!r}: {exc}") from exc

    def matches(self, line: str) -> bool:
        return bool(self._compiled.search(line))


@dataclass
class EnrichmentResult:
    """Result of enriching a single log line."""

    line: str
    tags: Dict[str, str]
    matched_rules: int

    @property
    def has_tags(self) -> bool:
        return bool(self.tags)


@dataclass
class TagEnricherConfig:
    rules: List[TagRule] = field(default_factory=list)
    merge_strategy: str = "last_wins"  # or "first_wins"

    def __post_init__(self) -> None:
        valid = {"last_wins", "first_wins"}
        if self.merge_strategy not in valid:
            raise ValueError(
                f"merge_strategy must be one of {valid}, got {self.merge_strategy!r}"
            )


class TagEnricher:
    """Attaches metadata tags to log lines by matching against configured rules."""

    def __init__(self, config: Optional[TagEnricherConfig] = None) -> None:
        self._config = config or TagEnricherConfig()

    def enrich(self, line: str) -> EnrichmentResult:
        merged: Dict[str, str] = {}
        matched = 0

        rules = self._config.rules
        if self._config.merge_strategy == "first_wins":
            rules = list(reversed(rules))

        for rule in rules:
            if rule.matches(line):
                merged.update(rule.tags)
                matched += 1

        return EnrichmentResult(line=line, tags=merged, matched_rules=matched)

    def enrich_batch(self, lines: List[str]) -> List[EnrichmentResult]:
        return [self.enrich(line) for line in lines]

    @classmethod
    def from_rules(cls, rules: List[Dict]) -> "TagEnricher":
        """Convenience constructor from a list of plain dicts."""
        tag_rules = [
            TagRule(pattern=r["pattern"], tags=r.get("tags", {}))
            for r in rules
        ]
        return cls(TagEnricherConfig(rules=tag_rules))
