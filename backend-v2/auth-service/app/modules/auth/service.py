import secrets
import asyncpg
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Response, Depends, status
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_token, decode_token
from app.core.redis import redis_client
from app.modules.auth.repository import AuthRepository
from app.modules.auth import schemas

class AuthService:

    def __init__(self, repo: AuthRepository = Depends()):
        # Default to real repository if none is passed
        self.repo = repo

    @staticmethod
    def _set_token_cookies(response: Response, user_id: str) -> None:
        """Helper to create and attach HttpOnly access and refresh cookies."""
        access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE)
        refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE)

        access_token = create_token({"sub": str(user_id), "type": "access"}, access_expires)
        refresh_token = create_token({"sub": str(user_id), "type": "refresh"}, refresh_expires)

        # Set Access Token Cookie
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=int(access_expires.total_seconds()),
        )

        # Set Refresh Token Cookie
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=int(refresh_expires.total_seconds()),
        )

    async def register_user(
        self,
        conn: asyncpg.Connection,
        payload: schemas.UserRegisterRequest,
        response: Response,
    ) -> schemas.UserResponse:
        # Check if user exists using injected repo instance
        existing_user = await self.repo.get_by_email(conn, payload.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already registered.",
            )

        hashed_pwd = hash_password(payload.password)
        
        # Save user using injected repo instance
        new_user = await self.repo.create_user(
            conn, payload.email, hashed_pwd, payload.full_name
        )

        self._set_token_cookies(response, str(new_user["id"]))
        return schemas.UserResponse(**new_user)

    async def login_user(
        self,
        conn: asyncpg.Connection, credentials: schemas.UserLoginRequest, response: Response
    ) -> schemas.UserResponse:
        user = await self.repo.get_by_email(conn, credentials.email)
        if not user or not verify_password(credentials.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
            )

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive.",
            )

        # Attach HttpOnly JWT Cookies
        self._set_token_cookies(response, str(user["id"]))

        return schemas.UserResponse(**user)

    async def refresh_session(self, conn: asyncpg.Connection, refresh_token: str, response: Response) -> schemas.UserResponse:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
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

        user = await self.repo.get_by_id(conn, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found.",
            )

        self._set_token_cookies(response, str(user["id"]))

        return schemas.UserResponse(**user)

    async def _revoke_tokens(self, user_id: str) -> None:
        """Revokes all active tokens for a user by recording the revocation time in Redis."""
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if redis_client:
            await redis_client.set(f"revoked:user:{user_id}", now_ts, ex=settings.REFRESH_TOKEN_EXPIRE * 86400)

    async def logout_user(self, user_id: uuid.UUID, response: Response) -> dict:
        """Clears auth cookies on logout."""
        response.delete_cookie(key="access_token")
        response.delete_cookie(key="refresh_token")
        await self._revoke_tokens(str(user_id))
        return {"message": "Successfully logged out"}

    async def delete_account(self, conn: asyncpg.Connection, user_id: uuid.UUID, response: Response) -> dict:
        deleted = await self.repo.delete_user(conn, user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        # Publish UserDeletedEvent to Redis
        if redis_client:
            import json
            await redis_client.publish(
                "events:user_deleted", 
                json.dumps({"user_id": str(user_id)})
            )

        # Clear active session cookies and revoke tokens
        await self.logout_user(user_id, response)

        return {"message": "Account successfully deleted."}

    async def request_password_reset(self, conn: asyncpg.Connection, data: schemas.ForgotPasswordRequest) -> dict:
        user = await self.repo.get_by_email(conn, data.email)
        if not user:
            return {"message": "If that email is registered, a password reset link has been sent."}

        # Generate secure random token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        await self.repo.create_reset_token(conn, user["id"], reset_token, expires_at)

        # TODO: Integrate Email Service (Resend/SMTP) here
        # E.g., await send_reset_email(user["email"], reset_token)
        print(f" RESET TOKEN for {user['email']}: {reset_token}")

        return {"message": "If that email is registered, a password reset link has been sent."}

    async def reset_password(self, conn: asyncpg.Connection, data: schemas.ResetPasswordRequest) -> dict:
        token_record = await self.repo.get_valid_reset_token(conn, data.token)
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token.",
            )

        new_hashed_password = hash_password(data.new_password)
        await self.repo.update_password_and_invalidate_token(
            conn,
            user_id=token_record["user_id"],
            new_hashed_password=new_hashed_password,
            token_id=token_record["id"],
        )
        
        await self._revoke_tokens(str(token_record["user_id"]))

        return {"message": "Password successfully reset. You can now log in with your new password."}

    async def change_password(
        self,
        conn: asyncpg.Connection,
        user_id: uuid.UUID,
        payload: schemas.ChangePasswordRequest,
    ) -> dict:
        current_hashed_password = await self.repo.get_password_by_id(conn, user_id)
        if not current_hashed_password:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        # 1. Verify current password
        if not verify_password(payload.current_password, current_hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password.",
            )

        # 2. Hash and update new password
        new_hashed = hash_password(payload.new_password)
        await self.repo.update_password(conn, user_id, new_hashed)
        
        await self._revoke_tokens(str(user_id))

        return {"message": "Password updated successfully."}