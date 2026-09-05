import asyncio
import logging
from app.core.database import get_pool
from app.modules.files.repositories import FileQueryRepository, TrashRepository
from app.core.object_bucket import R2StorageGateway
from app.core.config import settings
from app.core.repository import CoreRepository

logger = logging.getLogger(__name__)

async def process_deletion_jobs():
    logger.info("Started deletion job background worker")
    storage = R2StorageGateway()
    
    while True:
        try:
            pool = get_pool()
            if not pool:
                await asyncio.sleep(5)
                continue

            async with pool.acquire() as conn:
                repo = CoreRepository(conn)
                row = await repo.fetch_pending_job()
                
                if not row:
                    await asyncio.sleep(10)
                    continue

                user_id = row["user_id"]
                retry_count = row["retry_count"]
                logger.info(f"Processing deletion job for user {user_id} (Attempt {retry_count + 1})")
            
                await repo.mark_job_processing(user_id)

                try:
                    query_repo = FileQueryRepository(conn)
                    trash_repo = TrashRepository(conn)
                    files = await query_repo.list_files_by_owner(user_id)
                    
                    # 4. Batch delete from R2
                    storage_keys = [f.get("storage_key") for f in files if f.get("storage_key")]
                    if storage_keys:
                        await storage.batch_delete_objects(storage_keys)

                    await trash_repo.delete_all_user_data(user_id)
                    await repo.delete_user(user_id)
                    await repo.delete_job(user_id)
                    logger.info(f"Successfully processed deletion job for user {user_id}")

                except Exception as e:
                    logger.exception(f"Error processing deletion job for user {user_id}: {e}")
                    await repo.requeue_job(user_id, retry_count)

        except Exception as e:
            logger.error(f"Unexpected error in deletion job worker: {e}")
            await asyncio.sleep(5)
