"""Integration layer that wires FieldExtractor into the processing pipeline."""
from __future__ import annotations

from typing import Callable, List, Optional

from logdrift.field_extractor import (
    ExtractionResult,
    FieldExtractor,
    FieldExtractorConfig,
)


class FieldIntegration:
    """Processes lines through FieldExtractor and dispatches results."""

    def __init__(self, extractor: Optional[FieldExtractor] = None) -> None:
        self._extractor = extractor or FieldExtractor()
        self._callbacks: List[Callable[[ExtractionResult], None]] = []

    def add_callback(self, cb: Callable[[ExtractionResult], None]) -> None:
        """Register a callback that receives each ExtractionResult."""
        self._callbacks.append(cb)

    def process(self, line: str) -> ExtractionResult:
        result = self._extractor.extract(line)
        for cb in self._callbacks:
            cb(result)
        return result

    def process_batch(self, lines: List[str]) -> List[ExtractionResult]:
        return [self.process(line) for line in lines]

    @property
    def total_processed(self) -> int:
        return self._extractor.total_processed

    @property
    def total_matched(self) -> int:
        return self._extractor.total_matched

    @classmethod
    def from_config(cls, config: FieldExtractorConfig) -> "FieldIntegration":
        return cls(extractor=FieldExtractor(config=config))
