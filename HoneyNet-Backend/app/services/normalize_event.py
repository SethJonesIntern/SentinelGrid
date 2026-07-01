# app/services/normalize_event.py

from typing import Dict, Any, Optional
from app.schemas.event import HoneypotEvent
from app.services.ml_model import HONEYPOT_TYPES
import hashlib


def resolve_honeypot_type(event: HoneypotEvent) -> Optional[str]:
    """
    Determine which honeypot type an event belongs to (e.g. "ssh", "http").

    Prefers the explicit ``honeypot_type`` the forwarder sends; otherwise falls
    back to the prefix of ``event_type`` (events are named "<type>.<...>", e.g.
    "http.login.attempt"). Returns the type only if it's one we track, else
    None — so callers don't store a count against an unknown/garbage key.
    """
    candidate = event.honeypot_type or event.event_type.split(".")[0]
    candidate = candidate.strip().lower()
    return candidate if candidate in HONEYPOT_TYPES else None


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