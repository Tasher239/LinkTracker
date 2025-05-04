import httpx
import os
from telethon import events

from src.database.sql_database import user_states
from src.initialization.bot_client_init import bot_client

# сюда нужно положить ваш SCRAPPER_API_URL из конфига
SCRAPPER_API_URL = os.getenv("SCRAPPER_API_URL")


@bot_client.on(events.NewMessage())
async def upds_by_tag_handler(event: events.NewMessage.Event):
    """
    Высылает обновления по выбранным тегам
    :param event:
    :return:
    """
    chat_id = event.chat_id
    state = user_states.get(chat_id)
    if state != "AWAITING_UPDS_TAGS":
        return
    user_states.pop(chat_id, None)

    tags = event.raw_text.strip().split()
    if not tags:
        await event.reply("❗ Нужен хотя бы один тег. Попробуйте заново: /upds_by_tag")
        return

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{SCRAPPER_API_URL}/updates_by_tags",
                params={"tg_chat_id": chat_id, **{"tags": tags}},
                timeout=10.0,
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        await event.reply(f"❌ Ошибка при запросе обновлений: {e}")
        return

    updates = data.get("links", [])
    if not updates:
        await event.reply("ℹ️ Обновлений по заданным тегам не найдено.")
        return

    for upd in updates:
        text = f"⚡ Обновление по ссылке {upd['url']}:\n" f"{upd['description']}"
        await event.reply(text)


@bot_client.on(events.NewMessage(pattern="/upds_by_tags"))
async def upds_by_tag_cmd_handler(event: events.NewMessage.Event):
    """
    Ожидает ввод тегов
    :param event:
    :return:
    """
    chat_id = event.chat_id
    await event.reply("📝 Введите один или несколько тегов через пробел:")
    user_states[chat_id] = "AWAITING_UPDS_TAGS"
