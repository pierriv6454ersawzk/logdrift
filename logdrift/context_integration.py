"""Integrates ContextWindow into the logdrift pipeline."""
from __future__ import annotations

from typing import Callable, List, Optional

from logdrift.context_window import ContextCapture, ContextWindow, ContextWindowConfig


TriggerFn = Callable[[str], bool]


class ContextIntegration:
    """Wraps ContextWindow for use in a pipeline step.

    Feed each raw log line through ``process``; it returns a list of
    ContextCapture objects that are ready to be forwarded downstream
    (e.g. to the formatter or an alert handler).
    """

    def __init__(
        self,
        trigger_fn: TriggerFn,
        config: Optional[ContextWindowConfig] = None,
    ) -> None:
        self._trigger_fn = trigger_fn
        self._window = ContextWindow(config)

    def process(self, line: str) -> List[ContextCapture]:
        """Feed *line* and return any completed captures."""
        is_trigger = self._trigger_fn(line)
        return self._window.feed(line, is_trigger=is_trigger)

    def flush(self) -> List[ContextCapture]:
        """Flush remaining incomplete captures (call at end-of-stream)."""
        return self._window.flush()

    @classmethod
    def from_config(
        cls,
        trigger_fn: TriggerFn,
        before: int = 2,
        after: int = 2,
    ) -> "ContextIntegration":
        """Convenience constructor accepting plain ints."""
        return cls(trigger_fn, ContextWindowConfig(before=before, after=after))


def format_capture(capture: ContextCapture, separator: str = "---") -> str:
    """Render a ContextCapture as a human-readable multi-line string."""
    parts: List[str] = []
    if capture.before:
        parts.extend(f"  {l}" for l in capture.before)
    parts.append(f">> {capture.trigger_line}")
    if capture.after:
        parts.extend(f"  {l}" for l in capture.after)
    parts.append(separator)
    return "\n".join(parts)
