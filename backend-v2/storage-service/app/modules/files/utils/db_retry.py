from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from app.core.exceptions import DuplicateRecordError, InvalidOperationError, InfrastructureError

def _should_retry(e: BaseException) -> bool:
    if isinstance(e, (DuplicateRecordError, InvalidOperationError)):
        return True
    if isinstance(e, InfrastructureError) and "deadlock" in str(e).lower():
        return True
    return False

async def with_db_retry(fn, max_attempts: int = 3, base_delay: float = 0.1):
    @retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=base_delay, min=base_delay),
        retry=retry_if_exception(_should_retry),
        reraise=True
    )
    async def _retry_wrapper():
        return await fn()
        
    return await _retry_wrapper()
