import asyncio
from discord import Client
from models.events import Event


def verify_token(token: str) -> bool:
    # Placeholder for token verification logic
    # In a real implementation, this would check the token against a database or authentication service
    return token == "valid_token"

def _task_error_handler(task: asyncio.Task):
    """Callback that logs exceptions from fire-and-forget tasks."""
    if not task.cancelled() and task.exception():
        import traceback
        print(
            f"[ERROR] Background task '{task.get_name()}' raised an exception:")
        traceback.print_exception(
            type(task.exception()), task.exception(), task.exception().__traceback__)


async def get_discord_channel(channel_id: int, event: Event, client: Client):
    try:
        channel_id = int(event.session_id)
    except (TypeError, ValueError):
        print(
            f"Invalid session/channel id: {event.session_id}")
        return

    channel = client.get_channel(channel_id)
    if channel is None:
        try:
            channel = await client.fetch_channel(channel_id)
            return channel
        except Exception as fetch_error:
            print(
                f"Unable to resolve channel {channel_id}: {fetch_error}")
            return
    