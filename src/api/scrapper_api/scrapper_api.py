from fastapi import APIRouter, Header, Body, Query
from fastapi.responses import JSONResponse

from src.initialization.database_init import db_processor
from src.api.schemas.schemas import (
    ApiErrorResponse,
    LinkResponse,
    AddLinkRequest,
    RemoveLinkRequest,
    ListLinksResponse,
    ListLinksUpdate,
)

scrapper_api_router = APIRouter()


@scrapper_api_router.post(
    "/tg-chat/{tg_chat_id}",
    responses={
        200: {"description": "Чат зарегистрирован"},
        400: {"model": ApiErrorResponse, "description": "Некорректные параметры запроса"},
    },
)
async def register_user(tg_chat_id: int) -> JSONResponse:
    """
    Зарегистрировать чат
    :param tg_chat_id:
    :return:
    """

    try:
        await db_processor.add_user(tg_chat_id)
        return JSONResponse(status_code=200, content={"message": "Чат зарегистрирован"})
    except (KeyError, ValueError) as e:
        error_response = ApiErrorResponse(
            description="Некорректные параметры запроса",
            code="400",
            exception_name=type(e).__name__,
            exception_message=str(e),
            stacktrace=[],
        )
        return JSONResponse(status_code=400, content=error_response.dict())


@scrapper_api_router.delete(
    "/tg-chat/{tg_chat_id}",
    responses={
        200: {"description": "Чат успешно удален"},
        400: {"model": ApiErrorResponse, "description": "Некорректные параметры запроса"},
        404: {"model": ApiErrorResponse, "description": "Чат не существует"},
    },
)
async def delete_chat(tg_chat_id: int) -> JSONResponse:
    """
    Удалить чат
    :param tg_chat_id:
    :return:
    """
    try:
        status = await db_processor.delete_chat(tg_chat_id)
        if status is False:
            error_data = ApiErrorResponse(
                description="Чат не существует",
                code="404",
                exception_name="KeyError",
                exception_message="KeyError",
                stacktrace=[],
            ).dict()
            return JSONResponse(status_code=404, content=error_data)
        return JSONResponse(status_code=200, content={"message": "Чат удален"})
    except (KeyError, ValueError) as e:
        error_data = ApiErrorResponse(
            description="Некорректные параметры запроса",
            code="400",
            exception_name=type(e).__name__,
            exception_message=str(e),
            stacktrace=[],
        ).dict()
        return JSONResponse(status_code=400, content=error_data)


@scrapper_api_router.get(
    "/links",
    response_model=ListLinksResponse,
    responses={
        200: {"model": ListLinksResponse, "description": "Ссылки успешно получены"},
        400: {"model": ApiErrorResponse, "description": "Некорректные параметры запроса"},
    },
)
async def get_links(tg_chat_id: int = Header(...)) -> ListLinksResponse | JSONResponse:
    """
    Получить все отслеживаемые ссылки
    :param tg_chat_id:
    :return:
    """
    try:
        links = await db_processor.get_user_links(tg_chat_id)
        return ListLinksResponse(links=links, size=len(links))
    except (KeyError, ValueError) as e:
        error_response = ApiErrorResponse(
            description="Некорректные параметры запроса",
            code="400",
            exception_name=type(e).__name__,
            exception_message=str(e),
            stacktrace=[],
        ).dict()
        return JSONResponse(status_code=400, content=error_response)


@scrapper_api_router.post(
    "/links",
    response_model=None,
    responses={
        200: {"description": "Ссылка успешно добавлена"},
        400: {"model": ApiErrorResponse, "description": "Некорректные параметры запроса"},
        409: {"model": ApiErrorResponse, "description": "Ссылка уже существует"},
    },
)
async def add_link(
    tg_chat_id: int = Header(...), data: AddLinkRequest = Body(...)
) -> LinkResponse | JSONResponse:
    """
    Добавление новой ссылки
    :param tg_chat_id:
    :param data:
    :return:
    """
    try:
        new_link_id = await db_processor.add_link_for_user(tg_chat_id, data)
        return LinkResponse(id=new_link_id, url=data.url, tags=data.tags, filters=data.filters)

    except ValueError as e:
        return JSONResponse(
            status_code=409,
            content={
                "description": "Ссылка уже добавлена пользователем",
                "code": "409",
                "exception_name": "LinkAlreadyExists",
                "exception_message": str(e),
                "stacktrace": [],
            },
        )


@scrapper_api_router.delete(
    "/links",
    response_model=None,
    responses={
        200: {"description": "Ссылка успешно убрана"},
        400: {"model": ApiErrorResponse, "description": "Некорректные параметры запроса"},
        404: {"model": ApiErrorResponse, "description": "Ссылка не найдена"},
    },
)
async def delete_link(
    tg_chat_id: int = Header(...), data: RemoveLinkRequest = Query(...)
) -> LinkResponse | JSONResponse:
    """
    Убрать отслеживание ссылки
    :param tg_chat_id:
    :param data:
    :return:
    """
    try:
        result = await db_processor.remove_user_link(tg_chat_id, data.url)

        if result is None:
            return JSONResponse(
                status_code=404,
                content={
                    "description": "Ссылка не найдена",
                    "code": "404",
                    "exception_name": "KeyError",
                    "exception_message": "Ссылка не отслеживается пользователем или не существует",
                    "stacktrace": [],
                },
            )

        link_id, link_tags, link_filters = result
        return LinkResponse(id=link_id, url=data.url, tags=link_tags, filters=link_filters)

    except (KeyError, ValueError) as e:
        return JSONResponse(
            status_code=400,
            content={
                "description": "Некорректные параметры запроса",
                "code": "400",
                "exception_name": type(e).__name__,
                "exception_message": str(e),
                "stacktrace": [],
            },
        )


@scrapper_api_router.get(
    "/updates",
    response_model=None,
    responses={
        200: {"description": "Обновления успешно проверены"},
        400: {"model": ApiErrorResponse, "description": "Некорректные параметры запроса"},
        404: {"model": ApiErrorResponse, "description": "Ссылка не найдена"},
    },
)
async def check_updates() -> ListLinksUpdate | JSONResponse:
    """
    Проверить обновления
    :return:
    """
    try:
        updates = await db_processor.check_updates_for_all_users()
        return ListLinksUpdate(links=updates)

    except KeyError as e:
        return JSONResponse(
            status_code=404,
            content={
                "description": "Ссылка не найдена",
                "code": "404",
                "exception_name": "KeyError",
                "exception_message": str(e),
                "stacktrace": [],
            },
        )

    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "description": "Некорректные параметры запроса",
                "code": "400",
                "exception_name": type(e).__name__,
                "exception_message": str(e),
                "stacktrace": [],
            },
        )


@scrapper_api_router.get(
    "/updates_by_tags",
    response_model=None,
    responses={
        200: {"description": "Обновления успешно проверены"},
        400: {"model": ApiErrorResponse, "description": "Некорректные параметры запроса"},
    },
)
async def check_updates_by_tags(
    tg_chat_id: int = Query(...), tags: list[str] = Query(...)
) -> ListLinksUpdate | JSONResponse:
    """
    Проверить обновления по тегам
    :param tg_chat_id:
    :param tags:
    :return:
    """
    try:
        updates = await db_processor.get_updates_for_one_user_by_tags(tg_chat_id, tags)
        return ListLinksUpdate(links=updates)

    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "description": "Некорректные параметры запроса",
                "code": "400",
                "exception_name": type(e).__name__,
                "exception_message": str(e),
                "stacktrace": [],
            },
        )
