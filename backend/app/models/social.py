from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "shop_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User", back_populates="favorites")
    shop: Mapped["Shop"] = relationship("Shop", back_populates="favorites")


class Checkin(Base):
    __tablename__ = "checkins"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User", back_populates="checkins")
    shop: Mapped["Shop"] = relationship("Shop", back_populates="checkins")
