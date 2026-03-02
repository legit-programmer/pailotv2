
import discord
from discord.message import Message
from surfaces.ws_discord import connect_to_gateway, get_gateway, reset_gateway
from models.events import Event, EventType
from dotenv import load_dotenv
import os
load_dotenv()  

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    await connect_to_gateway("ws://localhost:8000/gateway/ws", token="valid_token")  

@client.event
async def on_message(message: Message):
    if message.author == client.user or message.author.id != 1466514404941103309:
        return
    gateway = await get_gateway()
    if gateway:
        try:
            await Event.client_send(gateway, EventType.USER_MESSAGE, data={"message": message.content}, session_id=str(message.channel.id))
        except Exception as e:
            print(f"Failed to send message to gateway: {e}")
            await reset_gateway()
            await message.channel.send("Failed to connect to gateway. Please try again later.")

client.run(os.getenv("BOT_TOKEN"))
