"""Replay a historical log file through the pipeline at a controlled rate."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Iterator, Optional


@dataclass
class ReplayConfig:
    """Configuration for log replay behaviour."""

    rate_multiplier: float = 1.0  # 1.0 = real-time, 2.0 = double speed, 0 = no delay
    max_lines: Optional[int] = None  # None means unlimited
    loop: bool = False  # restart from the beginning when EOF is reached

    def __post_init__(self) -> None:
        if self.rate_multiplier < 0:
            raise ValueError("rate_multiplier must be >= 0")
        if self.max_lines is not None and self.max_lines < 1:
            raise ValueError("max_lines must be >= 1 when set")


class ReplayReader:
    """Reads lines from a file and replays them with optional timing control."""

    def __init__(
        self,
        path: str,
        config: Optional[ReplayConfig] = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._path = path
        self._config = config or ReplayConfig()
        self._clock = clock
        self._sleep = sleep
        self._lines_emitted: int = 0
        self._stopped: bool = False

    @property
    def lines_emitted(self) -> int:
        return self._lines_emitted

    def stop(self) -> None:
        self._stopped = True

    def lines(self) -> Iterator[str]:
        """Yield lines from the file, respecting rate and loop settings."""
        while not self._stopped:
            yield from self._read_file_once()
            if not self._config.loop or self._stopped:
                break

    def _read_file_once(self) -> Iterator[str]:
        prev_time: Optional[float] = None

        with open(self._path, "r", encoding="utf-8") as fh:
            for raw_line in fh:
                if self._stopped:
                    return
                if (
                    self._config.max_lines is not None
                    and self._lines_emitted >= self._config.max_lines
                ):
                    self._stopped = True
                    return

                line = raw_line.rstrip("\n")
                now = self._clock()

                if prev_time is not None and self._config.rate_multiplier > 0:
                    delay = (now - prev_time) / self._config.rate_multiplier
                    if delay > 0:
                        self._sleep(delay)

                prev_time = self._clock()
                self._lines_emitted += 1
                yield line
