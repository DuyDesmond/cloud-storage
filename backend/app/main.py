import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.core.config import settings
from app.core.database import init_db_pool, close_db_pool, pool
from app.modules.auth.models import CREATE_USERS_TABLE_SQL
from app.modules.auth.router import router as auth_router
from app.modules.files.models import get_file_operations_tables_sql
from app.modules.files.router import router as file_operations_router
from app.modules.share.router import router as share_router
from app.modules.files.purge_trashed import run_purge_job
import app.modules.auth

logger = logging.getLogger(__name__)

# Initialize AsyncIOScheduler
scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB Pool and ensure table exists
    await init_db_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(CREATE_USERS_TABLE_SQL + "\n" + get_file_operations_tables_sql())
        print("Database tables verified / created.")

    # Schedule the trash purge job to run daily at 02:00 AM UTC
    # 'args' passes RETENTION_DAYS to run_purge_job(retention_days=30)
    scheduler.add_job(
        run_purge_job,
        trigger="cron",
        hour=2,
        minute=0,
        args=[20],
        id="purge_trashed_job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("APScheduler started: Daily trash purge job scheduled at 02:00 AM UTC.")

    yield

    scheduler.shutdown()
    logger.info("APScheduler shut down.")

    # Shutdown: Close DB Pool
    await close_db_pool()


app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# Register routes
app.include_router(auth_router, prefix=settings.API_STR)
app.include_router(file_operations_router, prefix=settings.API_STR)
app.include_router(share_router, prefix=settings.API_STR)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}