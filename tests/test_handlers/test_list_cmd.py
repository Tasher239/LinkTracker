import pytest
from unittest.mock import AsyncMock, patch, Mock
from http import HTTPStatus
import httpx

import src.bot.handlers.list_cmd_handler as handler_mod
from src.bot.handlers.list_cmd_handler import list_cmd_handler


@pytest.fixture(autouse=True)
def disable_redis_cache(monkeypatch):
    monkeypatch.setattr(handler_mod.redis_client, "get", AsyncMock(return_value=None))
    monkeypatch.setattr(handler_mod.redis_client, "set", AsyncMock(return_value=None))


@pytest.mark.asyncio
async def test_list_cmd_handler_empty_list(mock_event: Mock) -> None:
    mock_event.message.text = "/list"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(
            status_code=HTTPStatus.OK,
            json={"links": [], "size": 0},
        )

        await list_cmd_handler(mock_event)

        mock_event.respond.assert_called_once_with(
            "Список отслеживаемых ссылок пуст\n" "Вы можете добавить ссылку с помощью /track",
            parse_mode="Markdown",
        )


@pytest.mark.asyncio
async def test_list_cmd_handler_with_links(mock_event: Mock) -> None:
    mock_event.message.text = "/list"

    test_links = [
        {"url": "https://example1.com"},
        {"url": "https://example2.com"},
        {"url": "https://example3.com"},
    ]

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(
            status_code=HTTPStatus.OK,
            json={"links": test_links, "size": len(test_links)},
        )

        await list_cmd_handler(mock_event)

        expected_message = (
            "Список отслеживаемых ссылок🔗:\n\n"
            "1. https://example1.com\n"
            "2. https://example2.com\n"
            "3. https://example3.com\n"
        )

        mock_event.respond.assert_called_once_with(expected_message, parse_mode="Markdown")


@pytest.mark.asyncio
async def test_list_cmd_handler_server_error(mock_event: Mock) -> None:
    mock_event.message.text = "/list"

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = httpx.Response(status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        await list_cmd_handler(mock_event)

        mock_event.respond.assert_called_once_with(
            "❌ Произошла ошибка при получении списка отслеживаемых ссылок"
        )
