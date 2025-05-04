import json
import os
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from dotenv import load_dotenv
from src.api.bot_api.bot_send_message import send_messages_to_users

from telethon import TelegramClient
from logger.logger_init import logger

load_dotenv()


async def consume_messages(
    bot_client: TelegramClient,
    kafka_servers: str = "localhost:9092",
    topic: str = os.getenv("KAFKA_UPDATES_TOPIC"),
    dlq_topic: str = os.getenv("KAFKA_DEAD_LETTER_TOPIC"),
):
    """
    Создает Kafka consumer, рассылающего уведомления пользователям
    :param bot_client:
    :param kafka_servers:
    :param topic:
    :param dlq_topic:
    :return:
    """
    consumer = AIOKafkaConsumer(topic, bootstrap_servers=kafka_servers, group_id="bot_group")

    dlq_producer = AIOKafkaProducer(
        bootstrap_servers=kafka_servers, value_serializer=lambda v: json.dumps(v).encode("utf-8")
    )

    await consumer.start()
    logger.info("Kafka consumer запущен!")
    await dlq_producer.start()
    try:
        async for msg in consumer:
            try:
                data = json.loads(msg.value.decode("utf-8"))
                logger.debug(f"Данные получены!!!\n{data}")
                await send_messages_to_users(data, bot_client)
            except Exception as e:
                print("Ошибка обработки сообщения:", e)
                dead_letter_payload = {
                    "error": str(e),
                    "original_message": msg.value.decode("utf-8", errors="ignore"),
                }
                await dlq_producer.send_and_wait(dlq_topic, dead_letter_payload)
    finally:
        await consumer.stop()
        await dlq_producer.stop()
