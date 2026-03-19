import asyncio
from fastapi import WebSocket
from gateway.utils import verify_token
from models.events import Event, EventType
from agent.agent import Agent, get_global_agent, loop as agent_loop
from models.model_tools import Tool, ToolArgument, add_tool


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        add_tool(
            Tool(
                name="send_message_to_channel",
                description="Sends a message to the user through the websocket connection. Use this to send any messages that should be seen by the user, including intermediate thoughts, final answers, or error messages. The session_id should be used to ensure the message is sent to the correct user session.",
                args=[
                    ToolArgument(name="session_id", type="string", description="The ID of the user session or channel to which the message should be sent."),
                    ToolArgument(name="message", type="string", description="The message content to send to the user.")
                ],
                function=self.send_message_to_channel
            )
        )
        add_tool(
            Tool(
                name="list_active_connections",
                description="Returns a list of all currently active connection tokens.",
                function=self.list_active_connections
            )
        )
        add_tool(
            Tool(
                name="broadcast_message",
                description="Sends a message to all currently active websocket connections.",
                args=[
                    ToolArgument(name="message", type="string", description="The message content to broadcast.")
                ],
                function=self.broadcast_message
            )
        )
        add_tool(
            Tool(
                name="disconnect_connection",
                description="Forcefully closes the websocket connection for a specific token.",
                args=[
                    ToolArgument(name="token", type="string", description="The connection token to disconnect."),
                    ToolArgument(name="reason", type="string", description="Optional reason for disconnection.")
                ],
                function=self.disconnect_connection
            )
        )
        add_tool(
            Tool(
                name="get_connection_info",
                description="Retrieves metadata about a specific connection.",
                args=[
                    ToolArgument(name="token", type="string", description="The connection token.")
                ],
                function=self.get_connection_info
            )
        )

    async def accept_and_authenticate_connection(self, websocket: WebSocket, token: str):
        await websocket.accept()
        is_authenticated = verify_token(token)
        if is_authenticated:
            self.active_connections[token] = websocket
            return await Event.send(websocket, EventType.AUTHENTICATED)
        await Event.send(websocket, EventType.UNAUTHORIZED, data={"message": "Invalid token"})
        return await websocket.close()
    
    async def send_message_to_channel(self, session_id: str, message: str):
        for token, websocket in self.active_connections.items():
            try:
                await Event.send(websocket, EventType.AGENT_RESPONSE, session_id=session_id, data={"message": message})
            except Exception as e:
                print(f"Error sending message to connection {token}: {e}")

    async def list_active_connections(self) -> list[str]:
        return list(self.active_connections.keys())

    async def broadcast_message(self, message: str):
        agent = await get_global_agent()
        session_ids = agent.session_manager.get_all_session_ids()
        for session_id in session_ids:
            await self.send_message_to_channel(session_id, message)

    async def disconnect_connection(self, token: str, reason: str = ""):
        if token in self.active_connections:
            websocket = self.active_connections[token]
            try:
                await Event.send(websocket, EventType.ERROR, session_id="system", data={"message": f"Disconnected by agent. Reason: {reason}"})
                await websocket.close()
            except Exception as e:
                print(f"Error closing connection {token}: {e}")
            finally:
                del self.active_connections[token]
            return f"Successfully disconnected {token}."
        return f"Connection {token} not found."

    async def get_connection_info(self, token: str) -> dict:
        if token in self.active_connections:
            websocket = self.active_connections[token]
            return {
                "token": token,
                "client": f"{websocket.client.host}:{websocket.client.port}" if websocket.client else "Unknown"
            }
        return {"error": f"Connection {token} not found."}

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
