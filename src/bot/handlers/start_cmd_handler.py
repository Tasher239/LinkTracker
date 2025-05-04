from telethon.events import NewMessage
from src.initialization.bot_client_init import bot_client
from telethon import events
from dotenv import load_dotenv
import os
import httpx
from http import HTTPStatus

load_dotenv()
SCRAPPER_API_URL = os.getenv("SCRAPPER_API_URL")


@bot_client.on(events.NewMessage(pattern="/start"))  # type: ignore
async def start_cmd_handler(event: NewMessage.Event) -> None:
    """
    Обрабатывает команду /start
    Отправляет welcome сообщение пользователю и регистрирует его в системе
    :param event:
    :return:
    """
    user_id = event.sender_id
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{SCRAPPER_API_URL}/tg-chat/{user_id}")
    match response.status_code:
        case HTTPStatus.OK:
            text = (
                f"Здравствуйте, {event.sender.first_name}!\n\n"
                "Добро пожаловать в бота!\n"
                "Нажмите /help для получения списка команд."
            )
        case _:
            text = "❌ Ошибка регистрации. Попробуйте позже."

    await event.client.send_message(
        entity=event.input_chat,
        message=text,
        reply_to=event.message,
    )
