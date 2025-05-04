from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse
from telethon import TelegramClient
from telethon.errors.rpcerrorlist import RPCError

from src.api.bot_api.bot_send_message import send_messages_to_users
from src.api.schemas.schemas import ListLinksUpdate, ApiErrorResponse

bot_api_router = APIRouter()


async def get_tg_client(request: Request) -> TelegramClient:
    """
    Получение TelegramClient из контекста приложения
    :param request:
    :return:
    """
    return request.app.tg_client


@bot_api_router.post(
    "/updates",
    responses={
        200: {"description": "Обновление обработано"},
        400: {"model": ApiErrorResponse, "description": "Некорректные параметры запроса"},
    },
)
async def send_update(
    data: ListLinksUpdate = Body(...), tg_client: TelegramClient = Depends(get_tg_client)
) -> JSONResponse:
    """
    Hhttp-бэкенд отправки уведомлений пользователям
    :param data:
    :param tg_client:
    :return:
    """
    try:
        await send_messages_to_users(data.dict(), tg_client)
        return JSONResponse(status_code=200, content={"status": "ok"})
    except RPCError as e:
        error_response = ApiErrorResponse(
            description="Internal error processing the update",
            code="400",
            exception_name=e.__class__.__name__,
            exception_message=str(e),
            stacktrace=[str(e)],
        )
        return JSONResponse(status_code=400, content=error_response.dict())
