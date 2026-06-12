import asyncio
from collections import defaultdict, deque
from time import monotonic

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User, UserRole

bearer = HTTPBearer(auto_error=False)
_rate_limit_buckets: dict[str, deque[float]] = defaultdict(deque)
_rate_limit_lock = asyncio.Lock()


@dataclass
class AuthContext:
    user: User | None
    access_token: str | None = None


async def _resolve_auth_context(
    creds: HTTPAuthorizationCredentials | None,
    db: AsyncSession,
    *,
    strict: bool,
) -> AuthContext:
    if not creds:
        if strict:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        return AuthContext(user=None, access_token=None)

    try:
        payload = decode_token(creds.credentials)
        if payload.get("type") != "access":
            raise JWTError()
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        if strict:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        return AuthContext(user=None, access_token=None)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        if strict:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        return AuthContext(user=None, access_token=None)
    return AuthContext(user=user, access_token=creds.credentials)


async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    auth = await _resolve_auth_context(creds, db, strict=True)
    if not auth.user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return auth.user


async def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    auth = await _resolve_auth_context(creds, db, strict=False)
    return auth.user


async def get_optional_auth_context(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    return await _resolve_auth_context(creds, db, strict=False)


def require_role(*roles: UserRole):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return checker


require_admin = require_role(UserRole.superadmin, UserRole.admin)
require_superadmin = require_role(UserRole.superadmin)


def rate_limit(bucket: str, max_requests: int, window_seconds: int):
    async def checker(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"{bucket}:{client_ip}"
        now = monotonic()
        cutoff = now - window_seconds

        async with _rate_limit_lock:
            bucket_times = _rate_limit_buckets[key]
            while bucket_times and bucket_times[0] <= cutoff:
                bucket_times.popleft()

            if len(bucket_times) >= max_requests:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many AI requests, please retry later.",
                )

            bucket_times.append(now)

    return checker


rate_limit_ai_chat = rate_limit("ai-chat", max_requests=12, window_seconds=60)
rate_limit_ai_tools = rate_limit("ai-tools", max_requests=60, window_seconds=60)
rate_limit_ai_config = rate_limit("ai-config", max_requests=30, window_seconds=60)
