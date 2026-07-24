"""Small final-ABI runtime support services."""
from __future__ import annotations

from datetime import datetime, timezone


class SystemUTCClockV351:
    RUNTIME_ABI = "v351"
    SERVICE_KIND = "clock"

    def now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()


__all__ = ["SystemUTCClockV351"]
