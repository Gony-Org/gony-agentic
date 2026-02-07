from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import uuid4

class ChatRole(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"

class ChatMessage(BaseModel):
    role: ChatRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatHistory(BaseModel):
    session_id: str
    messages: List[ChatMessage]

class AgentRequest(BaseModel):
    user_id: str
    workspace_id: Optional[str] = None
    role: Optional[str] = None
    query: str
    session_id: Optional[str] = None # Optional, if not provided, a new one is created

class AgentResponse(BaseModel):
    status: str
    message: str
    session_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ChatSession(BaseModel):
    session_id: str
    session_name: Optional[str] = None
    updated_at: datetime

class ChatHistoryResponse(BaseModel):
    sessions: List[ChatSession]
