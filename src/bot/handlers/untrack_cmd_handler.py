from telethon import events, Button
from dotenv import load_dotenv
from http import HTTPStatus
import httpx
import os
from typing import Any
import redis.asyncio as redis
import json

from src.bot.states.states import UnTrackState
from src.database.sql_database import user_states, user_data
from src.initialization.bot_client_init import bot_client
from src.api.schemas.schemas import RemoveLinkRequest

load_dotenv()

SCRAPPER_API_URL = os.getenv("SCRAPPER_API_URL")
REDIS_URL = os.getenv("REDIS_URL")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)


async def handle_waiting_for_choice(event: events.NewMessage.Event, user_id: int) -> None:
    """
    Ожидает ввод номера ссылки и переходит в состояние ожидания подтверждения
    :param event:
    :param user_id:
    :return:
    """
    try:
        deleted_link_id = int(event.message.text.strip())
    except ValueError:
        await event.respond("❌ Некорректный ввод номера ссылки.")
        return
    user_data["deleted_link_number"] = deleted_link_id
    user_states[user_id] = UnTrackState.WAITING_FOR_CONFIRMATION

    buttons = [
        [
            Button.text("✅ Подтвердить", resize=True),
            Button.text("❌ Отменить", resize=True),
        ]
    ]
    await event.respond(
        f"Перестать отслеживать ресурс под номером {deleted_link_id}?",
        buttons=buttons,
    )


async def handle_waiting_for_confirmation(event: events.NewMessage.Event, user_id: int) -> None:
    """
    Ожидает подтверждение удаления ссылки
    :param event:
    :param user_id:
    :return:
    """
    text = event.message.text.strip().lower()
    if text in ["✅ подтвердить", "подтвердить"]:
        deleted_link_number = user_data.get("deleted_link_number")
        if deleted_link_number is None:
            raise ValueError("Не все необходимые данные введены")

        user_links = user_data.get("user_links")
        if user_links is None:
            raise ValueError("Данные о ссылках отсутствуют")

        links_list = user_links.get("links")
        if not isinstance(links_list, list) or not (1 <= deleted_link_number <= len(links_list)):
            await event.respond("❌ Неверный номер ссылки.")
            return

        link_url = links_list[deleted_link_number - 1].get("url")
        if not isinstance(link_url, str):
            await event.respond("❌ Ошибка: ссылка имеет неверный формат.")
            return

        data = RemoveLinkRequest(url=link_url)
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{SCRAPPER_API_URL}/links",
                headers={"tg-chat-id": str(user_id)},
                params={"url": data.url},
            )

        match response.status_code:
            case HTTPStatus.OK:
                await event.respond(f"✅ Ссылка {link_url} успешно удалена из отслеживания!")
                cache_key = f"links:{user_id}"
                cached_json = await redis_client.get(cache_key)
                if cached_json:
                    try:
                        cached_data = json.loads(cached_json)
                    except Exception:
                        cached_data = {"links": [], "size": 0}
                else:
                    cached_data = None

                if cached_data and "links" in cached_data:
                    new_links = [
                        link for link in cached_data["links"] if link.get("url") != link_url
                    ]
                    cached_data["links"] = new_links
                    cached_data["size"] = len(new_links)
                    await redis_client.set(cache_key, json.dumps(cached_data))
            case _:
                await event.respond("❌ Произошла ошибка при удалении ссылки")
    else:
        await event.respond("❌ Удаление отменено")
    user_states.pop(user_id, None)


@bot_client.on(events.NewMessage())  # type: ignore
async def handle_messages(event: events.NewMessage.Event) -> None:
    """
    Обрабатывает сообщения от пользователя
    :param event:
    :return:
    """
    user_id = event.sender_id
    user_state = user_states.get(user_id)

    if user_state == UnTrackState.WAITING_FOR_CHOICE:
        await handle_waiting_for_choice(event, user_id)
    elif user_state == UnTrackState.WAITING_FOR_CONFIRMATION:
        await handle_waiting_for_confirmation(event, user_id)


@bot_client.on(events.NewMessage(pattern="/untrack"))  # type: ignore
async def untrack_cmd_handler(event: events.NewMessage.Event) -> None:
    """
    Обрабатывает команду /untrack
    :param event:
    :return:
    """
    user_id = event.sender_id
    user_states[user_id] = UnTrackState.WAITING_FOR_CHOICE

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{SCRAPPER_API_URL}/links", headers={"tg-chat-id": str(user_id)}
        )

        match response.status_code:
            case HTTPStatus.OK:
                data: dict[str, Any] = response.json()
            case _:
                await event.respond("❌ Произошла ошибка при получении списка отслеживаемых ссылок")
                return

    user_data["user_links"] = data
    if data.get("size", 0) == 0:
        text = "Список отслеживаемых ссылок пуст\nУдалять нечего"
    else:
        text = "Выберите номер ссылки, которую хотите прекратить отслеживать🔗:\n\n"
        links = data.get("links")
        if isinstance(links, list):
            for num, link in enumerate(links, start=1):
                url = link.get("url", "неизвестно")
                text += f"{num}. {url}\n"
        else:
            text = "❌ Неверный формат данных о ссылках."
    await event.respond(text, parse_mode="Markdown")
