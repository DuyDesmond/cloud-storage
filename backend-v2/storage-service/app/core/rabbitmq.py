import asyncio
import json
import logging
from typing import Callable, Awaitable, Any
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
        logger.info("Connected to RabbitMQ in storage-service")

    async def close(self):
        if self.connection:
            await self.connection.close()
            logger.info("Closed RabbitMQ connection")
            
    async def consume(self, queue_name: str, handler: Callable[[dict[str, Any]], Awaitable[None]]):
        if not self.channel:
            raise Exception("RabbitMQ channel not initialized")
            
        queue = await self.channel.declare_queue(queue_name, durable=True)
        
        async def _process_message(message: aio_pika.abc.AbstractIncomingMessage):
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    await handler(data)
                except Exception as e:
                    logger.exception(f"Error processing message from {queue_name}: {e}")
                    raise

        await queue.consume(_process_message)
        logger.info(f"Started consuming from {queue_name}")

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
