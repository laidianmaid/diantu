from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.user


class UserLogin(BaseModel):
    email: str  # 登录时不做邮箱格式校验，直接匹配数据库
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    weight: float
    avatar_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ApiKeyOut(BaseModel):
    api_key: str
