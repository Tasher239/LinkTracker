import asyncio
import uvicorn
import os
import sys

from dotenv import load_dotenv
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from telethon.errors.rpcerrorlist import ApiIdInvalidError
from telethon import TelegramClient

from src.api.bot_api.kafka_consumer import consume_messages
from src.api.bot_api.http_bot_api import bot_api_router
from src.logger.logger_init import logger
from src.bot.settings.settings import TGBotSettings

load_dotenv()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = TGBotSettings()
    bot_client = TelegramClient(
        "session_files/kafka_bot_session", settings.api_id, settings.api_hash
    )
    await bot_client.start(bot_token=settings.token)
    loop = asyncio.get_event_loop()
    loop.set_default_executor(
        ThreadPoolExecutor(
            max_workers=4,
        ),
    )

    async with AsyncExitStack() as stack:
        try:
            app.tg_client = await stack.enter_async_context(bot_client)  # type: ignore[attr-defined]
        except ApiIdInvalidError:
            logger.info("Working without telegram client inside.")

        yield
        await stack.aclose()

    await loop.shutdown_default_executor()


def create_bot_app(lifespan) -> FastAPI:
    app = FastAPI(title="bot_app", lifespan=lifespan)
    app.include_router(router=bot_api_router)

    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


def run_http_bot():
    app = create_bot_app(lifespan)
    uvicorn.run(
        app,
        host=os.getenv("BOT_API_HOST"),
        port=int(os.getenv("BOT_API_PORT")),
        log_level=os.getenv("LOGGING_LEVEL", "info").lower(),
    )


async def run_kafka_bot_consumer():
    settings = TGBotSettings()  # type: ignore[call-arg]
    bot_client = TelegramClient(
        "session_files/kafka_bot_session", settings.api_id, settings.api_hash
    )
    await bot_client.start(bot_token=settings.token)
    async with bot_client:
        try:
            await consume_messages(bot_client)
        except KeyboardInterrupt:
            pass
        except Exception as exc:
            logger.exception("Main loop raised error.", extra={"exc": exc})
            raise


if __name__ == "__main__":
    """По типу доставки сообщений запускаем сервер (http) или consumer (kafka)"""

    APP_MESSAGE_TRANSPORT = os.getenv("APP_MESSAGE_TRANSPORT").lower()
    match APP_MESSAGE_TRANSPORT:
        case "http":
            run_http_bot()
        case "kafka":
            loop = asyncio.get_event_loop()
            loop.run_until_complete(run_kafka_bot_consumer())
        case _:
            raise ValueError(f"Unknown APP_MESSAGE_TRANSPORT: {APP_MESSAGE_TRANSPORT}")
