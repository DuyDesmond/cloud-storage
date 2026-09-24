import asyncio
import logging
import uuid
from typing import Any
from app.core.database import get_pool
from app.core.rabbitmq import get_rabbitmq_client
from app.core.repository import CoreRepository

logger = logging.getLogger(__name__)

async def handle_user_created(data: dict[str, Any]):
    logger.info(f"Handling user created event: {data}")
    pool = get_pool()
    if pool:
        async with pool.acquire() as conn:
            repo = CoreRepository(conn)
            await repo.upsert_user(uuid.UUID(data["id"]), data["email"], data["full_name"])

async def handle_user_deleted(data: dict[str, Any]):
    user_id = data.get("user_id")
    if not user_id:
        return
        
    logger.info(f"Handling user deleted event for user {user_id}")
    pool = get_pool()
    if pool:
        async with pool.acquire() as conn:
            repo = CoreRepository(conn)
            await repo.insert_deletion_job(uuid.UUID(user_id))

async def listen_for_events():
    rabbitmq = get_rabbitmq_client()
    await asyncio.sleep(2)
    
    try:        
        if not rabbitmq.channel:
            return

        exchange = rabbitmq.channel.default_exchange
        
        async def on_user_created(data):
            await handle_user_created(data)
            
        async def on_user_deleted(data):
            await handle_user_deleted(data)
    
        await rabbitmq.consume("events.user.created", on_user_created)
        await rabbitmq.consume("events.user.deleted", on_user_deleted)
        
    except Exception as e:
        logger.error(f"Failed to setup event listeners: {e}")
