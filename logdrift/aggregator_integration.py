from __future__ import annotations

from typing import Callable, List, Optional

from logdrift.log_aggregator import AggregationBucket, AggregationConfig, LogAggregator


class AggregatorIntegration:
    """Wires LogAggregator into the pipeline with optional top-N reporting."""

    def __init__(
        self,
        config: AggregationConfig,
        key_fn: Callable[[str], str],
        clock: Optional[Callable[[], float]] = None,
    ) -> None:
        kwargs = {"config": config, "key_fn": key_fn}
        if clock is not None:
            kwargs["clock"] = clock
        self._aggregator = LogAggregator(**kwargs)
        self._total_processed: int = 0
        self._callbacks: List[Callable[[AggregationBucket], None]] = []

    def add_callback(self, cb: Callable[[AggregationBucket], None]) -> None:
        self._callbacks.append(cb)
        self._aggregator.add_callback(cb)

    def process(self, line: str) -> AggregationBucket:
        self._total_processed += 1
        return self._aggregator.record(line)

    def process_batch(self, lines: List[str]) -> List[AggregationBucket]:
        return [self.process(line) for line in lines]

    def top(self, n: int = 10) -> List[AggregationBucket]:
        """Return the top-N buckets by count within the current window."""
        return self._aggregator.snapshot()[:n]

    @property
    def total_processed(self) -> int:
        return self._total_processed

    @property
    def total_keys(self) -> int:
        return self._aggregator.total_keys

    @classmethod
    def from_config(
        cls,
        window_seconds: float = 60.0,
        max_buckets: int = 100,
        key_fn: Optional[Callable[[str], str]] = None,
    ) -> "AggregatorIntegration":
        config = AggregationConfig(window_seconds=window_seconds, max_buckets=max_buckets)
        if key_fn is None:
            key_fn = lambda line: line.split()[0] if line.split() else line
        return cls(config=config, key_fn=key_fn)
