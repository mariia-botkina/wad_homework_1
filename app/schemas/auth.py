from pydantic import BaseModel
from typing import Optional

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    github_id: Optional[str] = None
    
    class Config:
        from_attributes = True
