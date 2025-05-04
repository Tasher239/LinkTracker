import pytest
from unittest.mock import AsyncMock, Mock
from src.bot.handlers.help_cmd_handler import help_cmd_handler
from src.bot.lexicon.lexicon import Commands


@pytest.mark.asyncio
async def test_help_cmd_handler(mock_event: Mock) -> None:
    """Тест: Бот должен отправлять список доступных команд"""
    mock_event.message.text = "/help"

    mock_event.client.send_message = AsyncMock()

    await help_cmd_handler(mock_event)

    expected_message = (
        "Бот реагирует на следующие команды:\n\n"
        f"{Commands.LIST} - Показать список отслеживаемых ссылок\n"
        f"{Commands.TRACK} - Начать отслеживание ссылки\n"
        f"{Commands.UNTRACK} - Прекратить отслеживание ссылки\n"
        f"{Commands.HELP} - Вывод списка доступных команд\n"
    )

    mock_event.client.send_message.assert_called_once_with(
        entity=mock_event.input_chat,
        message=expected_message,
    )
