from pydantic import BaseModel
from typing import Optional, Dict, Any
from enum import Enum

class SourceType(str, Enum):
    whatsapp = "whatsapp"
    slack = "slack"
    teams = "teams"
    gmail = "gmail"
    discord = "discord"
    generic = "generic"

class StreamEvent(BaseModel):
    source: SourceType
    stream_id: str              # conversation_id / channel_id / thread_id
    event_id: str               # message_id / email_id
    actor_id: str               # user_id / sender_id
    actor_name: Optional[str]
    timestamp: int
    content: str
    parent_event_id: Optional[str] = None
    raw_payload: Dict[str, Any]
