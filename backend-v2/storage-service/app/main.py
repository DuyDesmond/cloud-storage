import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db_pool, close_db_pool, pool
from app.core.redis import init_redis, close_redis
from app.modules.files.models import get_file_operations_tables_sql
from app.modules.files.router import router as file_operations_router
from app.modules.share.router import router as share_router
from app.core.rate_limit import setup_rate_limiting

import asyncio
from app.core.events import listen_for_events
from app.core.rabbitmq import rabbitmq_client
from app.core.jobs import process_deletion_jobs

logger = logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB Pool and ensure table exists
    await init_db_pool()
    await init_redis()
    await rabbitmq_client.connect()
    
    if pool:
        async with pool.acquire() as conn:
            # Note: storage-service only initializes its own tables
            await conn.execute(get_file_operations_tables_sql())
        print("Database tables verified / created.")

    # Start listening to events and jobs
    app.state.event_task = asyncio.create_task(listen_for_events())
    
    app.state.job_task = asyncio.create_task(process_deletion_jobs())

    yield

    # Shutdown: Close DB Pool
    await rabbitmq_client.close()
    await close_db_pool()
    await close_redis()

app = FastAPI(title=settings.PROJECT_NAME + " - Storage Service", lifespan=lifespan)
setup_rate_limiting(app)

# Register routes
app.include_router(file_operations_router, prefix=settings.API_STR)
app.include_router(share_router, prefix=settings.API_STR)

import os

cors_origins_str = os.getenv("CORS_ORIGINS", "http://localhost:4200")
cors_origins = [origin.strip() for origin in cors_origins_str.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME, "service": "storage"}