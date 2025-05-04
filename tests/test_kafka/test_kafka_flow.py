import asyncio
import pytest
import os

TOPIC = os.getenv("KAFKA_UPDATES_TOPIC")


@pytest.mark.asyncio
async def test_valid_message_processed(kafka_producer, kafka_consumer_task):
    """Валидное сообщение уходит пользователю."""
    payload = {
        "links": [
            {
                "id": 1,
                "url": "https://ex.com",
                "description": "upd",
                "tg_chat_id": 777,
            }
        ]
    }
    await kafka_producer.send_and_wait(TOPIC, payload)
    await asyncio.sleep(0.5)
    dummy = kafka_consumer_task
    assert dummy.sent == [(777, "⚡ Есть обновления по ссылке https://ex.com:\nupd\n\n")]


@pytest.mark.asyncio
async def test_invalid_message_goes_to_dlq(kafka_producer, dlq_consumer):
    """Некорректный payload попадает в dead‑letter‑topic"""
    await kafka_producer.send_and_wait(TOPIC, b"broken json")
    async for msg in dlq_consumer:
        value = msg.value
        assert "original_message" in value and "error" in value
        break
