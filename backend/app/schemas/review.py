from datetime import datetime
from pydantic import BaseModel, Field
from app.models.review import ReviewPlatform, ReactionType


class ReviewCreate(BaseModel):
    content: str
    score: float | None = Field(None, ge=1, le=5)
    parent_id: int | None = None


class ReviewOut(BaseModel):
    id: int
    shop_id: int
    user_id: int
    username: str = ""
    content: str
    score: float | None
    platform: ReviewPlatform
    parent_id: int | None
    created_at: datetime
    likes: int = 0
    dislikes: int = 0
    replies: list["ReviewOut"] = []

    model_config = {"from_attributes": True}


ReviewOut.model_rebuild()


class ReactionCreate(BaseModel):
    type: ReactionType
