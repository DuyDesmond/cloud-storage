import asyncpg
import uuid
from typing import Optional, Any
from app.core import queries

class CoreRepository:
    def __init__(self, conn: asyncpg.Connection):
        self.conn = conn

    async def upsert_user(self, user_id: uuid.UUID, email: str, full_name: str) -> None:
        await self.conn.execute(queries.UPSERT_USER, user_id, email, full_name)

    async def insert_deletion_job(self, user_id: uuid.UUID) -> None:
        await self.conn.execute(queries.INSERT_DELETION_JOB, user_id)

    async def fetch_pending_job(self) -> Optional[dict[str, Any]]:
        row = await self.conn.fetchrow(queries.FETCH_PENDING_JOB)
        return dict(row) if row else None

    async def mark_job_processing(self, user_id: uuid.UUID) -> None:
        await self.conn.execute(queries.MARK_JOB_PROCESSING, user_id)

    async def delete_user(self, user_id: uuid.UUID) -> None:
        await self.conn.execute(queries.DELETE_USER, user_id)

    async def delete_job(self, user_id: uuid.UUID) -> None:
        await self.conn.execute(queries.DELETE_JOB, user_id)

    async def requeue_job(self, user_id: uuid.UUID, retry_count: int) -> None:
        seconds = min(60 * (2 ** retry_count), 3600)
        interval = f"{seconds} seconds"
        await self.conn.execute(queries.REQUEUE_JOB, user_id, interval)
