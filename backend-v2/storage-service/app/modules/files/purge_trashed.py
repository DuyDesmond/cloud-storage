import asyncio
from datetime import datetime, timedelta, timezone
import logging
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.core import database
from app.modules.files.repositories.trash_repository import TrashRepository
from app.modules.files.repositories.file_query_repository import FileQueryRepository
from app.core.object_bucket import R2StorageGateway, StorageGateway

logger = logging.getLogger("purge_trashed")
RETENTION_DAYS = int(os.getenv("TRASH_RETENTION_DAYS", "20"))


async def _delete_r2_object_with_retry(storage: StorageGateway, storage_key: str, max_retries: int = 3) -> bool:
    """Helper to handle Cloudflare R2 object deletion with exponential backoff retries."""
    for attempt in range(1, max_retries + 1):
        try:
            await storage.delete_object(storage_key)
            return True
        except Exception as exc:
            logger.warning(f"Attempt {attempt}/{max_retries} failed deleting {storage_key}: {exc}")
            if attempt < max_retries:
                await asyncio.sleep(0.5 * attempt)
    return False


async def run_purge_job(retention_days: int = RETENTION_DAYS):
    """
    Main job function called by APScheduler or CLI runner.
    Scans and permanently purges expired trashed files and folders.
    """
    if database.pool is None:
        logger.error("Database pool is not initialized.")
        return

    storage = R2StorageGateway()
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    logger.info(f"Starting purge job for items trashed before {cutoff.isoformat()} ({retention_days} days retention)")

    async with database.pool.acquire() as conn:
        trash_repo = TrashRepository(conn)
        query_repo = FileQueryRepository(conn)
        
        # 1. Purge individual trashed files
        files = await trash_repo.list_trashed_files_before(cutoff)
        logger.info(f"Found {len(files)} trashed files eligible for hard-delete.")

        for f in files:
            file_id = f["id"]
            storage_key = f.get("storage_key")

            if storage_key:
                success = await _delete_r2_object_with_retry(storage, storage_key)
                if not success:
                    logger.error(f"Skipping DB deletion for file {file_id}; storage object {storage_key} failed to delete.")
                    continue

            # Isolated short transaction per DB deletion
            async with conn.transaction():
                deleted = await trash_repo.delete_file_by_id(file_id)
                if deleted:
                    logger.info(f"Purged DB record for file {file_id}")
                else:
                    logger.warning(f"No DB record found to delete for file {file_id}")

        # 2. Purge trashed Folders + child
        folders = await trash_repo.list_trashed_folders_before(cutoff)
        logger.info(f"Found {len(folders)} trashed folders eligible for hard-delete.")

        for fld in folders:
            folder_id = fld["id"]
            folder_path = fld.get("path")
            
            if not folder_path:
                continue

            files_under = await query_repo.list_files_under_path(folder_path)
            skip_folder = False

            # Delete physical storage for all child files in folder hierarchy
            for f in files_under:
                storage_key = f.get("storage_key")
                if not storage_key:
                    continue

                success = await _delete_r2_object_with_retry(storage, storage_key)
                if not success:
                    logger.error(f"Failed deleting child object {storage_key} under folder {folder_id}. Aborting folder purge.")
                    skip_folder = True
                    break

            if skip_folder:
                continue

            # Remove directory hierarchy records in a single transactional unit
            async with conn.transaction():
                await trash_repo.delete_files_under_path(folder_path)
                await trash_repo.delete_folders_under_path(folder_path)
                logger.info(f"Purged folder {folder_id} and all nested contents from DB")


async def main():
    """Standalone CLI entrypoint with database pool lifecycle management."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    await database.init_db_pool()
    try:
        await run_purge_job()
    finally:
        await database.close_db_pool()


if __name__ == "__main__":
    asyncio.run(main())