import asyncio
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]
sys.path.append(str(PROJECT_ROOT))
from app.core import database

async def apply_tables():
    await database.init_db_pool()

    if not database.pool:
        print(" Database database.pool is not available. Exiting.")
        return

    tables_file = SCRIPT_DIR / "design_tables.txt"
    if not tables_file.exists():
        print(f" Schema file '{tables_file.name}' not found.")
        await database.close_db_pool()
        return

    tables_sql = tables_file.read_text(encoding="utf-8")

    print("Executing tables script...")
    try:
        async with database.pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(tables_sql)

        print("Schema applied successfully!")

    except Exception as e:
        print(f" Error applying tables: {e}")
    finally:
        await database.close_db_pool()


if __name__ == "__main__":
    asyncio.run(apply_tables())