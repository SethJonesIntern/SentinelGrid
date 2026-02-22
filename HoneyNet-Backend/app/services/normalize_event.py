# app/services/normalize_event.py

from typing import Dict, Any
from app.schemas.event import HoneypotEvent
import hashlib


def generate_session_id(src_ip: str, event_type: str, timestamp) -> str:
    """
    Generates a deterministic session ID based on attacker + service + time window.
    """
    # Bucket into 1-hour windows so long attacks group together
    time_bucket = timestamp.strftime("%Y%m%d%H")

    base_string = f"{src_ip}:{event_type}:{time_bucket}"

    return hashlib.sha256(base_string.encode()).hexdigest()


def normalize_event_dict(event: HoneypotEvent) -> Dict[str, Any]:
    """
    Normalizes an incoming HoneypotEvent into a canonical JSON structure
    for consistent database storage.
    """

    # Ensure payload is always a dictionary
    payload = event.data or {}

    # Use provided session_id or generate one
    session_id = event.session_id or generate_session_id(
        src_ip=event.source_ip,
        event_type=event.event_type,
        timestamp=event.timestamp
    )

    return {
        # Canonical timestamp format
        "timestamp": event.timestamp.isoformat(),

        # Standardized naming
        "src_ip": event.source_ip,

        # Clean event type formatting
        "event_type": event.event_type.strip().lower(),

        # Sensor metadata (if provided)
        "sensor_id": event.sensor_id,

        # Session grouping
        "session_id": session_id,

        # Event-specific details
        "payload": payload,
    }