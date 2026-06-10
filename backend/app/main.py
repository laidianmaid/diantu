from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
import app.models  # noqa: F401 — ensures models are registered before create_all

from app.routers import auth, users, shops, reviews, ai, amap_proxy


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _create_superadmin_if_needed()
    yield


async def _create_superadmin_if_needed():
    import os
    from sqlalchemy import select
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    email = os.getenv("SUPERADMIN_EMAIL", "admin@diantu.local")
    password = os.getenv("SUPERADMIN_PASSWORD", "changeme123")
    username = os.getenv("SUPERADMIN_USERNAME", "superadmin")

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.role == UserRole.superadmin))
        if result.scalar_one_or_none():
            return
        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role=UserRole.superadmin,
        )
        db.add(user)
        await db.commit()


app = FastAPI(
    title=settings.app_name,
    description="来点妹抖吗？ RESTful API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_PREFIX = "/api/v1"
app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(users.router, prefix=API_PREFIX)
app.include_router(shops.router, prefix=API_PREFIX)
app.include_router(reviews.router, prefix=API_PREFIX)
app.include_router(ai.router, prefix=API_PREFIX)
app.include_router(amap_proxy.router)  # 无 API_PREFIX，路径为 /_AMapService/...


@app.get("/")
async def root():
    return {"message": settings.app_name, "docs": "/docs"}
