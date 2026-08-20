from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# In a production environment with Redis, we'd use:
# from limits.storage import RedisStorage
# storage_uri = "redis://localhost:6379"
# limiter = Limiter(key_func=get_remote_address, storage_uri=storage_uri)

# For now, we use the default memory storage
limiter = Limiter(key_func=get_remote_address)

def setup_rate_limiting(app):
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
