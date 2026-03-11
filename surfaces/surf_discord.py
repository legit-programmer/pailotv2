
import asyncio
import discord
from discord.message import Message
from gateway.utils import _task_error_handler
from surfaces.ws_discord import connect_to_gateway, get_gateway, reset_gateway, receive_msgs
from models.events import Event, EventType
import os
from config import get_config


intents = discord.Intents.all()

client = discord.Client(intents=intents)
receiver_task = None


@client.event
async def on_ready():
    global receiver_task
    print(f'We have logged in as {client.user}')
    await connect_to_gateway("ws://localhost:8000/gateway/ws", token="valid_token")
    if receiver_task is None or receiver_task.done():
        receiver_task = asyncio.create_task(receive_msgs(client), name="discord_receiver")
        receiver_task.add_done_callback(_task_error_handler)


@client.event
async def on_message(message: Message):
    if message.author == client.user or message.author.id != get_config().discord_master_user_id:
        return
    gateway = await get_gateway()
    if gateway:
        # handle commands in a more robust way in the future, maybe with a command prefix and a command parser. For now, we just check if the message starts with certain strings.
        if message.content.startswith(">reset"):
            await reset_gateway()
            return await message.channel.send("Gateway reset successfully.")
        elif message.content.startswith(">session_reset"):
            try:
                await Event.client_send(gateway, EventType.RESET_SESSION, session_id=str(message.channel.id))
                await message.channel.send(f"Session {message.channel.id} has been reset.")
            except Exception as e:
                print(f"Failed to send reset session event to gateway: {e}")
                await reset_gateway()
                await message.channel.send("Failed to connect to gateway. Please try again later.")
            return
        elif message.content.startswith(">change_model"):
            parts = message.content.split()
            if len(parts) < 2:
                await message.channel.send("Please specify a model name. Usage: `>change_model <model_name>`")
                return
            new_model = parts[1]
            try:
                await Event.client_send(gateway, EventType.CHANGE_MODEL, data={"model": new_model}, session_id=str(message.channel.id))
                await message.channel.send(f"Model change request sent for session {message.channel.id} to {new_model}.")
                
            except Exception as e:
                print(f"Failed to send change model event to gateway: {e}")
                await reset_gateway()
                await message.channel.send("Failed to connect to gateway. Please try again later.")
            return
            
        try:
            messsage_to_send = ""
            if message.reference:
                original_message = message.reference.resolved if isinstance(message.reference.resolved, Message) else message.channel.fetch_message(message.reference.message_id)
                messsage_to_send += f"Replying to: {original_message.content}\n\n{message.content}"
            else:
                messsage_to_send = message.content
            await Event.client_send(gateway, EventType.USER_MESSAGE, data={"message": messsage_to_send}, session_id=str(message.channel.id))
            await message.channel.typing()
        except Exception as e:
            print(f"Failed to send message to gateway: {e}")
            await reset_gateway()

            await message.channel.send("Failed to connect to gateway. Please try again later.")

async def start_discord_bot():
    print("Starting Discord bot...")
    await client.start(os.getenv("BOT_TOKEN"))
