"""Integration layer that combines LabelClassifier with pipeline events."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from logdrift.label_classifier import (
    ClassificationResult,
    ClassifierConfig,
    LabelClassifier,
    Severity,
)


@dataclass
class ClassifierIntegration:
    """Wraps LabelClassifier and tracks classification statistics."""

    _classifier: LabelClassifier
    _callbacks: List[Callable[[ClassificationResult], None]] = field(
        default_factory=list, init=False
    )
    _total_processed: int = field(default=0, init=False)
    _severity_counts: dict = field(default_factory=dict, init=False)

    def __init__(self, config: ClassifierConfig) -> None:
        self._classifier = LabelClassifier(config)
        self._callbacks = []
        self._total_processed = 0
        self._severity_counts = {s.value: 0 for s in Severity}

    def add_callback(self, cb: Callable[[ClassificationResult], None]) -> None:
        """Register a callback invoked for every classification result."""
        self._callbacks.append(cb)

    def process(self, line: str) -> ClassificationResult:
        """Classify a single log line and update counters."""
        result = self._classifier.classify(line)
        self._total_processed += 1
        self._severity_counts[result.severity.value] += 1
        for cb in self._callbacks:
            cb(result)
        return result

    def process_batch(self, lines: List[str]) -> List[ClassificationResult]:
        """Classify multiple lines and return all results."""
        return [self.process(line) for line in lines]

    @property
    def total_processed(self) -> int:
        return self._total_processed

    def severity_count(self, severity: Severity) -> int:
        """Return how many lines were classified at the given severity."""
        return self._severity_counts.get(severity.value, 0)

    @classmethod
    def from_config(cls, config: Optional[ClassifierConfig] = None) -> "ClassifierIntegration":
        """Create an integration with a default or provided config."""
        return cls(config or ClassifierConfig())
