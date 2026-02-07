from pydantic import BaseModel, Field
from typing import List, Optional, Any
from datetime import datetime

class LogEntry(BaseModel):
    id: str
    timestamp: datetime
    resource: Optional[str] = None
    action: Optional[str] = None
    userId: Optional[str] = None
    role: Optional[str] = None
    workspaceId: Optional[str] = None
    metadata: Optional[str] = None

class LogRetrieveResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    logs: List[LogEntry] = []
    count: int
    totalCount: int

class LogSuggestion(BaseModel):
    type: str = Field(..., description="Type of suggestion: 'proposal' (requires accept/reject) or 'message' (informational).")
    id: Optional[str] = None
    title: Optional[str] = None
    message: str
    workspaceId: Optional[str] = None
    role: Optional[str] = None


