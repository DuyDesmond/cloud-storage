import asyncpg
from typing import AsyncGenerator
from app.core.config import settings

# Global connection pool reference
pool: asyncpg.Pool | None = None


async def init_db_pool() -> None:
    """Initializes the asyncpg connection pool on application startup."""
    global pool
    try:
        pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=2,
            max_size=10,
            timeout=30.0,
            command_timeout=60.0,
        )
        print(" Neon PostgreSQL connection pool initialized.")
    except Exception as e:
        print(f" Failed to connect to database: {e}")
        raise e


async def close_db_pool() -> None:
    """Closes the connection pool gracefully on app shutdown."""
    global pool
    if pool:
        await pool.close()
        print(" Connection pool closed.")


async def get_db_connection() -> AsyncGenerator:
    if pool is None:
        raise RuntimeError("Database connection pool is not initialized.")

    async with pool.acquire() as connection:
        yield connection