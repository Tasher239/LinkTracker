import aiocron

from dotenv import load_dotenv
from telethon import events, Button

from src.initialization.notification_service_init import notif_service
from src.initialization.bot_client_init import bot_client
from src.logger.logger_init import logger

load_dotenv()

immediate_cron_pattern = "* * * * *"
digest_cron_pattern = "* 20 * * *"  # Каждый день в 20:00

current_cron_expression = immediate_cron_pattern
current_cron_handle = None


@bot_client.on(events.NewMessage(pattern="/notifications"))  # type: ignore
async def notifications_cmd_handler(event: events.NewMessage.Event) -> None:
    """
    Выбор режима уведомлений
    :param event:
    :return:
    """
    buttons = [
        [
            Button.inline("Сразу (каждую минуту)", b"notif_immediate"),
            Button.inline("Дайджест (раз в сутки)", b"notif_digest"),
        ]
    ]
    await event.respond("Выберите режим уведомлений:", buttons=buttons)


async def send_notifications_global():
    """
    Дерагет метод отправки уведомлений пользователям
    у объекта сервиса нотификации
    :return:
    """
    try:
        logger.debug("Отправка уведомлений согласно новому расписанию.")
        await notif_service.send_notifications()
    except Exception as e:
        logger.exception("Ошибка при отправке уведомлений: %s", e)


def schedule_notifications(cron_pattern: str):
    """
    Останавливает текущую задачу, если она уже запущена,
    и создает новую с заданным расписанием
    :param cron_pattern:
    :return:
    """
    global current_cron_handle
    if current_cron_handle is not None:
        current_cron_handle.stop()
    current_cron_handle = aiocron.crontab(cron_pattern, start=True)(send_notifications_global)
    logger.info("Создана крон-задача уведомлений с расписанием: %s", cron_pattern)


@bot_client.on(events.CallbackQuery)  # type: ignore
async def notifications_callback_handler(event: events.CallbackQuery.Event) -> None:
    """
    Обработчик выбора режима уведомлений:
      - "notif_immediate" для немедленных уведомлений (каждую минуту)
      - "notif_digest" для дайджеста (раз в сутки)
    :param event:
    :return:
    """
    global current_cron_expression
    data = event.data
    if data == b"notif_immediate":
        current_cron_expression = immediate_cron_pattern
        schedule_notifications(current_cron_expression)
        await event.edit(
            "Режим уведомлений обновлен: *Сразу* (каждую минуту)", parse_mode="Markdown"
        )
    elif data == b"notif_digest":
        current_cron_expression = digest_cron_pattern
        schedule_notifications(current_cron_expression)
        await event.edit(
            "Режим уведомлений обновлен: *Дайджест* (раз в сутки)", parse_mode="Markdown"
        )
    else:
        await event.answer("Неизвестный выбор!", alert=True)


schedule_notifications(current_cron_expression)
