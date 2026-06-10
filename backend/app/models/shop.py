import enum
from datetime import datetime, timezone
from sqlalchemy import String, Float, Enum, DateTime, ForeignKey, Boolean, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ShopStatus(str, enum.Enum):
    open = "open"
    closed = "closed"
    preparing = "preparing"
    shutdown = "shutdown"


class Shop(Base):
    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    color: Mapped[str] = mapped_column(String(32), default="gray")
    address: Mapped[str] = mapped_column(String(512))
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    style: Mapped[str | None] = mapped_column(String(64), nullable=True)
    type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[ShopStatus] = mapped_column(Enum(ShopStatus), default=ShopStatus.open)
    hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    owner: Mapped["User | None"] = relationship("User", back_populates="shops", foreign_keys=[owner_id])
    photos: Mapped[list["ShopPhoto"]] = relationship("ShopPhoto", back_populates="shop", cascade="all, delete-orphan")
    staff: Mapped[list["ShopStaff"]] = relationship("ShopStaff", back_populates="shop", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship("Review", back_populates="shop", cascade="all, delete-orphan")
    favorites: Mapped[list["Favorite"]] = relationship("Favorite", back_populates="shop", cascade="all, delete-orphan")
    checkins: Mapped[list["Checkin"]] = relationship("Checkin", back_populates="shop", cascade="all, delete-orphan")


class ShopPhoto(Base):
    __tablename__ = "shop_photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    url: Mapped[str] = mapped_column(String(512))
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    shop: Mapped["Shop"] = relationship("Shop", back_populates="photos")


class ShopStaff(Base):
    __tablename__ = "shop_staff"

    id: Mapped[int] = mapped_column(primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    is_today: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    shop: Mapped["Shop"] = relationship("Shop", back_populates="staff")
    user: Mapped["User"] = relationship("User")
