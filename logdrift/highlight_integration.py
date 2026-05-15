"""Integrates RegexHighlighter into the log processing pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from logdrift.regex_highlighter import HighlightResult, HighlightRule, RegexHighlighter


@dataclass
class HighlightConfig:
    rules: List[dict] = field(default_factory=list)  # [{"pattern": ..., "label": ..., "color": ...}]
    use_color: bool = True

    def build_rules(self) -> List[HighlightRule]:
        built: List[HighlightRule] = []
        for entry in self.rules:
            kwargs = {"pattern": entry["pattern"]}
            if "label" in entry:
                kwargs["label"] = entry["label"]
            if "color" in entry:
                kwargs["color_code"] = entry["color"]
            built.append(HighlightRule(**kwargs))
        return built


class HighlightIntegration:
    """Wraps RegexHighlighter and exposes a pipeline-compatible process method."""

    def __init__(
        self,
        highlighter: RegexHighlighter,
        on_match: Optional[Callable[[HighlightResult], None]] = None,
    ) -> None:
        self._highlighter = highlighter
        self._on_match = on_match
        self._total_processed: int = 0
        self._total_matched: int = 0

    @property
    def total_processed(self) -> int:
        return self._total_processed

    @property
    def total_matched(self) -> int:
        return self._total_matched

    def process(self, line: str) -> HighlightResult:
        result = self._highlighter.highlight(line)
        self._total_processed += 1
        if result.has_match:
            self._total_matched += 1
            if self._on_match is not None:
                self._on_match(result)
        return result

    def process_batch(self, lines: List[str]) -> List[HighlightResult]:
        return [self.process(line) for line in lines]

    @classmethod
    def from_config(cls, config: HighlightConfig, on_match: Optional[Callable[[HighlightResult], None]] = None) -> "HighlightIntegration":
        rules = config.build_rules()
        highlighter = RegexHighlighter(rules=rules, use_color=config.use_color)
        return cls(highlighter=highlighter, on_match=on_match)
