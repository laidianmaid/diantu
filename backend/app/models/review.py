import enum
from datetime import datetime, timezone
from sqlalchemy import String, Float, Enum, DateTime, ForeignKey, Integer, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ReviewPlatform(str, enum.Enum):
    native = "native"
    meituan = "meituan"
    baidu = "baidu"
    gaode = "gaode"


class ReactionType(str, enum.Enum):
    like = "like"
    dislike = "dislike"


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    content: Mapped[str] = mapped_column(String(4096))
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    platform: Mapped[ReviewPlatform] = mapped_column(Enum(ReviewPlatform), default=ReviewPlatform.native)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("reviews.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    shop: Mapped["Shop"] = relationship("Shop", back_populates="reviews")
    user: Mapped["User"] = relationship("User", back_populates="reviews")
    reactions: Mapped[list["ReviewReaction"]] = relationship("ReviewReaction", back_populates="review", cascade="all, delete-orphan")
    replies: Mapped[list["Review"]] = relationship("Review", foreign_keys=[parent_id])


class ReviewReaction(Base):
    __tablename__ = "review_reactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("reviews.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[ReactionType] = mapped_column(Enum(ReactionType))

    review: Mapped["Review"] = relationship("Review", back_populates="reactions")
    user: Mapped["User"] = relationship("User")
