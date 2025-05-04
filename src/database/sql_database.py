import asyncpg

from src.api.schemas.schemas import AddLinkRequest, LinkResponse
from src.api.utils.string_makers import make_description
from src.api.schemas.schemas import LinkUpdate
from src.api.scrapper_api.utils_scrapper_api import check_last_update
from typing import Any, Optional, cast
from logger.logger_init import logger
import asyncio

user_states: dict[int, Any] = {}  # храним состояния пользователей
user_data: dict[str, Any] = {}  # храним текущие данные пользователя


class SqlDbProcessor:
    def __init__(self, db_url: str):
        self.db_url = db_url
        self.pool: Optional[asyncpg.Pool] = None
        self.BATCH_SIZE = 500

    async def create_database(self, database_name: str):
        """Создает базу данных, если её нет"""
        sys_db_url = (
            self.db_url.rsplit("/", 1)[0] + "/postgres"
        )  # Подключение к системной БД postgres
        conn = await asyncpg.connect(sys_db_url)

        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", database_name
        )

        if not db_exists:
            await conn.execute(f'CREATE DATABASE "{database_name}"')
            print(f"База данных '{database_name}' успешно создана!")
        else:
            print(f"База данных '{database_name}' уже существует.")

        await conn.close()

    async def connect(self):
        """Создает пул подключений"""
        self.pool = await asyncpg.create_pool(self.db_url)
        logger.info("Соединение с БД успешно установлено")

    async def close(self):
        if self.pool:
            await self.pool.close()
            logger.info("Соединение с БД успешно закрыто")

    # async def create_tables(self):
    #     """Создаем таблицы, если их нет"""
    #     if self.pool is None:
    #         raise RuntimeError("Connection pool is not initialized. Call connect() first.")
    #     async with self.pool.acquire() as conn:
    #         await conn.execute(
    #             """
    #                 CREATE TABLE IF NOT EXISTS users(
    #                     tg_chat_id BIGINT PRIMARY KEY
    #                 );
    #
    #                 CREATE TABLE IF NOT EXISTS links(
    #                     id SERIAL PRIMARY KEY,
    #                     link_url TEXT NOT NULL UNIQUE
    #                 );
    #
    #                 CREATE TABLE IF NOT EXISTS user_links (
    #                     user_id BIGINT NOT NULL REFERENCES users(tg_chat_id) ON DELETE CASCADE,
    #                     link_id INTEGER NOT NULL REFERENCES links(id) ON DELETE CASCADE,
    #                     tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    #                     filters TEXT[] DEFAULT ARRAY[]::TEXT[],
    #                     PRIMARY KEY (user_id, link_id)
    #                 );
    #         """
    #         )

    async def add_user(self, tg_chat_id: int):
        """Добавление пользователя в бд"""
        if not self.pool:
            raise RuntimeError("Connection pool is not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (tg_chat_id) VALUES ($1) ON CONFLICT DO NOTHING", tg_chat_id
            )

    async def add_link_for_user(self, tg_chat_id: int, add_link: AddLinkRequest) -> int:
        """Добавляет ссылку пользователю, если её ещё нет"""
        if not self.pool:
            raise RuntimeError("Connection pool is not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Проверяем, существует ли пользователь
                user_exists = await conn.fetchval(
                    "SELECT 1 FROM users WHERE tg_chat_id = $1", tg_chat_id
                )
                if not user_exists:
                    raise ValueError(f"Пользователь {tg_chat_id} не зарегистрирован")

                # Проверяем, существует ли ссылка
                link_id = await conn.fetchval(
                    "SELECT id FROM links WHERE link_url = $1", add_link.url
                )

                # Если ссылки нет, создаем новую
                if not link_id:
                    link_id = await conn.fetchval(
                        """
                        INSERT INTO links (link_url) VALUES ($1) 
                        ON CONFLICT (link_url) DO NOTHING 
                        RETURNING id
                        """,
                        add_link.url,
                    )

                # Здесь link_id может быть None, если почему-то не вернулся id
                if not link_id:
                    raise RuntimeError("Failed to insert or find link_id")

                # Проверяем, отслеживает ли пользователь уже эту ссылку
                tracking_exists = await conn.fetchval(
                    "SELECT 1 FROM user_links WHERE user_id = $1 AND link_id = $2",
                    tg_chat_id,
                    link_id,
                )
                if tracking_exists:
                    raise ValueError(
                        f"Пользователь {tg_chat_id} уже отслеживает ссылку {add_link.url}"
                    )

                await conn.execute(
                    """
                    INSERT INTO user_links (user_id, link_id, tags, filters)
                    VALUES ($1, $2, $3, $4)
                    """,
                    tg_chat_id,
                    link_id,
                    add_link.tags,
                    add_link.filters,
                )

                return cast(int, link_id)  # Возвращаем ID ссылки

    async def get_user_links(self, tg_chat_id: int) -> list[LinkResponse]:
        """Возвращает все ссылки пользователя"""
        if not self.pool:
            raise RuntimeError("Connection pool is not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            links = await conn.fetch(
                """
                SELECT user_links.link_id, links.link_url, user_links.tags, user_links.filters
                FROM user_links
                JOIN links ON user_links.link_id = links.id
                WHERE user_links.user_id = $1;
                """,
                tg_chat_id,
            )

            return [
                LinkResponse(
                    id=link["link_id"],
                    url=link["link_url"],
                    tags=list(link["tags"]) if link["tags"] else [],
                    filters=list(link["filters"]) if link["filters"] else [],
                )
                for link in links
            ]

    async def delete_chat(self, tg_chat_id: int) -> bool:
        if not self.pool:
            raise RuntimeError("Connection pool is not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            # проверяем, есть ли чат в БД
            chat_exists = await conn.fetchval(
                "SELECT 1 FROM users WHERE tg_chat_id = $1", tg_chat_id
            )
            if not chat_exists:
                return False
            await conn.execute("DELETE FROM users WHERE tg_chat_id = $1", tg_chat_id)
            return True

    async def remove_user_link(
        self, tg_chat_id: int, link_url: str
    ) -> tuple[int, list[str], list[str]] | None:
        if not self.pool:
            raise RuntimeError("Connection pool is not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                link_data = await conn.fetchrow(
                    "SELECT id, link_url FROM links WHERE link_url = $1", link_url
                )

                if not link_data:
                    return None

                link_id = link_data["id"]

                user_link_data = await conn.fetchrow(
                    "SELECT tags, filters FROM user_links WHERE user_id = $1 AND link_id = $2",
                    tg_chat_id,
                    link_id,
                )

                if not user_link_data:
                    return None

                tags, filters = user_link_data["tags"], user_link_data["filters"]

                await conn.execute(
                    "DELETE FROM user_links WHERE user_id = $1 AND link_id = $2",
                    tg_chat_id,
                    link_id,
                )

                return link_id, tags, filters

    async def check_updates_for_all_users(self) -> list[LinkUpdate]:
        """Проверяет обновления для всех пользователей пакетами по 500 записей параллельно"""
        if not self.pool:
            raise RuntimeError("Connection pool is not initialized. Call connect() first.")
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                cursor = await conn.cursor(
                    """
                    SELECT user_links.user_id, user_links.link_id, links.link_url, user_links.filters
                    FROM user_links
                    JOIN links ON user_links.link_id = links.id
                    """,
                )

                updates = []

                while True:
                    rows = await cursor.fetch(self.BATCH_SIZE)
                    if not rows:
                        break

                    # Создаем задачи для обработки каждой ссылки
                    tasks = [
                        self._process_user_link(
                            row["user_id"], row["link_id"], row["link_url"], row["filters"] or []
                        )
                        for row in rows
                    ]

                    batch_results = await asyncio.gather(*tasks)
                    updates.extend([res for res in batch_results if res is not None])

                return updates

    @staticmethod
    async def _process_user_link(
        tg_chat_id: int,
        link_id: int,
        link_url: str,
        filters: list[str],
    ) -> LinkUpdate | None:
        update_info = await check_last_update(link_url)
        if update_info and (not filters or update_info.user_name in filters):
            descr = await make_description(update_info)
            return LinkUpdate(
                id=link_id,
                url=link_url,
                description=descr,
                tg_chat_id=tg_chat_id,
            )

        return None

    async def get_updates_for_one_user_by_tags(
        self, tg_chat_id: int, tags: list[str]
    ) -> list[LinkUpdate]:
        if not self.pool:
            raise RuntimeError("Connection pool is not initialized. Call connect() first.")

        async with self.pool.acquire() as conn:
            # Берём из user_links только те записи, у которых массив tags пересекается с заданным
            rows = await conn.fetch(
                """
                SELECT ul.user_id,
                       ul.link_id,
                       l.link_url,
                       ul.filters
                FROM user_links AS ul
                JOIN links AS l
                  ON ul.link_id = l.id
                WHERE ul.user_id = $1
                  AND ul.tags && $2::text[]
                """,
                tg_chat_id,
                tags,
            )

        tasks = [
            self._process_user_link(row["user_id"], row["link_id"], row["link_url"], [])
            for row in rows
        ]
        results = await asyncio.gather(*tasks)

        return [upd for upd in results if upd is not None]
