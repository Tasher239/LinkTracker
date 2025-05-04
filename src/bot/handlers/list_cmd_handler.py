import os
import httpx
import json
import redis.asyncio as redis

from dotenv import load_dotenv
from http import HTTPStatus
from telethon import events

from src.initialization.bot_client_init import bot_client
from src.logger.logger_init import logger

load_dotenv()
SCRAPPER_API_URL = os.getenv("SCRAPPER_API_URL")
REDIS_URL = os.getenv("REDIS_URL")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)


@bot_client.on(events.NewMessage(pattern="/list"))  # type: ignore
async def list_cmd_handler(event: events.NewMessage.Event):
    """
    Показывает список отслеживаемых ссылок
    :param event:
    :return:
    """
    user_id = event.sender_id
    cache_key = f"links:{user_id}"
    cached_value = await redis_client.get(cache_key)
    if cached_value:
        logger.debug("Данные для /list найдены в кэше.")
        data = json.loads(cached_value)
    else:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SCRAPPER_API_URL}/links", headers={"tg-chat-id": str(user_id)}
            )

            match response.status_code:
                case HTTPStatus.OK:
                    data = response.json()
                    await redis_client.set(cache_key, json.dumps(data))
                case _:
                    await event.respond(
                        "❌ Произошла ошибка при получении списка отслеживаемых ссылок"
                    )
                    return

    if data["size"] == 0:
        text = "Список отслеживаемых ссылок пуст\nВы можете добавить ссылку с помощью /track"
    else:
        text = "Список отслеживаемых ссылок🔗:\n\n"
        for num, link in enumerate(data["links"], start=1):
            text += f"{num}. {link['url']}\n"
    await event.respond(text, parse_mode="Markdown")
