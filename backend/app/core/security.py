import secrets
from datetime import datetime, timedelta, timezone

from jose import jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(sub: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": sub, "exp": expire, "type": "access"}, settings.secret_key, ALGORITHM)


def create_refresh_token(sub: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    return jwt.encode({"sub": sub, "exp": expire, "type": "refresh"}, settings.secret_key, ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


def generate_api_key() -> str:
    return "dk_" + secrets.token_urlsafe(32)
