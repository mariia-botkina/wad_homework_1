import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
import uuid
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user import User
from app.config import settings

REFRESH_TOKEN_PREFIX = "refresh_token:"
OAUTH_STATE_PREFIX = "oauth_state:"

class AuthService:
    def hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    def verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    
    def create_access_token(self, user_id: int) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {"sub": str(user_id), "exp": expire, "type": "access"}
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    def create_refresh_token(self) -> str:
        return str(uuid.uuid4())
    
    def decode_access_token(self, token: str) -> Optional[int]:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            if payload.get("type") != "access":
                return None
            return int(payload["sub"])
        except jwt.PyJWTError:
            return None
    
    async def store_refresh_token(self, redis, user_id: int, refresh_token: str):
        key = f"{REFRESH_TOKEN_PREFIX}{refresh_token}"
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
        await redis.setex(key, ttl, str(user_id))
    
    async def get_user_id_from_refresh_token(self, redis, refresh_token: str) -> Optional[int]:
        key = f"{REFRESH_TOKEN_PREFIX}{refresh_token}"
        value = await redis.get(key)
        if value:
            return int(value)
        return None
    
    async def delete_refresh_token(self, redis, refresh_token: str):
        key = f"{REFRESH_TOKEN_PREFIX}{refresh_token}"
        await redis.delete(key)

    async def generate_oauth_state(self, redis) -> str:
        state = str(uuid.uuid4())
        key = f"{OAUTH_STATE_PREFIX}{state}"
        await redis.setex(key, 600, "1")
        return state

    async def validate_oauth_state(self, redis, state: str) -> bool:
        key = f"{OAUTH_STATE_PREFIX}{state}"
        value = await redis.get(key)
        if not value:
            return False
        await redis.delete(key)
        return True
    
    async def register(self, db: AsyncSession, username: str, password: str, email: Optional[str] = None) -> User:
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            raise ValueError("Username already taken")
        
        hashed = self.hash_password(password)
        user = User(username=username, hashed_password=hashed, email=email)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def login(self, db: AsyncSession, username: str, password: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user or not user.hashed_password:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user
    
    async def get_github_access_token(self, code: str) -> Optional[str]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                },
                headers={"Accept": "application/json"},
            )
            data = response.json()
            return data.get("access_token")
    
    async def get_github_user(self, access_token: str) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            if response.status_code == 200:
                return response.json()
            return None
    
    async def get_or_create_github_user(self, db: AsyncSession, github_user: dict) -> User:
        github_id = str(github_user["id"])
        username = github_user.get("login", f"github_{github_id}")
        email = github_user.get("email")
        
        result = await db.execute(select(User).where(User.github_id == github_id))
        user = result.scalar_one_or_none()
        if user:
            return user
        
        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none():
            username = f"{username}_{github_id}"
        
        user = User(username=username, email=email, github_id=github_id)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user

auth_service = AuthService()
