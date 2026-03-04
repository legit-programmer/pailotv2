
import asyncio
import discord
from discord.message import Message
from surfaces.ws_discord import connect_to_gateway, get_gateway, reset_gateway, receive_msgs
from models.events import Event, EventType
import os


intents = discord.Intents.all()

client = discord.Client(intents=intents)
receiver_task = None


@client.event
async def on_ready():
    global receiver_task
    print(f'We have logged in as {client.user}')
    await connect_to_gateway("ws://localhost:8000/gateway/ws", token="valid_token")
    if receiver_task is None or receiver_task.done():
        receiver_task = asyncio.create_task(receive_msgs(client))


@client.event
async def on_message(message: Message):
    if message.author == client.user or message.author.id != 1466514404941103309:
        return
    gateway = await get_gateway()
    if gateway:
        try:
            await Event.client_send(gateway, EventType.USER_MESSAGE, data={"message": message.content}, session_id=str(message.channel.id))
            await message.channel.typing()
        except Exception as e:
            print(f"Failed to send message to gateway: {e}")
            await reset_gateway()

            await message.channel.send("Failed to connect to gateway. Please try again later.")

async def start_discord_bot():
    print("Starting Discord bot...")
    await client.start(os.getenv("BOT_TOKEN"))
