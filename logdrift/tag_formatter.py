"""Formatting helpers that render EnrichmentResult tags alongside log output."""

from __future__ import annotations

from typing import List, Optional

from logdrift.tag_enricher import EnrichmentResult


_RESET = "\033[0m"
_CYAN = "\033[36m"
_BOLD = "\033[1m"


class TagFormatter:
    """Renders tag metadata appended to a log line string."""

    def __init__(self, color: bool = True, separator: str = " | ") -> None:
        self._color = color
        self._separator = separator

    def format_tags(self, tags: dict) -> str:
        if not tags:
            return ""
        parts = [f"{k}={v}" for k, v in sorted(tags.items())]
        tag_str = " ".join(parts)
        if self._color:
            return f"{_CYAN}[{tag_str}]{_RESET}"
        return f"[{tag_str}]"

    def format_result(self, result: EnrichmentResult) -> str:
        tag_part = self.format_tags(result.tags)
        if not tag_part:
            return result.line
        return f"{result.line}{self._separator}{tag_part}"

    def format_batch(self, results: List[EnrichmentResult]) -> List[str]:
        return [self.format_result(r) for r in results]


class TagSummaryFormatter:
    """Produces a human-readable summary of tag frequencies across many results."""

    def summarize(self, results: List[EnrichmentResult]) -> str:
        counts: dict = {}
        for result in results:
            for k, v in result.tags.items():
                key = f"{k}={v}"
                counts[key] = counts.get(key, 0) + 1

        if not counts:
            return "No tags observed."

        lines = ["Tag summary:"]
        for tag, count in sorted(counts.items(), key=lambda x: -x[1]):
            lines.append(f"  {tag}: {count}")
        return "\n".join(lines)
