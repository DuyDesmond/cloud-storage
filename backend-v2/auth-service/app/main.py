import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db_pool, close_db_pool, pool
from app.core.redis import init_redis, close_redis
from app.modules.auth.models import CREATE_USERS_TABLE_SQL
from app.modules.auth.router import router as auth_router
from app.modules.auth.internal_router import router as internal_router
from app.core.rabbitmq import rabbitmq_client

logger = logging.getLogger(__name__)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB Pool and ensure table exists
    await init_db_pool()
    await init_redis()
    await rabbitmq_client.connect()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(CREATE_USERS_TABLE_SQL)
        print("Database tables verified / created.")

    yield

    # Shutdown: Close DB Pool
    await rabbitmq_client.close()
    await close_db_pool()
    await close_redis()


from app.core.rate_limit import setup_rate_limiting

app = FastAPI(title=settings.PROJECT_NAME + " - Auth Service", lifespan=lifespan)
setup_rate_limiting(app)

# Register routes
app.include_router(auth_router, prefix=settings.API_STR)

app.include_router(internal_router)

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
    return {"status": "ok", "project": settings.PROJECT_NAME, "service": "auth"}