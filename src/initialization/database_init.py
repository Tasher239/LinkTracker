import os
from dotenv import load_dotenv

from src.database.sql_database import SqlDbProcessor
from src.database.orm_database import OrmDbProcessor
import asyncio

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
ACCESS_TYPE = os.getenv("ACCESS_TYPE", "SQL")

db_processor: SqlDbProcessor | OrmDbProcessor

match ACCESS_TYPE:
    case "SQL":
        db_processor = SqlDbProcessor(DATABASE_URL)
    case "ORM":
        db_processor = OrmDbProcessor(DATABASE_URL)
    case _:
        raise ValueError(f"Unknown ACCESS_TYPE: {ACCESS_TYPE}")


async def create_db():
    """Функция инициализации БД"""
    database_name = DATABASE_URL.rsplit("/", 1)[1]
    await db_processor.create_database(database_name)


if __name__ == "__main__":
    asyncio.run(create_db())
