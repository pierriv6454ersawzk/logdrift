"""Formatting utilities for log output with anomaly highlighting."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from logdrift.anomaly_detector import AnomalyResult


class Color(str, Enum):
    RESET = "\033[0m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"
    BOLD = "\033[1m"
    DIM = "\033[2m"


@dataclass
class FormatOptions:
    color: bool = True
    show_rate: bool = True
    show_anomaly_score: bool = False


class LogFormatter:
    """Formats log lines for terminal output, highlighting anomalies."""

    def __init__(self, options: Optional[FormatOptions] = None) -> None:
        self.options = options or FormatOptions()

    def format_line(
        self,
        line: str,
        anomaly: Optional[AnomalyResult] = None,
        current_rate: float = 0.0,
    ) -> str:
        """Return a formatted string for terminal display."""
        parts: list[str] = []

        if anomaly and anomaly.is_anomaly:
            parts.append(self._colorize(Color.RED, Color.BOLD, "[ANOMALY] "))
        elif anomaly and anomaly.score > 0.5:
            parts.append(self._colorize(Color.YELLOW, None, "[SPIKE]   "))
        else:
            parts.append(self._colorize(Color.DIM, None, "[OK]      "))

        if self.options.show_rate:
            rate_str = f"{current_rate:6.1f}/s "
            parts.append(self._colorize(Color.CYAN, None, rate_str))

        if self.options.show_anomaly_score and anomaly is not None:
            parts.append(self._colorize(Color.DIM, None, f"(score={anomaly.score:.2f}) "))

        parts.append(line)
        return "".join(parts)

    def _colorize(self, color: Color, modifier: Optional[Color], text: str) -> str:
        if not self.options.color:
            return text
        prefix = modifier.value + color.value if modifier else color.value
        return f"{prefix}{text}{Color.RESET.value}"

    def format_summary(self, total_lines: int, anomaly_count: int, elapsed: float) -> str:
        """Return a summary line shown when tailing stops."""
        rate = total_lines / elapsed if elapsed > 0 else 0.0
        summary = (
            f"\n--- logdrift summary ---\n"
            f"  lines processed : {total_lines}\n"
            f"  anomalies found : {anomaly_count}\n"
            f"  avg rate        : {rate:.1f}/s\n"
            f"  elapsed         : {elapsed:.1f}s\n"
        )
        if self.options.color:
            return f"{Color.BOLD.value}{summary}{Color.RESET.value}"
        return summary
