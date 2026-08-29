"""
File: backend/app/api/v1/stats.py
Description:
    API Routes for Real-Time Dashboard Telemetry & System Analytics (Role 6).
    - Ring buffer for live telemetry event streaming to the dashboard.
    - Captures ElevenLabs phone call tool invocations, KRA PIN lookups, OSCU signings,
      and WhatsApp receipts in real-time.
"""

from collections import deque
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Telemetry & Stats"])

# Thread-safe in-memory ring buffer for last 200 telemetry events
_TELEMETRY_LOGS: deque = deque(maxlen=200)


class TelemetryEvent(BaseModel):
    id: str
    timestamp: str
    node: str
    message: str
    level: str = "info"


def record_telemetry_event(node: str, message: str, level: str = "info") -> None:
    """Record an event into the live telemetry stream."""
    now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
    event_id = f"log-{int(datetime.now(timezone.utc).timestamp() * 1000)}"
    _TELEMETRY_LOGS.append({
        "id": event_id,
        "timestamp": now_str,
        "node": node.upper(),
        "message": message,
        "level": level,
    })


@router.get("/telemetry", response_model=List[TelemetryEvent])
def get_live_telemetry_stream(limit: int = 50):
    """
    Fetch the latest live telemetry events for the dashboard terminal.
    """
    logs_list = list(_TELEMETRY_LOGS)
    return logs_list[-limit:]


@router.delete("/telemetry")
def clear_telemetry_logs():
    """Clear all telemetry logs for a fresh live demo run."""
    _TELEMETRY_LOGS.clear()
    record_telemetry_event("SYSTEM", "Live telemetry stream connected. Speak into microphone...", "success")
    return {"ok": True, "message": "Telemetry logs cleared"}
