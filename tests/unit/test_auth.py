"""Unit tests for auth (JWT creation/verification, API keys)."""

from datetime import timedelta

import pytest
from jose import jwt

from src.api.middleware.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    create_access_token,
    verify_jwt,
)
from src.config.settings import settings


class TestCreateAccessToken:
    def test_token_contains_subject_and_expiry(self):
        token = create_access_token("user-123")
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        assert payload["sub"] == "user-123"
        assert "exp" in payload

    def test_custom_expires_delta(self):
        token = create_access_token("user-456", expires_delta=timedelta(minutes=5))
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
        assert payload["sub"] == "user-456"


class TestVerifyJWT:
    @pytest.mark.asyncio
    async def test_valid_token_returns_payload(self):
        from fastapi.security import HTTPAuthorizationCredentials

        token = create_access_token("user-789")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        payload = await verify_jwt(creds)
        assert payload["sub"] == "user-789"

    @pytest.mark.asyncio
    async def test_invalid_token_raises(self):
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials

        creds = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="not-a-real-token"
        )
        with pytest.raises(HTTPException):
            await verify_jwt(creds)

    @pytest.mark.asyncio
    async def test_missing_credentials_raises(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await verify_jwt(None)


class TestConstants:
    def test_algorithm_is_hs256(self):
        assert ALGORITHM == "HS256"

    def test_default_expiry_minutes(self):
        assert ACCESS_TOKEN_EXPIRE_MINUTES == 60
