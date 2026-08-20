import uuid
from fastapi import HTTPException, Request, status
from app.core.security import decode_token

async def get_current_user(request: Request) -> dict:
    """FastAPI Dependency: Stateless JWT verification."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing.",
        )

    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    try:
        user_id = uuid.UUID(str(sub))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject identifier.",
        )

    # Check Redis for token revocation based on payload['iat']
    from app.core.redis import redis_client
    if redis_client:
        revoked_ts = await redis_client.get(f"revoked:user:{user_id}")
        if revoked_ts:
            iat = payload.get("iat", 0)
            if int(revoked_ts) > iat:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked.",
                )

    return {"id": user_id}
