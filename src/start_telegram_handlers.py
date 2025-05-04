import asyncio

from telethon.tl.functions.bots import SetBotCommandsRequest
from telethon.tl.types import BotCommandScopeDefault, BotCommand
from telethon import TelegramClient

from src.initialization.bot_client_init import bot_client, settings
from src.logger.logger_init import logger

from src.bot.handlers import (
    help_cmd_handler,
    start_cmd_handler,
    track_cmd_handler,
    untrack_cmd_handler,
    list_cmd_handler,
    notification_cmd_handler,
    unknown_cmd_handler,
    upds_by_tag_cmd_handler,
)


async def set_commands(bot: TelegramClient) -> None:
    """
    Автоматически генерирует меню бота с командами
    :param bot:
    :return:
    """
    commands = [
        BotCommand(command="start", description="Запуск бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="track", description="Отслеживание ссылок"),
        BotCommand(command="untrack", description="Прекратить отслеживание"),
        BotCommand(command="list", description="Список отслеживаемых ссылок"),
        BotCommand(command="notifications", description="Выбор времени нотификации"),
        BotCommand(command="upds_by_tags", description="Обновления по тегу"),
    ]

    await bot(
        SetBotCommandsRequest(scope=BotCommandScopeDefault(), lang_code="ru", commands=commands)
    )


async def main() -> None:
    """
    Запускает бота и хендлеры сообщений
    :return:
    """
    logger.info("Run the event loop to start receiving messages")
    await bot_client.start(bot_token=settings.token)
    async with bot_client:
        try:
            await set_commands(bot_client)
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass
        except Exception as exc:
            logger.exception("Main loop raised error.", extra={"exc": exc})
            raise


if __name__ == "__main__":
    """
    Запуск тг бота
    """
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
