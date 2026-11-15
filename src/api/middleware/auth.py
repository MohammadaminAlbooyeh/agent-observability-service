"""Auth: per-project API keys for ingestion, admin keys / JWT for reads and management."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import settings
from src.database.base import get_session
from src.database.models.sqlalchemy_models import Project

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.jwt_expire_minutes
DASHBOARD_COOKIE = "access_token"


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def generate_project_api_key() -> str:
    return "obs_" + secrets.token_urlsafe(32)


def is_admin_key(api_key: str | None) -> bool:
    if not api_key:
        return False
    return any(hmac.compare_digest(api_key, key) for key in settings.admin_api_keys)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode({"sub": subject, "exp": expire}, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except JWTError:
        return None


async def verify_jwt(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> dict[str, Any]:
    """Verify a Bearer JWT and return its payload."""
    if not credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing authentication token")
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    return payload


async def require_admin(
    api_key: str | None = Security(api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> str:
    """Allow an admin API key (X-API-Key) or a valid Bearer JWT."""
    if is_admin_key(api_key):
        return "admin-key"
    if credentials:
        payload = decode_token(credentials.credentials)
        if payload is not None:
            return str(payload.get("sub", ""))
    raise HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Admin API key or bearer token required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_ingest_project(
    api_key: str | None = Security(api_key_header),
    session: AsyncSession = Depends(get_session),
) -> Project | None:
    """Resolve the ingesting project from its API key.

    Returns None for admin keys, which may ingest spans not tied to a project.
    """
    if not api_key:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Missing API key")
    if is_admin_key(api_key):
        return None
    result = await session.execute(
        select(Project).where(Project.api_key_hash == hash_api_key(api_key))
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return project


def dashboard_user(request: Request) -> str | None:
    """Return the logged-in dashboard user from the session cookie, if any."""
    token = request.cookies.get(DASHBOARD_COOKIE)
    if not token:
        return None
    payload = decode_token(token)
    return str(payload.get("sub")) if payload else None
