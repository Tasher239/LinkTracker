from src.bot.settings.settings import TGBotSettings
from telethon import TelegramClient

settings = TGBotSettings()  # type: ignore[call-arg]
bot_client = TelegramClient("session_files/tg_bot_session", settings.api_id, settings.api_hash)
