from collections import defaultdict
from telethon import TelegramClient


async def send_messages_to_users(data: dict, tg_client: TelegramClient) -> None:
    """
    Принимает словарь из ListLinksUpdate, tg_client
    группирует уведомления по пользователям и рассылает

    :param data:
    :param tg_client:
    :return:
    """

    links_group = defaultdict(list)
    for link in data.get("links", []):
        links_group[link["tg_chat_id"]].append(link)

    for tg_chat_id, links in links_group.items():
        text = ""
        for link in links:
            text += f"⚡ Есть обновления по ссылке {link['url']}:\n{link['description']}\n\n"
        if text:
            await tg_client.send_message(int(tg_chat_id), text)
