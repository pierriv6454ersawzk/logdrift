from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class AggregationConfig:
    window_seconds: float = 60.0
    max_buckets: int = 100

    def __post_init__(self) -> None:
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if self.max_buckets < 1:
            raise ValueError("max_buckets must be at least 1")


@dataclass
class AggregationBucket:
    key: str
    count: int = 0
    first_seen: float = 0.0
    last_seen: float = 0.0

    def to_dict(self) -> dict:
        return {
            "key": self.key,
            "count": self.count,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
        }


class LogAggregator:
    """Aggregates log lines by a key function within a rolling time window."""

    def __init__(
        self,
        config: AggregationConfig,
        key_fn: Callable[[str], str],
        clock: Callable[[], float] = __import__("time").monotonic,
    ) -> None:
        self._config = config
        self._key_fn = key_fn
        self._clock = clock
        self._buckets: Dict[str, AggregationBucket] = {}
        self._callbacks: List[Callable[[AggregationBucket], None]] = []

    def add_callback(self, cb: Callable[[AggregationBucket], None]) -> None:
        self._callbacks.append(cb)

    def record(self, line: str) -> AggregationBucket:
        now = self._clock()
        self._evict(now)
        key = self._key_fn(line)
        if key not in self._buckets:
            if len(self._buckets) >= self._config.max_buckets:
                self._drop_oldest()
            self._buckets[key] = AggregationBucket(key=key, count=0, first_seen=now, last_seen=now)
        bucket = self._buckets[key]
        bucket.count += 1
        bucket.last_seen = now
        for cb in self._callbacks:
            cb(bucket)
        return bucket

    def snapshot(self) -> List[AggregationBucket]:
        now = self._clock()
        self._evict(now)
        return sorted(self._buckets.values(), key=lambda b: b.count, reverse=True)

    def _evict(self, now: float) -> None:
        cutoff = now - self._config.window_seconds
        expired = [k for k, b in self._buckets.items() if b.last_seen < cutoff]
        for k in expired:
            del self._buckets[k]

    def _drop_oldest(self) -> None:
        if not self._buckets:
            return
        oldest_key = min(self._buckets, key=lambda k: self._buckets[k].last_seen)
        del self._buckets[oldest_key]

    @property
    def total_keys(self) -> int:
        return len(self._buckets)
