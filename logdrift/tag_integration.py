"""Integration layer: wire TagEnricher into the log processing pipeline."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from logdrift.tag_enricher import EnrichmentResult, TagEnricher, TagEnricherConfig, TagRule


class TagIntegration:
    """Wraps TagEnricher and exposes a process() method compatible with the pipeline."""

    def __init__(self, enricher: TagEnricher) -> None:
        self._enricher = enricher
        self._callbacks: List[Callable[[EnrichmentResult], None]] = []
        self._total_enriched = 0
        self._total_tagged = 0

    def add_callback(self, cb: Callable[[EnrichmentResult], None]) -> None:
        """Register a callback invoked for every enriched line that carries tags."""
        self._callbacks.append(cb)

    def process(self, line: str) -> EnrichmentResult:
        result = self._enricher.enrich(line)
        self._total_enriched += 1
        if result.has_tags:
            self._total_tagged += 1
            for cb in self._callbacks:
                cb(result)
        return result

    def process_batch(self, lines: List[str]) -> List[EnrichmentResult]:
        return [self.process(line) for line in lines]

    @property
    def total_enriched(self) -> int:
        return self._total_enriched

    @property
    def total_tagged(self) -> int:
        return self._total_tagged

    @classmethod
    def from_config(
        cls,
        rules: Optional[List[Dict]] = None,
        merge_strategy: str = "last_wins",
    ) -> "TagIntegration":
        tag_rules = [
            TagRule(pattern=r["pattern"], tags=r.get("tags", {}))
            for r in (rules or [])
        ]
        config = TagEnricherConfig(rules=tag_rules, merge_strategy=merge_strategy)
        return cls(TagEnricher(config))
