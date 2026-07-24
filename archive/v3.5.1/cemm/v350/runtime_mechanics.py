"""Mechanical v3.5.1 runtime services with no semantic-brain imports."""
from __future__ import annotations

from datetime import datetime, timezone


class SystemClock:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "clock"
    clock_ref = "clock:system-utc-v351"
    clock_revision = "1"

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()


__all__ = ["SystemClock"]
