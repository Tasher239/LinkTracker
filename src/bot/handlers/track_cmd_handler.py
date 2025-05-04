from telethon import events, Button
from dotenv import load_dotenv
from http import HTTPStatus
import redis.asyncio as redis
import os
import httpx
import json


from src.database.sql_database import user_states, user_data
from src.initialization.bot_client_init import bot_client
from src.bot.states.states import TrackState
from src.api.schemas.schemas import AddLinkRequest

load_dotenv()
SCRAPPER_API_URL = os.getenv("SCRAPPER_API_URL")
REDIS_URL = os.getenv("REDIS_URL")

redis_client = redis.from_url(REDIS_URL, decode_responses=True)


async def handle_waiting_for_link(event: events.NewMessage.Event, user_id: int) -> None:
    """
    Ожидает ввод ссылки и
    переходит в состояние ожидания тегов
    :param event:
    :param user_id:
    :return:
    """
    link = event.message.text.strip()
    user_data["entered_link"] = link
    user_states[user_id] = TrackState.WAITING_FOR_TAGS
    await event.respond(
        "Пожалуйста, введите теги, каждый с новой строки (опционально)\n"
        "Или «-», если теги не нужны"
    )


async def handle_waiting_for_tags(event: events.NewMessage.Event, user_id: int) -> None:
    """
    Ожидает ввод тегов и переходит в состояние ожидания фильтров
    :param event:
    :param user_id:
    :return:
    """
    tags = event.message.text.strip().split("\n")
    user_data["entered_tags"] = tags
    user_states[user_id] = TrackState.WAITING_FOR_FILTERS
    await event.respond(
        "Пожалуйста, введите фильтры, каждый с новой строки (опционально)\n"
        "Или «-», если фильтры не нужны"
    )


async def handle_waiting_for_filters(event: events.NewMessage.Event, user_id: int) -> None:
    """
    Ожидает ввод фильтров и переходит в состояние ожидания подтверждения
    :param event:
    :param user_id:
    :return:
    """
    filters = event.message.text.strip().split("\n")
    user_data["entered_filters"] = filters
    user_states[user_id] = TrackState.WAITING_FOR_CONFIRMATION

    buttons = [
        [
            Button.text("✅ Подтвердить", resize=True),
            Button.text("❌ Отменить", resize=True),
        ]
    ]

    if user_data["entered_tags"] == ["-"]:
        entered_tags_str = "-\n"
    else:
        entered_tags_str = "\n".join(f"«{tag}»" for tag in user_data["entered_tags"]) + "\n"

    if user_data["entered_filters"] == ["-"]:
        entered_filters_str = "-"
    else:
        entered_filters_str = "\n".join(
            f"«{filter_name}»" for filter_name in user_data["entered_filters"]
        )

    text = (
        f"Вы хотите отслеживать ссылку: {user_data['entered_link']}\n"
        f"теги:\n{entered_tags_str}"
        f"фильтры:\n{entered_filters_str}"
    )
    await event.respond(text, buttons=buttons)


async def handle_waiting_for_confirmation(event: events.NewMessage.Event, user_id: int) -> None:
    """
    Ожидает подтверждение от пользователя и региструет ссылку
    :param event:
    :param user_id:
    :return:
    """
    text = event.message.text.strip().lower()
    if text in ["✅ подтвердить", "подтвердить"]:
        entered_link = user_data.get("entered_link")
        entered_tags = user_data.get("entered_tags")
        entered_filters = user_data.get("entered_filters")
        if entered_link is None or entered_tags is None or entered_filters is None:
            raise ValueError("Не все необходимые данные введены")

        if entered_tags == ["-"]:
            entered_tags = []
        if entered_filters == ["-"]:
            entered_filters = []
        data = AddLinkRequest(url=entered_link, tags=entered_tags, filters=entered_filters)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{SCRAPPER_API_URL}/links",
                headers={"tg-chat-id": str(user_id)},
                json=data.dict(),
            )

            match response.status_code:
                case HTTPStatus.OK:
                    cache_key = f"links:{user_id}"
                    cache_json = await redis_client.get(cache_key)
                    if cache_json:
                        try:
                            cached_data = json.loads(cache_json)
                        except Exception:
                            cached_data = {"links": [], "size": 0}
                    else:
                        cached_data = {"links": [], "size": 0}

                    new_link_entry = data.dict()
                    cached_data["links"].append(new_link_entry)
                    cached_data["size"] = len(cached_data["links"])
                    await redis_client.set(cache_key, json.dumps(cached_data))

                    await event.respond(
                        f"✅ Ссылка {entered_link} успешно добавлена в список отслеживаемых!"
                    )
                case HTTPStatus.CONFLICT:
                    await event.respond(f"❌ Вы уже отслеживаете эту ссылку")
                case _:
                    await event.respond("❌ Ссылка не добавлена")
    else:
        await event.respond("❌ Ссылка не добавлена")

    user_states.pop(user_id, None)
    user_data.pop("entered_link", None)
    user_data.pop("entered_tags", None)
    user_data.pop("entered_filters", None)


@bot_client.on(events.NewMessage())  # type: ignore
async def handle_confirm_track_messages(event: events.NewMessage.Event) -> None:
    user_id = event.sender_id
    state = user_states.get(user_id)
    if state == TrackState.WAITING_FOR_LINK:
        await handle_waiting_for_link(event, user_id)
    elif state == TrackState.WAITING_FOR_TAGS:
        await handle_waiting_for_tags(event, user_id)
    elif state == TrackState.WAITING_FOR_FILTERS:
        await handle_waiting_for_filters(event, user_id)
    elif state == TrackState.WAITING_FOR_CONFIRMATION:
        await handle_waiting_for_confirmation(event, user_id)


@bot_client.on(events.NewMessage(pattern="/track"))  # type: ignore
async def track_cmd_handler(event: events.NewMessage.Event) -> None:
    user_id = event.sender_id
    user_states[user_id] = TrackState.WAITING_FOR_LINK
    await event.respond("Пожалуйста, отправьте ссылку, которую хотите отслеживать.")
