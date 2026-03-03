import asyncio
import discord
import websockets

from models.events import Event, EventType


gateway = None


async def connect_to_gateway(uri, token=None):
    global gateway
    try:
        gateway = await websockets.connect(uri+f"?token={token}" if token else "")
        return gateway
    except ConnectionRefusedError:
        print(f"Connection refused. Is the server running at {uri}?")
    except Exception as e:
        print(f"An error occurred: {e}")


async def get_gateway():
    if gateway is None:
        await connect_to_gateway("ws://localhost:8000/gateway/ws", token="valid_token")
    return gateway


async def reset_gateway():
    global gateway
    if gateway:
        await gateway.close()
    gateway = None


async def receive_msgs(client: discord.Client):
    while True:
        gateway = await get_gateway()

        if gateway is None:
            await asyncio.sleep(1)
            continue

        try:
            async for message in gateway:
                event = Event.model_validate_json(message)
                if event.event_type == EventType.AGENT_RESPONSE and event.session_id and event.data:
                    try:
                        channel_id = int(event.session_id)
                    except (TypeError, ValueError):
                        print(
                            f"Invalid session/channel id: {event.session_id}")
                        continue

                    channel = client.get_channel(channel_id)
                    if channel is None:
                        try:
                            channel = await client.fetch_channel(channel_id)
                        except Exception as fetch_error:
                            print(
                                f"Unable to resolve channel {channel_id}: {fetch_error}")
                            continue

                    await channel.send(event.data["message"])

        except asyncio.CancelledError:
            raise
        except Exception as e:
            print(f"Error receiving messages: {e}")
            await reset_gateway()
        finally:
            await asyncio.sleep(1)
