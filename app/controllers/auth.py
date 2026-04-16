from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.redis_client import get_redis
from app.services.auth_service import auth_service
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshRequest, UserResponse
from app.dependencies import get_current_user
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db), redis=Depends(get_redis)):
    try:
        user = await auth_service.register(db, body.username, body.password, body.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    access_token = auth_service.create_access_token(user.id)
    refresh_token = auth_service.create_refresh_token()
    await auth_service.store_refresh_token(redis, user.id, refresh_token)
    
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db), redis=Depends(get_redis)):
    user = await auth_service.login(db, body.username, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = auth_service.create_access_token(user.id)
    refresh_token = auth_service.create_refresh_token()
    await auth_service.store_refresh_token(redis, user.id, refresh_token)
    
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, redis=Depends(get_redis)):
    user_id = await auth_service.get_user_id_from_refresh_token(redis, body.refresh_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    
    await auth_service.delete_refresh_token(redis, body.refresh_token)
    
    access_token = auth_service.create_access_token(user_id)
    new_refresh_token = auth_service.create_refresh_token()
    await auth_service.store_refresh_token(redis, user_id, new_refresh_token)
    
    return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)

@router.post("/logout")
async def logout(body: RefreshRequest, current_user: User = Depends(get_current_user), redis=Depends(get_redis)):
    user_id = await auth_service.get_user_id_from_refresh_token(redis, body.refresh_token)
    if not user_id or user_id != current_user.id:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    await auth_service.delete_refresh_token(redis, body.refresh_token)
    return {"message": "Logged out"}

@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/github")
async def github_login(redis=Depends(get_redis)):
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")
    state = await auth_service.generate_oauth_state(redis)
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
        f"&scope=user:email"
        f"&state={state}"
    )
    return RedirectResponse(url=url)

@router.get("/github/callback")
async def github_callback(code: str, state: str, db: AsyncSession = Depends(get_db), redis=Depends(get_redis)):
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(status_code=501, detail="GitHub OAuth not configured")

    if not await auth_service.validate_oauth_state(redis, state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    
    token = await auth_service.get_github_access_token(code)
    if not token:
        raise HTTPException(status_code=400, detail="Failed to get GitHub token")
    
    github_user = await auth_service.get_github_user(token)
    if not github_user:
        raise HTTPException(status_code=400, detail="Failed to get GitHub user")
    
    user = await auth_service.get_or_create_github_user(db, github_user)
    
    access_token = auth_service.create_access_token(user.id)
    refresh_token = auth_service.create_refresh_token()
    await auth_service.store_refresh_token(redis, user.id, refresh_token)
    
    frontend_url = settings.FRONTEND_URL
    return RedirectResponse(
        url=f"{frontend_url}/#/oauth?access_token={access_token}&refresh_token={refresh_token}"
    )
