"""Output sinks for writing formatted log lines to various destinations."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from typing import TextIO


class OutputSink(ABC):
    """Abstract base class for output destinations."""

    @abstractmethod
    def write(self, line: str) -> None:
        """Write a formatted line to the sink."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Release any resources held by the sink."""
        ...


class StreamSink(OutputSink):
    """Writes lines to a text stream (e.g. stdout or stderr)."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream: TextIO = stream if stream is not None else sys.stdout

    def write(self, line: str) -> None:
        self._stream.write(line + "\n")
        self._stream.flush()

    def close(self) -> None:
        # We do not close streams we did not open (e.g. stdout).
        pass


class FileSink(OutputSink):
    """Appends formatted lines to a file on disk."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._file: TextIO = open(path, "a", encoding="utf-8")  # noqa: WPS515

    def write(self, line: str) -> None:
        self._file.write(line + "\n")
        self._file.flush()

    def close(self) -> None:
        if not self._file.closed:
            self._file.close()


class MultiSink(OutputSink):
    """Fan-out sink that writes to multiple sinks simultaneously."""

    def __init__(self, *sinks: OutputSink) -> None:
        self._sinks = list(sinks)

    def write(self, line: str) -> None:
        for sink in self._sinks:
            sink.write(line)

    def close(self) -> None:
        for sink in self._sinks:
            sink.close()
