from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional

class HoneypotEvent(BaseModel):
    timestamp: datetime
    source_ip: str
    event_type: str

    # optional flexible payload
    data: Optional[Dict[str, Any]] = None