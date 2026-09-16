import json
import logging
from typing import Any
import aio_pika
from fastapi import FastAPI
from app.core.config import settings

logger = logging.getLogger(__name__)

class RabbitMQClient:
    def __init__(self):
        self.connection: aio_pika.RobustConnection | None = None
        self.channel: aio_pika.RobustChannel | None = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        self.channel = await self.connection.channel()
        logger.info("Connected to RabbitMQ")

    async def close(self):
        if self.connection:
            await self.connection.close()
            logger.info("Closed RabbitMQ connection")

    async def publish_event(self, routing_key: str, data: dict[str, Any]):
        if not self.channel:
            logger.error("Cannot publish event: channel is not open")
            return
            
        message = aio_pika.Message(
            body=json.dumps(data).encode("utf-8"),
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
            content_type="application/json",
        )
        await self.channel.default_exchange.publish(message, routing_key=routing_key)
        logger.info(f"Published event to {routing_key}")

rabbitmq_client = RabbitMQClient()

def setup_rabbitmq(app: FastAPI):
    @app.on_event("startup")
    async def startup_event():
        await rabbitmq_client.connect()

    @app.on_event("shutdown")
    async def shutdown_event():
        await rabbitmq_client.close()

def get_rabbitmq_client() -> RabbitMQClient:
    return rabbitmq_client
