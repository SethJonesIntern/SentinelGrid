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

    # optional flexible payload
    data: Optional[Dict[str, Any]] = None