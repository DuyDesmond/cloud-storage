import asyncpg
from fastapi import APIRouter, Depends, Request, Response, status, HTTPException
from app.core.database import get_db_connection
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.service import AuthService
from app.modules.auth import schemas
from app.core.rate_limit import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

def set_auth_cookies(response: Response, tokens: dict) -> None:
    response.set_cookie(
        key="access_token",
        value=tokens["access_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=tokens["access_expires_seconds"],
    )
    response.set_cookie(
        key="refresh_token",
        value=tokens["refresh_token"],
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=tokens["refresh_expires_seconds"],
    )

@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    payload: schemas.UserRegisterRequest,
    response: Response,
    auth_service: AuthService = Depends(AuthService),
):
    user, tokens = await auth_service.register_user(payload)
    set_auth_cookies(response, tokens)
    return user

@router.post("/login", response_model=schemas.UserResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    payload: schemas.UserLoginRequest,
    response: Response,
    auth_service: AuthService = Depends(AuthService),
):
    user, tokens = await auth_service.login_user(payload)
    set_auth_cookies(response, tokens)
    return user


@router.post("/refresh", response_model=schemas.UserResponse)
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(AuthService),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    user, tokens = await auth_service.refresh_session(refresh_token)
    set_auth_cookies(response, tokens)
    return user


@router.post("/logout")
@limiter.limit("10/minute")
async def logout(
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(AuthService),
):
    res = await auth_service.logout_user(current_user["id"])
    response.delete_cookie(key="access_token", httponly=True, secure=True, samesite="lax")
    response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="lax")
    return res


@router.get("/me", response_model=schemas.UserResponse)
@limiter.limit("10/minute")
async def get_me(request: Request, current_user: dict = Depends(get_current_user)):
    """Protected endpoint: Returns current user profile."""
    return schemas.UserResponse(**current_user)

@router.delete("/me", status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")
async def delete_me(
    request: Request,
    response: Response,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(AuthService),
):
    """Protected endpoint: Permanently deletes current user account."""
    res = await auth_service.delete_account(current_user["id"])
    response.delete_cookie(key="access_token", httponly=True, secure=True, samesite="lax")
    response.delete_cookie(key="refresh_token", httponly=True, secure=True, samesite="lax")
    return res

@router.post("/forgot-password", response_model=schemas.MessageResponse)
@limiter.limit("10/minute")
async def forgot_password(
    request: Request,
    payload: schemas.ForgotPasswordRequest,
    auth_service: AuthService = Depends(AuthService),
):
    """Requests a password reset link for a given email address."""
    return await auth_service.request_password_reset(payload)


@router.post("/reset-password", response_model=schemas.MessageResponse)
@limiter.limit("10/minute")
async def reset_password(
    request: Request,
    payload: schemas.ResetPasswordRequest,
    auth_service: AuthService = Depends(AuthService),
):
    """Resets user password using a valid reset token."""
    return await auth_service.reset_password(payload)

@router.put("/change-password", response_model=schemas.MessageResponse)
@limiter.limit("10/minute")
async def change_password(
    request: Request,
    payload: schemas.ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    auth_service: AuthService = Depends(AuthService),
):
    """Protected endpoint: Allows logged-in users to update their password."""
    return await auth_service.change_password(current_user["id"], payload)