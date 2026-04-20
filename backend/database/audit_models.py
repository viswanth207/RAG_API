from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class APIAuditLog(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    api_key: str
    endpoint: str
    method: str
    message_length: int
    response_length: Optional[int] = None
    status_code: int
    latency_ms: float
    metadata: Dict[str, Any] = {}
