import pytest
from unittest.mock import patch, Mock
from http import HTTPStatus
import httpx
from src.bot.handlers.track_cmd_handler import track_cmd_handler
from src.bot.handlers.track_cmd_handler import handle_waiting_for_link
from src.bot.handlers.track_cmd_handler import handle_waiting_for_tags
from src.bot.handlers.track_cmd_handler import handle_waiting_for_filters
from src.bot.handlers.track_cmd_handler import handle_waiting_for_confirmation
from src.database.sql_database import user_states, user_data
from src.bot.states.states import TrackState


@pytest.mark.asyncio
async def test_track_cmd_handler(mock_event: Mock) -> None:
    """Тест: Бот должен перевести пользователя в WAITING_FOR_LINK после /track"""
    mock_event.message.text = "/track"

    await track_cmd_handler(mock_event)

    assert user_states[mock_event.sender_id] == TrackState.WAITING_FOR_LINK
    mock_event.respond.assert_called_once_with(
        "Пожалуйста, отправьте ссылку, которую хотите отслеживать."
    )


@pytest.mark.asyncio
async def test_handle_waiting_for_link(mock_event: Mock) -> None:
    """Тест: Бот должен перейти в WAITING_FOR_TAGS после ввода ссылки"""
    mock_event.message.text = "https://example.com"

    await handle_waiting_for_link(mock_event, mock_event.sender_id)

    assert user_states[mock_event.sender_id] == TrackState.WAITING_FOR_TAGS
    assert user_data["entered_link"] == "https://example.com"
    mock_event.respond.assert_called_once_with(
        "Пожалуйста, введите теги, каждый с новой строки (опционально)\n"
        "Или «-», если теги не нужны"
    )


@pytest.mark.asyncio
async def test_handle_waiting_for_tags(mock_event: Mock) -> None:
    """Тест: Бот должен перейти в WAITING_FOR_FILTERS после ввода тегов"""
    mock_event.message.text = "tag1\ntag2"

    await handle_waiting_for_tags(mock_event, mock_event.sender_id)

    assert user_states[mock_event.sender_id] == TrackState.WAITING_FOR_FILTERS
    assert user_data["entered_tags"] == ["tag1", "tag2"]
    mock_event.respond.assert_called_once_with(
        "Пожалуйста, введите фильтры, каждый с новой строки (опционально)\n"
        "Или «-», если фильтры не нужны"
    )


@pytest.mark.asyncio
async def test_handle_waiting_for_filters(mock_event: Mock) -> None:
    """Тест: Бот должен показать подтверждение после ввода фильтров"""
    mock_event.message.text = "filter1\nfilter2"

    # вписываем entered_tags и entered_link, чтобы избежать KeyError
    user_data["entered_tags"] = ["tag1", "tag2"]
    user_data["entered_link"] = "https://example.com"

    await handle_waiting_for_filters(mock_event, mock_event.sender_id)

    assert user_states[mock_event.sender_id] == TrackState.WAITING_FOR_CONFIRMATION
    assert user_data["entered_filters"] == ["filter1", "filter2"]

    mock_event.respond.assert_called_once()
    args, kwargs = mock_event.respond.call_args
    assert "Вы хотите отслеживать ссылку" in args[0]  # Проверяем текст подтверждения


@pytest.mark.asyncio
async def test_handle_waiting_for_confirmation_success(mock_event: Mock) -> None:
    """Тест: Бот успешно добавляет ссылку в трекер"""
    mock_event.message.text = "✅ Подтвердить"
    user_data["entered_link"] = "https://example.com"
    user_data["entered_tags"] = ["tag1"]
    user_data["entered_filters"] = ["filter1"]
    user_states[mock_event.sender_id] = TrackState.WAITING_FOR_CONFIRMATION

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = httpx.Response(status_code=HTTPStatus.OK)

        await handle_waiting_for_confirmation(mock_event, mock_event.sender_id)

        mock_event.respond.assert_called_once_with(
            "✅ Ссылка https://example.com успешно добавлена в список отслеживаемых!"
        )


@pytest.mark.asyncio
async def test_handle_waiting_for_confirmation_fail(mock_event: Mock) -> None:
    """Тест: Бот отправляет ошибку, если не удалось добавить ссылку"""
    mock_event.message.text = "✅ Подтвердить"
    user_data["entered_link"] = "https://example.com"
    user_data["entered_tags"] = ["tag1"]
    user_data["entered_filters"] = ["filter1"]
    user_states[mock_event.sender_id] = TrackState.WAITING_FOR_CONFIRMATION

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = httpx.Response(status_code=HTTPStatus.BAD_REQUEST)

        await handle_waiting_for_confirmation(mock_event, mock_event.sender_id)

        mock_event.respond.assert_called_once_with("❌ Ссылка не добавлена")


@pytest.mark.asyncio
async def test_handle_waiting_for_confirmation_duplicate(mock_event: Mock) -> None:
    """Тест: Бот отправляет ошибку 409, если пользователь пытается добавить
    уже существующую ссылку."""

    mock_event.message.text = "✅ Подтвердить"
    user_data["entered_link"] = "https://example.com"
    user_data["entered_tags"] = ["tag1"]
    user_data["entered_filters"] = ["filter1"]
    user_states[mock_event.sender_id] = TrackState.WAITING_FOR_CONFIRMATION

    with patch("httpx.AsyncClient.post") as mock_post:
        mock_post.return_value = httpx.Response(status_code=HTTPStatus.CONFLICT)

        await handle_waiting_for_confirmation(mock_event, mock_event.sender_id)

        mock_event.respond.assert_called_once_with("❌ Вы уже отслеживаете эту ссылку")
