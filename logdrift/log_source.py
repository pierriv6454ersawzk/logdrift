"""Log source abstractions for reading from local files or stdin."""

import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterator, Optional


class LogSource(ABC):
    """Abstract base class for log sources."""

    @abstractmethod
    def lines(self) -> Iterator[str]:
        """Yield log lines one at a time."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Release any resources held by this source."""
        ...


class FileLogSource(LogSource):
    """Tail a local file, yielding new lines as they are written."""

    def __init__(self, path: str, poll_interval: float = 0.1, encoding: str = "utf-8") -> None:
        self.path = Path(path)
        self.poll_interval = poll_interval
        self.encoding = encoding
        self._file = open(self.path, "r", encoding=self.encoding)  # noqa: WPS515
        self._file.seek(0, 2)  # seek to end
        self._closed = False

    def lines(self) -> Iterator[str]:
        """Yield lines appended to the file, blocking between polls."""
        while not self._closed:
            line = self._file.readline()
            if line:
                yield line.rstrip("\n")
            else:
                time.sleep(self.poll_interval)

    def close(self) -> None:
        self._closed = True
        self._file.close()


class StdinLogSource(LogSource):
    """Read log lines from standard input."""

    def __init__(self) -> None:
        self._closed = False

    def lines(self) -> Iterator[str]:
        """Yield lines from stdin until EOF or close."""
        for line in sys.stdin:
            if self._closed:
                break
            yield line.rstrip("\n")

    def close(self) -> None:
        self._closed = True


def open_source(path: Optional[str] = None, **kwargs) -> LogSource:
    """Factory: return a FileLogSource for *path* or StdinLogSource for stdin."""
    if path is None or path == "-":
        return StdinLogSource()
    return FileLogSource(path, **kwargs)
