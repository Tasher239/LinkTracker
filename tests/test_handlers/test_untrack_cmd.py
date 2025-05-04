import pytest
from unittest.mock import patch, AsyncMock
from http import HTTPStatus
import httpx
from src.bot.handlers.untrack_cmd_handler import (
    untrack_cmd_handler,
    handle_waiting_for_choice,
    handle_waiting_for_confirmation,
)
from src.database.sql_database import user_states, user_data
from src.bot.states.states import UnTrackState


@pytest.mark.asyncio
async def test_untrack_cmd_handler_empty_list(mock_event: AsyncMock) -> None:
    """Тест: Бот должен сообщить, что список отслеживаемых ссылок пуст"""
    mock_event.message.text = "/untrack"

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            status_code=HTTPStatus.OK,
            json={"links": [], "size": 0},
        )

        await untrack_cmd_handler(mock_event)

        mock_event.respond.assert_called_once_with(
            "Список отслеживаемых ссылок пуст\nУдалять нечего",
            parse_mode="Markdown",
        )


@pytest.mark.asyncio
async def test_untrack_cmd_handler_with_links(mock_event: AsyncMock) -> None:
    """Тест: Бот должен корректно вывести список ссылок для удаления"""
    mock_event.message.text = "/untrack"

    test_links = [
        {"url": "https://example1.com"},
        {"url": "https://example2.com"},
    ]

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = httpx.Response(
            status_code=HTTPStatus.OK,
            json={"links": test_links, "size": len(test_links)},
        )

        await untrack_cmd_handler(mock_event)

        expected_message = (
            "Выберите номер ссылки, которую хотите прекратить отслеживать🔗:\n\n"
            "1. https://example1.com\n"
            "2. https://example2.com\n"
        )

        mock_event.respond.assert_called_once_with(expected_message, parse_mode="Markdown")


@pytest.mark.asyncio
async def test_handle_waiting_for_choice_invalid_number(mock_event: AsyncMock) -> None:
    """Тест: Бот должен отправлять ошибку, если пользователь ввел некорректный номер"""
    mock_event.message.text = "abc"  # Некорректный ввод (не число)

    await handle_waiting_for_choice(mock_event, mock_event.sender_id)

    mock_event.respond.assert_called_once_with("❌ Некорректный ввод номера ссылки.")


@pytest.mark.asyncio
async def test_handle_waiting_for_confirmation_success(mock_event: AsyncMock) -> None:
    """Тест: Бот должен успешно удалить ссылку"""
    mock_event.message.text = "✅ Подтвердить"

    user_data["deleted_link_number"] = 1
    user_data["user_links"] = {"links": [{"url": "https://example.com"}]}
    user_states[mock_event.sender_id] = UnTrackState.WAITING_FOR_CONFIRMATION

    with patch("httpx.AsyncClient.delete") as mock_delete:
        mock_delete.return_value = httpx.Response(status_code=HTTPStatus.OK)

        await handle_waiting_for_confirmation(mock_event, mock_event.sender_id)

        mock_event.respond.assert_called_once_with(
            "✅ Ссылка https://example.com успешно удалена из отслеживания!"
        )


@pytest.mark.asyncio
async def test_handle_waiting_for_confirmation_fail(mock_event: AsyncMock) -> None:
    mock_event.message.text = "✅ Подтвердить"

    user_data["deleted_link_number"] = 1
    user_data["user_links"] = {"links": [{"url": "https://example.com"}]}
    user_states[mock_event.sender_id] = UnTrackState.WAITING_FOR_CONFIRMATION

    with patch("httpx.AsyncClient.delete") as mock_delete:
        mock_delete.return_value = httpx.Response(status_code=HTTPStatus.BAD_REQUEST)

        await handle_waiting_for_confirmation(mock_event, mock_event.sender_id)

        mock_event.respond.assert_called_once_with("❌ Произошла ошибка при удалении ссылки")
