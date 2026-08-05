import asyncio
from datetime import datetime, timedelta, timezone
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]
sys.path.append(str(PROJECT_ROOT))

from app.core import database
from app.modules.files import queries as file_queries
from app.modules.files.repository import FileOperationsRepository
from app.modules.files.service import R2StorageGateway


RETENTION_DAYS = int(os.getenv("TRASH_RETENTION_DAYS", "30"))


async def purge_trashed():
    await database.init_db_pool()
    repo = FileOperationsRepository()
    storage = R2StorageGateway()

    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)

    try:
        async with database.pool.acquire() as conn:
            # 1) Purge trashed files: attempt synchronous deletion with retries, only remove DB row on success
            files = await repo.list_trashed_files_before(conn, cutoff)
            print(f"Found {len(files)} trashed files eligible for hard-delete (before {cutoff.isoformat()}).")
            for f in files:
                file_id = f["id"]
                storage_key = f.get("storage_key")
                try:
                    if storage_key:
                        last_exc = None
                        for attempt in range(1, 4):
                            try:
                                await storage.delete_object(storage_key)
                                last_exc = None
                                break
                            except Exception as exc:
                                last_exc = exc
                                await asyncio.sleep(0.5 * attempt)

                        if last_exc is not None:
                            print(f"Failed to delete object {storage_key} for file {file_id}: {last_exc}")
                            continue

                    async with conn.transaction():
                        deleted = await repo.delete_file_by_id(conn, file_id)
                        if deleted:
                            print(f"Deleted DB row for file {file_id}")
                        else:
                            print(f"No DB row deleted for file {file_id}")
                except Exception as exc:
                    print(f"Error deleting file {file_id}: {exc}")

            # 2) Purge trashed folders: attempt to delete files under each folder, then delete folder rows
            folders = await repo.list_trashed_folders_before(conn, cutoff)
            print(f"Found {len(folders)} trashed folders eligible for hard-delete.")
            for fld in folders:
                folder_id = fld["id"]
                folder_path = fld.get("path")
                try:
                    # delete files under this folder path
                    files_under = await repo.list_files_under_path(conn, folder_path)
                    skip_folder = False
                    for f in files_under:
                        storage_key = f.get("storage_key")
                        if not storage_key:
                            continue
                        last_exc = None
                        for attempt in range(1, 4):
                            try:
                                await storage.delete_object(storage_key)
                                last_exc = None
                                break
                            except Exception as exc:
                                last_exc = exc
                                await asyncio.sleep(0.5 * attempt)

                        if last_exc is not None:
                            print(f"Failed to delete object {storage_key} under folder {folder_id}: {last_exc}")
                            skip_folder = True
                            break

                    if skip_folder:
                        continue

                    # now delete the folder row itself and any files under path
                    async with conn.transaction():
                        await repo.delete_files_under_path(conn, folder_path)
                        await repo.delete_folders_under_path(conn, folder_path)
                        print(f"Deleted folder {folder_id} and its contents")
                except Exception as exc:
                    print(f"Error processing folder {folder_id}: {exc}")

    finally:
        await database.close_db_pool()


if __name__ == "__main__":
    asyncio.run(purge_trashed())
