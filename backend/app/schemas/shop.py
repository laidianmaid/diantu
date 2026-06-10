from datetime import datetime
from pydantic import BaseModel
from app.models.shop import ShopStatus


class ShopCreate(BaseModel):
    name: str
    color: str = "gray"
    address: str
    description: str | None = None
    style: str | None = None
    type: str | None = None
    status: ShopStatus = ShopStatus.open
    hours: dict | None = None


class ShopUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    address: str | None = None
    description: str | None = None
    style: str | None = None
    type: str | None = None
    status: ShopStatus | None = None
    hours: dict | None = None


class ShopOut(BaseModel):
    id: int
    name: str
    color: str
    address: str
    lat: float | None
    lng: float | None
    description: str | None
    style: str | None
    type: str | None
    status: ShopStatus
    hours: dict | None
    score: float
    owner_id: int | None
    created_at: datetime
    photo_urls: list[str] = []
    checkin_count: int = 0
    favorite_count: int = 0

    model_config = {"from_attributes": True}


class ShopListOut(BaseModel):
    id: int
    name: str
    color: str
    lat: float | None
    lng: float | None
    status: ShopStatus
    score: float

    model_config = {"from_attributes": True}
