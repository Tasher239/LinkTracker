from telethon import events
from dotenv import load_dotenv
import os
from src.initialization.bot_client_init import bot_client

load_dotenv()
SCRAPPER_API_URL = os.getenv("SCRAPPER_API_URL")

valid_commands: set[str] = {
    "/start",
    "/help",
    "/track",
    "/untrack",
    "/list",
    "/notifications",
    "/upds_by_tags",
}


@bot_client.on(events.NewMessage)  # type: ignore
async def unknown_cmd_handler(event: events.NewMessage.Event):
    """
    Обрабатывает неизвестные команды
    :param event:
    :return:
    """
    if event.text.startswith("/") and event.text not in valid_commands:
        await event.reply("Неизвестная команда. Пожалуйста, используйте правильные команды.")
