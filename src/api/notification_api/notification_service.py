import httpx
import json
import os
from http import HTTPStatus
from aiokafka import AIOKafkaProducer
from dotenv import load_dotenv

from src.logger.logger_init import logger
from src.api.schemas.schemas import ListLinksUpdate


load_dotenv()
SCRAPPER_API_URL = os.getenv("SCRAPPER_API_URL")
BOT_API_URL = os.getenv("BOT_API_URL")


class NotificationService:
    """
    Сервис нотификации, его методы через экземпляр периодически вызывают крон-задачи
    """

    def __init__(self, transport_type):
        self.transport_type = transport_type
        match self.transport_type.lower():
            case "kafka":
                self.send_func = self._send_via_kafka
            case "http":
                self.send_func = self._send_via_http

    @staticmethod
    async def get_updated_links() -> ListLinksUpdate:
        """
        Делает hhtp-запрос на scrapper для получения апдейтов
        :return:
        """
        async with httpx.AsyncClient() as scrapper_api_client:
            response = await scrapper_api_client.get(f"{SCRAPPER_API_URL}/updates")
            if response.status_code == HTTPStatus.OK:
                return response.json()

    async def _send_via_http(self) -> None:
        """
        Делает http-запрос на сервис бота, чтобы отправить апдейты
        :return:
        """
        list_links = await self.get_updated_links()
        async with httpx.AsyncClient() as bot_api_client:
            response = await bot_api_client.post(f"{BOT_API_URL}/updates", json=list_links)
            if response.status_code != HTTPStatus.OK:
                logger.error("Ошибка отправки уведомлений")

    async def _send_via_kafka(self):
        """
        Consumer записывает уведомления в топик апдейтов Kafka
        :return:
        """
        list_links = await self.get_updated_links()
        if len(list_links) > 0:
            producer = AIOKafkaProducer(
                bootstrap_servers="localhost:9092",
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            await producer.start()
            try:
                await producer.send_and_wait(os.getenv("KAFKA_UPDATES_TOPIC"), list_links)
                logger.debug("Уведомления отправлены в Kafka")
            finally:
                await producer.stop()

    async def send_notifications(self):
        """
        Функция, для внешнего дерганья,
        инкапсулирующая отправку уведомлений
        :return:
        """
        await self.send_func()
