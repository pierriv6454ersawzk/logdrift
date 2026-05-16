"""Human-readable reporting for heartbeat silence events."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from logdrift.heartbeat_integration import HeartbeatIntegration


@dataclass
class SilenceEvent:
    silence_duration_seconds: float
    detected_at: float
    resumed: bool = False
    resumed_at: Optional[float] = None

    def summary(self) -> str:
        status = "RESUMED" if self.resumed else "ONGOING"
        return (
            f"[HEARTBEAT] silence={self.silence_duration_seconds:.1f}s "
            f"detected_at={self.detected_at:.1f} status={status}"
        )


class HeartbeatReporter:
    """Listens to a HeartbeatIntegration and collects SilenceEvents."""

    def __init__(
        self,
        integration: HeartbeatIntegration,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._integration = integration
        self._clock = clock
        self._events: List[SilenceEvent] = []
        self._current: Optional[SilenceEvent] = None

        integration.add_on_silence(self._on_silence)
        integration.add_on_resume(self._on_resume)

    def _on_silence(self, duration: float) -> None:
        evt = SilenceEvent(
            silence_duration_seconds=duration,
            detected_at=self._clock(),
        )
        self._current = evt
        self._events.append(evt)

    def _on_resume(self, _now: float) -> None:
        if self._current is not None:
            self._current.resumed = True
            self._current.resumed_at = self._clock()
            self._current = None

    @property
    def events(self) -> List[SilenceEvent]:
        return list(self._events)

    @property
    def total_silences(self) -> int:
        return len(self._events)

    def latest_summary(self) -> Optional[str]:
        if not self._events:
            return None
        return self._events[-1].summary()
