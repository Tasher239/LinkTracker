import pytest
from unittest.mock import Mock
from src.bot.handlers.unknown_cmd_handler import unknown_cmd_handler


@pytest.mark.asyncio
@pytest.mark.parametrize("command", ["/unknown_command", "/list_all", "/"])
async def test_unknown_command(mock_event: Mock, command: str) -> None:
    """Проверяем, что бот отвечает на неизвестную команду"""
    mock_event.text = command
    await unknown_cmd_handler(mock_event)
    mock_event.reply.assert_called_with(
        "Неизвестная команда. Пожалуйста, используйте правильные команды."
    )
