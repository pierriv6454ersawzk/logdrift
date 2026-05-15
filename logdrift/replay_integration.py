"""Wires ReplayReader into the standard pipeline as a LogSource."""

from __future__ import annotations

from typing import Callable, Iterator, Optional

from logdrift.log_source import LogSource
from logdrift.replay_reader import ReplayConfig, ReplayReader


class ReplaySource(LogSource):
    """A LogSource backed by a ReplayReader for historical log replay."""

    def __init__(self, reader: ReplayReader) -> None:
        self._reader = reader

    def lines(self) -> Iterator[str]:
        yield from self._reader.lines()

    def close(self) -> None:
        self._reader.stop()


class ReplayIntegration:
    """High-level helper to create a ReplaySource from a file path and config."""

    def __init__(
        self,
        path: str,
        config: Optional[ReplayConfig] = None,
        clock: Optional[Callable[[], float]] = None,
        sleep: Optional[Callable[[float], None]] = None,
    ) -> None:
        import time

        kwargs: dict = {"path": path, "config": config or ReplayConfig()}
        if clock is not None:
            kwargs["clock"] = clock
        if sleep is not None:
            kwargs["sleep"] = sleep

        self._reader = ReplayReader(**kwargs)
        self.source = ReplaySource(self._reader)

    @property
    def lines_emitted(self) -> int:
        return self._reader.lines_emitted

    def stop(self) -> None:
        self._reader.stop()

    @classmethod
    def from_config(
        cls,
        path: str,
        rate_multiplier: float = 1.0,
        max_lines: Optional[int] = None,
        loop: bool = False,
    ) -> "ReplayIntegration":
        config = ReplayConfig(
            rate_multiplier=rate_multiplier,
            max_lines=max_lines,
            loop=loop,
        )
        return cls(path=path, config=config)
