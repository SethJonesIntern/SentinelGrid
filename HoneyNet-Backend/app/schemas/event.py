from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional

class HoneypotEvent(BaseModel):
    timestamp: datetime
    source_ip: str
    event_type: str

    # optional fields sent by sensor
    session_id: Optional[str] = None
    sensor_id: Optional[str] = None

    # Honeypot type this event came from (e.g. "ssh", "http"). The forwarder
    # sends it; if absent we fall back to the event_type prefix. See
    # normalize_event.resolve_honeypot_type.
    honeypot_type: Optional[str] = None

    # optional flexible payload
    data: Optional[Dict[str, Any]] = None