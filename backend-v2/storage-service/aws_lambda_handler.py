import asyncio
import logging
from app.modules.files.purge_trashed import run_purge_job
from app.core import database

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    AWS Lambda entry point for periodic trash purging.
    Trigger this via AWS EventBridge (e.g. daily cron).
    """
    logger.info("Lambda execution started for trash purge.")
    
    async def _run():
        await database.init_db_pool()
        try:
            await run_purge_job()
        finally:
            await database.close_db_pool()

    # Create new event loop for Lambda execution
    loop = asyncio.get_event_loop()
    if loop.is_closed():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
    loop.run_until_complete(_run())
    
    logger.info("Lambda execution completed.")
    return {
        'statusCode': 200,
        'body': 'Purge job completed successfully'
    }
