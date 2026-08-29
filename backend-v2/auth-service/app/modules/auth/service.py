import secrets
import asyncpg
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends, status
from app.core.config import settings
from app.core.security import hash_password, verify_password, create_token, decode_token
from app.modules.auth.repository import AuthRepository
from app.modules.auth.cache import CacheRepository
from app.modules.auth import schemas

class AuthService:

    def __init__(self, repo: AuthRepository = Depends(), cache: CacheRepository = Depends()):
        self.repo = repo
        self.cache = cache

    @staticmethod
    def generate_tokens(user_id: str) -> dict:
        """Helper to create access and refresh tokens."""
        access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE)
        refresh_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE)

        access_token = create_token({"sub": str(user_id), "type": "access"}, access_expires)
        refresh_token = create_token({"sub": str(user_id), "type": "refresh"}, refresh_expires)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "access_expires_seconds": int(access_expires.total_seconds()),
            "refresh_expires_seconds": int(refresh_expires.total_seconds()),
        }

    async def register_user(
        self,
        payload: schemas.UserRegisterRequest,
    ) -> tuple[schemas.UserResponse, dict]:
        hashed_pwd = hash_password(payload.password)
        
        try:
            # Save user using injected repo instance
            new_user = await self.repo.create_user(
                payload.email, hashed_pwd, payload.full_name
            )
        except asyncpg.exceptions.UniqueViolationError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address already registered.",
            )

        tokens = self.generate_tokens(str(new_user["id"]))
        return schemas.UserResponse(**new_user), tokens

    async def login_user(
        self,
        credentials: schemas.UserLoginRequest
    ) -> tuple[schemas.UserResponse, dict]:
        user = await self.repo.get_by_email(credentials.email)
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

        tokens = self.generate_tokens(str(user["id"]))
        return schemas.UserResponse(**user), tokens

    async def refresh_session(self, refresh_token: str) -> tuple[schemas.UserResponse, dict]:
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

        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found.",
            )

        tokens = self.generate_tokens(str(user["id"]))
        return schemas.UserResponse(**user), tokens

    async def _revoke_tokens(self, user_id: str) -> None:
        """Revokes all active tokens for a user by recording the revocation time in Redis."""
        now_ts = int(datetime.now(timezone.utc).timestamp())
        await self.cache.revoke_user_tokens(user_id, now_ts)

    async def logout_user(self, user_id: uuid.UUID) -> dict:
        """Revokes tokens on logout."""
        await self._revoke_tokens(str(user_id))
        return {"message": "Successfully logged out"}

    async def delete_account(self, user_id: uuid.UUID) -> dict:
        deleted = await self.repo.delete_user(user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )

        # Publish UserDeletedEvent to Redis
        await self.cache.publish_user_deleted(str(user_id))

        # Delete user profile cache
        await self.cache.delete_user_profile(str(user_id))

        # Revoke tokens
        await self.logout_user(user_id)

        return {"message": "Account successfully deleted."}

    async def request_password_reset(self, data: schemas.ForgotPasswordRequest) -> dict:
        user = await self.repo.get_by_email(data.email)
        if not user:
            return {"message": "If that email is registered, a password reset link has been sent."}

        # Generate secure random token
        reset_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

        await self.repo.create_reset_token(user["id"], reset_token, expires_at)

        # TODO: Integrate Email Service (Resend/SMTP) here
        # E.g., await send_reset_email(user["email"], reset_token)

        return {"message": "If that email is registered, a password reset link has been sent."}

    async def reset_password(self, data: schemas.ResetPasswordRequest) -> dict:
        token_record = await self.repo.get_valid_reset_token(data.token)
        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token.",
            )

        new_hashed_password = hash_password(data.new_password)
        await self.repo.update_password_and_invalidate_token(
            user_id=token_record["user_id"],
            new_hashed_password=new_hashed_password,
            token_id=token_record["id"],
        )
        
        await self._revoke_tokens(str(token_record["user_id"]))
        await self.cache.delete_user_profile(str(token_record["user_id"]))

        return {"message": "Password successfully reset. You can now log in with your new password."}

    async def change_password(
        self,
        user_id: uuid.UUID,
        payload: schemas.ChangePasswordRequest,
    ) -> dict:
        current_hashed_password = await self.repo.get_password_by_id(user_id)
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
        await self.repo.update_password(user_id, new_hashed)
        
        await self._revoke_tokens(str(user_id))
        await self.cache.delete_user_profile(str(user_id))

        return {"message": "Password updated successfully."}