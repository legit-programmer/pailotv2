import asyncio
import logging
import discord
import websockets

from gateway.utils import get_discord_channel
from models.events import Event, EventType
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
gateway = None


async def connect_to_gateway(uri, token=None):
    global gateway
    try:
        gateway = await websockets.connect(uri+f"?token={token}" if token else "")
        return gateway
    except ConnectionRefusedError:
        logger.error(f"Connection refused. Is the server running at {uri}?")
    except Exception as e:
        logger.error(f"An error occurred: {e}")


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
                if event.session_id:
                    channel = await get_discord_channel(event.session_id, event, client)
                    if event.event_type == EventType.AGENT_RESPONSE and event.data and channel:
                        print(f"Sending message to channel {channel.id}")
                        message_content = event.data.get("message")
                        if not message_content:
                            await Event.client_send(gateway, EventType.USER_MESSAGE, data={"message": "No message content or invalid format from your side, please resend the message."}, session_id=event.session_id)
                            continue
                        for i in range(0, len(message_content), 2000):
                            await channel.send(message_content[i:i+2000])
                    elif event.event_type == EventType.ERROR and event.data and channel:
                        await channel.send(f"Error:\n ```{event.data['message']}```")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Error receiving messages: {e}")
            await reset_gateway()
        finally:
            await asyncio.sleep(1)
