import enum
from datetime import datetime, timezone
from sqlalchemy import String, Float, Enum, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    superadmin = "superadmin"
    admin = "admin"
    owner = "owner"
    user = "user"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.user)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    api_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    shops: Mapped[list["Shop"]] = relationship("Shop", back_populates="owner", foreign_keys="Shop.owner_id")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="user")
    favorites: Mapped[list["Favorite"]] = relationship("Favorite", back_populates="user")
    checkins: Mapped[list["Checkin"]] = relationship("Checkin", back_populates="user")
