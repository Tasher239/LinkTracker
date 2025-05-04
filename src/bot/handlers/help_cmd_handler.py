from telethon.events import NewMessage
from telethon import events
from src.bot.lexicon.lexicon import Commands
from src.initialization.bot_client_init import bot_client


@bot_client.on(events.NewMessage(pattern="/help"))  # type: ignore
async def help_cmd_handler(event: NewMessage.Event) -> None:
    """
    Показывает список доступных команд
    :param event:
    :return:
    """
    text = (
        f"Бот реагирует на следующие команды:\n\n"
        f"{Commands.LIST} - Показать список отслеживаемых ссылок\n"
        f"{Commands.TRACK} - Начать отслеживание ссылки\n"
        f"{Commands.UNTRACK} - Прекратить отслеживание ссылки\n"
        f"{Commands.HELP} - Вывод списка доступных команд\n"
    )

    await event.client.send_message(
        entity=event.input_chat,
        message=text,
    )
