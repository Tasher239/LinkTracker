import json, asyncio, pytest
from unittest.mock import AsyncMock, patch

from src.bot.handlers.list_cmd_handler import list_cmd_handler


class MockEvent:
    """минимальный Event с методом respond()"""

    def __init__(self, user_id):
        self.sender_id = user_id
        self.message = AsyncMock()
        self.message.text = "/list"
        self.respond = AsyncMock()


@pytest.mark.asyncio
async def test_cache_hit_and_invalidate(redis_client, monkeypatch):
    """
    Кэш отдаёт данные
    после добавления ссылки кэш инвалидируется
    """
    uid = 42
    key = f"links:{uid}"
    cached = {"links": [{"url": "cached"}], "size": 1}
    await redis_client.set(key, json.dumps(cached))

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_http:
        ev = MockEvent(uid)
        await list_cmd_handler(ev)
        mock_http.assert_not_called()

    from src.bot.handlers.track_cmd_handler import redis_client as rc_code

    await rc_code.delete(key)
    assert await redis_client.get(key) is None
