import asyncio
from fastapi import WebSocket
from gateway.utils import verify_token
from models.events import Event, EventType
from agent.agent import Agent, get_global_agent, loop as agent_loop


class ConnectionManager:
    def __init__(self, global_agent: Agent):
        self.active_connections: dict[str, WebSocket] = {}
        self.global_agent = global_agent

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
            agent = await get_global_agent()
            if event.event_type == EventType.USER_MESSAGE and event.session_id and event.data:

                try:
                    sm = agent.session_manager
                    if not sm.is_loop_active(event.session_id):
                        sm.active_loops.add(event.session_id)
                    else:
                        sm.add_steering_message(event.session_id, event.data["message"])
                        return await Event.send(websocket, EventType.AGENT_RESPONSE, data={"message": "Message steered."}, session_id=event.session_id)
                    
                    loop_task = asyncio.create_task(agent_loop(
                        event.data["message"], session_id=event.session_id))

                    async def done_callback(task: asyncio.Task):
                        sm.active_loops.discard(event.session_id)
                        await Event.send(websocket, EventType.AGENT_RESPONSE, data={'message': task.result()}, session_id=event.session_id)

                    def callback_wrapper(task: asyncio.Task):
                        asyncio.create_task(done_callback(task))

                    loop_task.add_done_callback(callback_wrapper)
                except Exception as e:
                    await Event.send(websocket, EventType.ERROR, data={"message": f"An error occurred while processing your message: {e}"}, session_id=event.session_id)
            elif event.event_type == EventType.CHANGE_MODEL and event.session_id and event.data:
                new_model = event.data.get("model")
                if new_model:
                    try:
                        agent.session_manager.update_session_model(
                            event.session_id, new_model)
                        await Event.send(websocket, EventType.AGENT_RESPONSE, data={"message": f"Model for session {event.session_id} updated to {new_model}"}, session_id=event.session_id)
                    except ValueError as e:
                        await Event.send(websocket, EventType.ERROR, data={"message": str(e)}, session_id=event.session_id)
                else:
                    await Event.send(websocket, EventType.ERROR, data={"message": "No model specified in change model event"}, session_id=event.session_id)
            elif event.event_type == EventType.RESET_SESSION and event.session_id:
                try:
                    agent.session_manager.delete_session(event.session_id)
                    await Event.send(websocket, EventType.AGENT_RESPONSE, data={"message": f"Session {event.session_id} has been reset successfully."}, session_id=event.session_id)
                except Exception as e:
                    await Event.send(websocket, EventType.ERROR, data={"message": f"Failed to reset session: {e}"}, session_id=event.session_id)
        except Exception as e:
            raise e
