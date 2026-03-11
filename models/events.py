from fastapi import WebSocket
from pydantic import BaseModel
from enum import Enum

from websockets import ClientConnection

class EventType(str, Enum):
    USER_MESSAGE = "user_message"
    AGENT_RESPONSE = "agent_response"
    CREATE_SESSION = "create_session"
    DESTROY_SESSION = "destroy_session"
    UNAUTHORIZED = "unauthorized"
    ERROR = "error"
    AUTHENTICATED = "authenticated"
    CHANGE_MODEL = "change_model"
    RESET_SESSION = "reset_session"

class Event(BaseModel):
    event_type: EventType
    session_id: str | None = None
    data: dict | None = None

    @classmethod
    async def send(cls, websocket: WebSocket, event_type: EventType, session_id: str | None = None, data: dict | None = None):
        event = cls(event_type=event_type, session_id=session_id, data=data)
        await websocket.send_text(event.model_dump_json())
        return event
    
    @classmethod
    async def client_send(cls, websocket: ClientConnection, event_type: EventType, session_id: str | None = None, data: dict | None = None):
        event = cls(event_type=event_type, session_id=session_id, data=data)
        await websocket.send(event.model_dump_json())
        return event