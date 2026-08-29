import asyncio
import json
import logging
import uuid
from app.core.redis import get_redis_client
from app.core.database import get_pool
from app.modules.files.repository import FileOperationsRepository
from app.modules.files.service import R2StorageGateway

logger = logging.getLogger(__name__)

async def handle_user_deleted(user_id: str):
    logger.info(f"Handling user deleted event for user {user_id}")
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        return

    storage = R2StorageGateway()
    pool = get_pool()
    if pool:
        async with pool.acquire() as conn:
            repo = FileOperationsRepository(conn)
            # 1. Delete actual files from R2
            try:
                files = await repo.list_files_by_owner(uid)
                for f in files:
                    sk = f.get("storage_key")
                    if sk:
                        try:
                            # Strict blob-first deletion implies deleting from blob before DB
                            await storage.delete_object(sk)
                        except Exception as e:
                            logger.exception(f"Failed to delete object {sk}: {e}")
            except Exception as e:
                logger.exception(f"Error fetching files for deleted user {uid}: {e}")

            # 2. Delete all user data from storage DB
            try:
                await repo.delete_all_user_data(uid)
            except Exception as e:
                logger.exception(f"Error deleting user data for {uid}: {e}")

async def listen_for_events():
    redis_client = get_redis_client()
    if not redis_client:
        return
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("events:user_deleted")
    logger.info("Subscribed to events:user_deleted")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                user_id = data.get("user_id")
                if user_id:
                    asyncio.create_task(handle_user_deleted(user_id))
    except asyncio.CancelledError:
        logger.info("Event listener cancelled")
    finally:
        await pubsub.unsubscribe()
