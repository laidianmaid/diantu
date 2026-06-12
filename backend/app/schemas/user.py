from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole
from app.models.shop import ShopStatus


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


class UserFavoriteShopOut(BaseModel):
    shop_id: int
    shop_name: str
    address: str
    color: str
    style: str | None
    type: str | None
    status: ShopStatus
    score: float
    lat: float | None
    lng: float | None
    favorited_at: datetime


class UserCheckinShopOut(BaseModel):
    shop_id: int
    shop_name: str
    address: str
    color: str
    style: str | None
    type: str | None
    status: ShopStatus
    score: float
    lat: float | None
    lng: float | None
    checked_in_at: datetime


class UserReviewHistoryOut(BaseModel):
    review_id: int
    shop_id: int
    shop_name: str
    shop_color: str
    shop_style: str | None
    shop_type: str | None
    shop_status: ShopStatus
    shop_score: float
    content: str
    score: float | None
    created_at: datetime
