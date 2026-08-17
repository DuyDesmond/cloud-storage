from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.core.database import init_db_pool, close_db_pool, pool
from app.modules.auth.models import CREATE_USERS_TABLE_SQL
from app.modules.auth.router import router as auth_router
from app.modules.files.models import get_file_operations_tables_sql
from app.modules.files.router import router as file_operations_router
from app.modules.share.router import router as share_router
from fastapi.middleware.cors import CORSMiddleware
import app.modules.auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize DB Pool and ensure table exists
    await init_db_pool()
    if pool:
        async with pool.acquire() as conn:
            await conn.execute(CREATE_USERS_TABLE_SQL + "\n" + get_file_operations_tables_sql())
        print("Database tables verified / created.")

    yield

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