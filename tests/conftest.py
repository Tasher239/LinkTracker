from typing import AsyncGenerator, Generator
import sys
import asyncio
from urllib.parse import urlparse
from unittest.mock import MagicMock, Mock, AsyncMock
import json, aiokafka, redis.asyncio as aioredis
from contextlib import suppress

import pytest
import pytest_asyncio
from _pytest.monkeypatch import MonkeyPatch
from telethon import TelegramClient
from telethon.events import NewMessage

from fastapi.testclient import TestClient

from src.database.sql_database import user_states, user_data, SqlDbProcessor
from src.database.orm_database import OrmDbProcessor
from src.database.run_migrations import run_liquibase_migrations_with_params

from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer
from testcontainers.kafka import KafkaContainer
import os

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

TelegramClient.start = lambda self, **_: self


@pytest.fixture(autouse=True)
def mock_event() -> Mock:
    event = Mock(spec=NewMessage.Event)
    event.input_chat = "test_chat"
    event.chat_id = 123456789
    event.sender_id = 123456789
    event.message = MagicMock()
    event.message.text = "Test message"
    event.client = MagicMock(spec=TelegramClient)
    event.reply = AsyncMock()
    event.respond = AsyncMock()
    return event


@pytest.fixture(autouse=True)
def reset_state():
    user_states.clear()
    user_data.clear()


@pytest_asyncio.fixture(scope="session")
def postgres_container() -> Generator[str, None, None]:
    with PostgresContainer("postgres:13") as postgres:
        url = postgres.get_connection_url()
        if url.startswith("postgresql+psycopg2"):
            url = url.replace("postgresql+psycopg2", "postgresql", 1)
        yield url


@pytest_asyncio.fixture(scope="session")
async def liquibase_migrate(postgres_container: str) -> AsyncGenerator[None, None]:
    """
    Выполняет миграции Liquibase, используя параметры подключения,
    полученные из URL, возвращаемого postgres_container.
    """
    parsed = urlparse(postgres_container)
    host: str = parsed.hostname or "localhost"
    port: int = parsed.port or 5432
    dbname: str = parsed.path.lstrip("/") or "test"
    username: str = parsed.username or (os.getenv("POSTGRES_USER") or "postgres")
    password: str = parsed.password or (os.getenv("POSTGRES_PASSWORD") or "postgres")

    run_liquibase_migrations_with_params(host, port, dbname, username, password)
    yield


@pytest_asyncio.fixture
async def orm_db_processor(
    postgres_container: str, liquibase_migrate: None
) -> AsyncGenerator[OrmDbProcessor, None]:
    _ = liquibase_migrate
    processor = OrmDbProcessor(postgres_container)
    await processor.connect()
    yield processor
    await processor.close()


@pytest_asyncio.fixture
async def sql_db_processor(
    postgres_container: str, liquibase_migrate: None
) -> AsyncGenerator[SqlDbProcessor, None]:
    processor = SqlDbProcessor(postgres_container)
    await processor.connect()
    yield processor
    await processor.close()


@pytest_asyncio.fixture
async def override_db_processor(
    monkeypatch: MonkeyPatch, orm_db_processor: OrmDbProcessor
) -> AsyncGenerator[OrmDbProcessor, None]:
    """
    Создаём тестовый db_processor и подменяем
    все места, где он импортирован.
    """
    monkeypatch.setattr("src.initialization.database_init.db_processor", orm_db_processor)
    monkeypatch.setattr("src.api.scrapper_api.scrapper_api.db_processor", orm_db_processor)

    yield orm_db_processor


@pytest.fixture
def client(
    override_db_processor: OrmDbProcessor,
) -> Generator[TestClient, None, None]:
    """
    Создаём FastAPI + TestClient.
    db_processor уже пропатчен, поэтому
    в scrapper_api.py будет тестовый процессор.
    """
    from fastapi import FastAPI
    from src.api.scrapper_api.scrapper_api import scrapper_api_router

    _ = override_db_processor

    app = FastAPI()
    app.include_router(scrapper_api_router)

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def redis_conn_url() -> str:
    """
    Возвращает URL для подключения к Redis.
    """
    with RedisContainer() as rc:
        url = rc.get_connection_url()
        os.environ["REDIS_URL"] = url
        yield url


@pytest_asyncio.fixture
async def redis_client(redis_conn_url):
    client = aioredis.from_url(redis_conn_url, decode_responses=True)
    yield client
    await client.flushall()
    await client.close()


@pytest.fixture(scope="session")
def kafka_bootstrap() -> str:
    with KafkaContainer() as kc:
        bs = kc.get_bootstrap_servers()
        os.environ["KAFKA_UPDATES_TOPIC"] = "updates_topic"
        os.environ["KAFKA_DEAD_LETTER_TOPIC"] = "dlq_topic"
        yield bs


@pytest_asyncio.fixture
async def kafka_producer(kafka_bootstrap):
    producer = aiokafka.AIOKafkaProducer(
        bootstrap_servers=kafka_bootstrap,
        value_serializer=lambda v: json.dumps(v).encode(),
    )
    await producer.start()
    yield producer
    await producer.stop()


@pytest_asyncio.fixture
async def dlq_consumer(kafka_bootstrap):
    consumer = aiokafka.AIOKafkaConsumer(
        os.getenv("KAFKA_DEAD_LETTER_TOPIC"),
        bootstrap_servers=kafka_bootstrap,
        group_id="tests",
        auto_offset_reset="earliest",
        value_deserializer=lambda x: json.loads(x.decode()),
    )
    await consumer.start()
    yield consumer
    await consumer.stop()


class DummyTG:
    """Простой тг‑кдиент для проверки рассылки"""

    def __init__(self):
        self.sent: list[tuple[int, str]] = []

    async def send_message(self, chat_id: int, text: str):
        self.sent.append((chat_id, text))


@pytest.fixture
async def kafka_consumer_task(event_loop, kafka_bootstrap):
    """Запускаем consume_messages() в фоне и отдаём DummyTG"""
    from src.api.bot_api.kafka_consumer import consume_messages

    dummy_tg = DummyTG()

    task = event_loop.create_task(
        consume_messages(
            dummy_tg,
            kafka_bootstrap,
            os.getenv("KAFKA_UPDATES_TOPIC"),
            os.getenv("KAFKA_DEAD_LETTER_TOPIC"),
        )
    )

    await asyncio.sleep(1)
    yield dummy_tg
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
