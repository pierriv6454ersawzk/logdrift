"""Extracts structured key=value fields from log lines."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_KV_PATTERN = re.compile(r'(\w[\w.\-]*)=("[^"]*"|\S+)')


@dataclass
class ExtractionResult:
    line: str
    fields: Dict[str, str] = field(default_factory=dict)

    @property
    def has_fields(self) -> bool:
        return bool(self.fields)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return self.fields.get(key, default)


@dataclass
class FieldExtractorConfig:
    keys: Optional[List[str]] = None  # None means accept all keys

    def __post_init__(self) -> None:
        if self.keys is not None and not isinstance(self.keys, list):
            raise TypeError("keys must be a list or None")


class FieldExtractor:
    """Parses key=value pairs from a log line."""

    def __init__(self, config: Optional[FieldExtractorConfig] = None) -> None:
        self._config = config or FieldExtractorConfig()
        self._total_processed: int = 0
        self._total_matched: int = 0

    @property
    def total_processed(self) -> int:
        return self._total_processed

    @property
    def total_matched(self) -> int:
        return self._total_matched

    def extract(self, line: str) -> ExtractionResult:
        self._total_processed += 1
        raw: Dict[str, str] = {}
        for m in _KV_PATTERN.finditer(line):
            key = m.group(1)
            value = m.group(2).strip('"')
            if self._config.keys is None or key in self._config.keys:
                raw[key] = value
        if raw:
            self._total_matched += 1
        return ExtractionResult(line=line, fields=raw)

    def extract_batch(self, lines: List[str]) -> List[ExtractionResult]:
        return [self.extract(line) for line in lines]
