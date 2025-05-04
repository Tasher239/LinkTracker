import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload
from sqlalchemy_utils import create_database, database_exists
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine

from src.logger.logger_init import logger
from src.database.orm_models import Base, User, Link, UserLink
from src.api.schemas.schemas import AddLinkRequest, LinkResponse, LinkUpdate
from src.api.scrapper_api.utils_scrapper_api import check_last_update
from src.api.utils.string_makers import make_description


class OrmDbProcessor:
    BATCH_SIZE = 500

    def __init__(self, db_url: str):
        """
        Инициализация обработчика БД через SQLAlchemy ORM
        """
        self.db_url = db_url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def create_database(self, database_name: str):
        """
        Создает базу данных, если её нет — через sqlalchemy-utils.
        """
        # Формируем URL для новой базы, заменяя последнее название на database_name
        new_db_url = self.db_url.rsplit("/", 1)[0] + f"/{database_name}"
        new_db_url = new_db_url.replace("postgresql://", "postgresql+psycopg://")

        if not database_exists(new_db_url):
            create_database(new_db_url)
            logger.info(f"База данных '{database_name}' успешно создана!")
        else:
            logger.info(f"База данных '{database_name}' уже существует.")

    async def connect(self):
        """
        Асинхронное подключение к целевой базе данных.
        Создаёт движок и фабрику сессий (async_sessionmaker).
        """
        async_db_url = self.db_url.replace("postgresql://", "postgresql+psycopg://")
        self._engine = create_async_engine(async_db_url, echo=False, future=True)
        self._session_factory = async_sessionmaker(bind=self._engine, expire_on_commit=False)
        logger.info(f"Подключение установлено{self._engine}, {self._session_factory}")

    def _get_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._session_factory is None:
            raise RuntimeError("Session factory is not initialized. Call connect() first.")
        return self._session_factory

    async def close(self):
        """
        Закрывает подключение к БД
        """
        if self._engine:
            await self._engine.dispose()

    async def create_tables(self):
        """
        Создает таблицы, если их нет
        """
        if self._engine is None:
            raise RuntimeError("Engine is not initialized.")
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def add_user(self, tg_chat_id: int):
        """
        Добавление пользователя в БД (ON CONFLICT DO NOTHING)
        """
        factory = self._get_session_factory()
        async with factory() as session:
            async with session.begin():
                existing_user = await session.get(User, tg_chat_id)
                if existing_user:
                    return
                new_user = User(tg_chat_id=tg_chat_id)
                session.add(new_user)

    async def add_link_for_user(self, tg_chat_id: int, add_link: AddLinkRequest) -> int:
        """
        Добавляет ссылку пользователю, если её ещё нет.
        Возвращает ID добавленной (или найденной) ссылки.
        """
        factory = self._get_session_factory()
        async with factory() as session:
            async with session.begin():
                user = await session.get(User, tg_chat_id)
                if not user:
                    raise ValueError(f"Пользователь {tg_chat_id} не зарегистрирован")

                result = await session.execute(select(Link).filter_by(link_url=add_link.url))
                link = result.scalars().first()
                if link is None:
                    link = Link(link_url=add_link.url)
                    session.add(link)
                    await session.flush()

                result = await session.execute(
                    select(UserLink).filter_by(user_id=tg_chat_id, link_id=link.id)
                )
                exist_track = result.scalars().first()
                if exist_track:
                    raise ValueError(
                        f"Пользователь {tg_chat_id} уже отслеживает ссылку {add_link.url}"
                    )
                user_link = UserLink(
                    user_id=tg_chat_id,
                    link_id=link.id,
                    tags=add_link.tags,
                    filters=add_link.filters,
                )
                session.add(user_link)
                return link.id

                # def _find_link(sync_session: Session) -> Link | None:
                #     return sync_session.query(Link).filter_by(link_url=add_link.url).first()
                #
                # link_obj = await session.run_sync(_find_link)
                #
                # if not link_obj:
                #     link_obj = Link(link_url=add_link.url)
                #     session.add(link_obj)
                #     await session.flush()
                #
                # def _find_userlink(sync_session: Session) -> UserLink | None:
                #     return (
                #         sync_session.query(UserLink)
                #         .filter_by(user_id=tg_chat_id, link_id=link_obj.id)
                #         .first()
                #     )
                #
                # existing_ul = await session.run_sync(_find_userlink)
                # if existing_ul:
                #     raise ValueError(
                #         f"Пользователь {tg_chat_id} уже отслеживает ссылку {add_link.url}"
                #     )
                #
                # # 5) Создаём новую связь
                # user_link = UserLink(
                #     user_id=user.tg_chat_id,
                #     link_id=link_obj.id,
                #     tags=add_link.tags,
                #     filters=add_link.filters,
                # )
                # session.add(user_link)
                # return link_obj.id

    async def get_user_links(self, tg_chat_id: int) -> list[LinkResponse]:
        factory = self._get_session_factory()
        async with factory() as session:
            user = await session.get(User, tg_chat_id)
            if not user:
                return []

            return [
                LinkResponse(
                    id=ul.link.id,
                    url=ul.link.link_url,
                    tags=ul.tags or [],
                    filters=ul.filters or [],
                )
                for ul in user.user_links
            ]

    async def delete_chat(self, tg_chat_id: int) -> bool:
        factory = self._get_session_factory()
        async with factory() as session:
            async with session.begin():
                user = await session.get(User, tg_chat_id)
                if not user:
                    return False
                await session.delete(user)
                return True

    async def remove_user_link(
        self, tg_chat_id: int, link_url: str
    ) -> tuple[int, list[str], list[str]] | None:
        factory = self._get_session_factory()
        async with factory() as session:
            async with session.begin():
                user = await session.get(User, tg_chat_id)
                if not user:
                    return None

                user_link_to_remove = None
                for ul in user.user_links:
                    if ul.link and ul.link.link_url == link_url:
                        user_link_to_remove = ul
                        break

                if not user_link_to_remove:
                    return None

                link_id = user_link_to_remove.link_id
                tags = user_link_to_remove.tags or []
                filters = user_link_to_remove.filters or []

                await session.delete(user_link_to_remove)
                return link_id, tags, filters

    async def check_updates_for_all_users(self) -> list[LinkUpdate]:
        updates = []
        offset = 0
        factory = self._get_session_factory()

        while True:
            async with factory() as session:
                result = await session.execute(
                    select(User)
                    .options(selectinload(User.user_links).selectinload(UserLink.link))
                    .offset(offset)
                    .limit(self.BATCH_SIZE)
                )
                users = result.scalars().all()

                if not users:
                    break

                tasks = [
                    asyncio.create_task(self._process_user_link(ul))
                    for user in users
                    for ul in user.user_links
                    if ul.link
                ]

                batch_results = await asyncio.gather(*tasks)

                # Отфильтровываем None (если обновлений не было)
                updates.extend([res for res in batch_results if res is not None])

            offset += self.BATCH_SIZE

        return updates

    @staticmethod
    async def _process_user_link(ul: UserLink) -> LinkUpdate | None:
        update_info = await check_last_update(ul.link.link_url)
        # если есть фильтры, значит ссылку нужно пропускать только если она проходит фильтр

        if update_info and (not ul.filters or update_info.user_name in ul.filters):
            return LinkUpdate(
                id=ul.link_id,
                url=ul.link.link_url,
                description=await make_description(update_info),
                tg_chat_id=ul.user_id,
            )

        return None

    async def get_updates_for_one_user_by_tags(
        self, tg_chat_id: int, tags: list[str]
    ) -> list[LinkUpdate]:
        factory = self._get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(UserLink)
                .options(selectinload(UserLink.link))
                .where(UserLink.user_id == tg_chat_id, UserLink.tags.overlap(tags))
            )
            links = result.unique().scalars().all()

            coros = (self._process_user_link(ul) for ul in links if ul.link)
            results = await asyncio.gather(*coros)
            return [upd for upd in results if upd is not None]
