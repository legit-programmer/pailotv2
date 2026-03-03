import asyncio

from fastapi import WebSocket
from gateway.utils import verify_token
from models.events import Event, EventType
from agent.agent import Agent, get_global_agent, loop as agent_loop


class ConnectionManager:
    def __init__(self, global_agent: Agent):
        self.active_connections: dict[str, WebSocket] = {}
        self.global_agent = global_agent
        self.active_loops = set()

    async def accept_and_authenticate_connection(self, websocket: WebSocket, token: str):
        await websocket.accept()
        is_authenticated = verify_token(token)
        if is_authenticated:
            self.active_connections[token] = websocket
            return await Event.send(websocket, EventType.AUTHENTICATED)
        await Event.send(websocket, EventType.UNAUTHORIZED, data={"message": "Invalid token"})
        return await websocket.close()

    async def receive_and_handle_events(self, websocket: WebSocket):
        try:
            data = await websocket.receive_json()
            event = Event(**data)
            if event.event_type == EventType.USER_MESSAGE and event.session_id and event.data:
                if event.session_id in self.active_loops:
                    return await Event.send(websocket, EventType.ERROR, data={"message": "An agent loop is already active for this session. Please wait until it finishes."}, session_id=event.session_id)

                self.active_loops.add(event.session_id)
                try:
                    result = await agent_loop(event.data["message"], session_id=event.session_id)
                    await Event.send(websocket, EventType.AGENT_RESPONSE, data={'message': result}, session_id=event.session_id)
                finally:
                    print(f"Loop for session {event.session_id} finished. Cleaning up.")
                    self.active_loops.discard(event.session_id)
                # implement a queue system if you want to handle multiple messages in the same session while a loop is active. For now, we just discard new messages until the current loop is done.
        except Exception as e:
            await Event.send(websocket, EventType.ERROR, data={"message": str(e)})
