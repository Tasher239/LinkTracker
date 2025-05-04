import asyncio
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dotenv import load_dotenv

import uvicorn
from fastapi import FastAPI
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.responses import Response

from src.initialization.database_init import db_processor
from src.api.scrapper_api.scrapper_api import scrapper_api_router
from src.logger.logger_init import logger


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> Response:
    logger.exception("Invalid request data: %s", exc)
    return await request_validation_exception_handler(request, exc)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await db_processor.connect()
    yield
    await db_processor.close()


app = FastAPI(title="scrapper_app", lifespan=lifespan)

app.exception_handler(RequestValidationError)(validation_exception_handler)
app.include_router(router=scrapper_api_router)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

if __name__ == "__main__":
    uvicorn.run(
        "src.scrapper_app:app",
        host=os.getenv("SCRAPPER_API_HOST"),
        port=int(os.getenv("SCRAPPER_API_PORT")),
        log_level=os.getenv("LOGGING_LEVEL", "info").lower(),
    )
