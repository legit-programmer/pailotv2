import asyncio
import websockets


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