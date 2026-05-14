"""Rate-based log line sampler for reducing noise during high-volume bursts."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SamplerConfig:
    """Configuration for the log sampler."""

    max_rate: float  # lines per second above which sampling kicks in
    sample_fraction: float = 0.1  # fraction of lines to keep when over max_rate
    window_seconds: float = 5.0  # rolling window for rate estimation

    def __post_init__(self) -> None:
        if not (0.0 < self.sample_fraction <= 1.0):
            raise ValueError("sample_fraction must be in (0, 1]")
        if self.max_rate <= 0:
            raise ValueError("max_rate must be positive")
        if self.window_seconds <= 0:
            raise ValueError("window_seconds must be positive")


class LogSampler:
    """Decides whether a log line should be forwarded based on current rate.

    When the observed rate exceeds ``config.max_rate``, only a fraction of
    lines (``config.sample_fraction``) are passed through so that downstream
    components are not overwhelmed.
    """

    def __init__(self, config: SamplerConfig, clock=None) -> None:
        self._config = config
        self._clock = clock or time.monotonic
        self._timestamps: list[float] = []
        self._total_seen: int = 0
        self._total_passed: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def should_pass(self, line: str) -> bool:  # noqa: ARG002  (line reserved for future pattern-based sampling)
        """Return True if the line should be forwarded."""
        now = self._clock()
        self._record(now)
        rate = self._current_rate(now)

        if rate <= self._config.max_rate:
            self._total_passed += 1
            return True

        # Deterministic fractional sampling based on seen count
        threshold = self._config.sample_fraction
        bucket = (self._total_seen - 1) % round(1.0 / threshold)
        passes = bucket == 0
        if passes:
            self._total_passed += 1
        return passes

    @property
    def total_seen(self) -> int:
        return self._total_seen

    @property
    def total_passed(self) -> int:
        return self._total_passed

    def current_rate(self) -> float:
        """Return the current observed rate (lines/second)."""
        return self._current_rate(self._clock())

    def is_sampling(self) -> bool:
        """Return True when the sampler is actively dropping lines."""
        return self.current_rate() > self._config.max_rate

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record(self, now: float) -> None:
        self._total_seen += 1
        self._timestamps.append(now)
        self._evict(now)

    def _evict(self, now: float) -> None:
        cutoff = now - self._config.window_seconds
        while self._timestamps and self._timestamps[0] < cutoff:
            self._timestamps.pop(0)

    def _current_rate(self, now: float) -> float:
        self._evict(now)
        if not self._timestamps:
            return 0.0
        elapsed = self._config.window_seconds
        return len(self._timestamps) / elapsed
