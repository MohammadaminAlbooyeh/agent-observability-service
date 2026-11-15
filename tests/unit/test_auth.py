"""Unit tests for auth (JWT creation/verification, API keys)."""

from datetime import timedelta

import pytest
from jose import jwt

from src.api.middleware.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    create_access_token,
    generate_project_api_key,
    hash_api_key,
    is_admin_key,
    require_admin,
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


class TestKeys:
    def test_project_keys_are_unique_and_hashed(self):
        a, b = generate_project_api_key(), generate_project_api_key()
        assert a != b and a.startswith("obs_")
        assert hash_api_key(a) == hash_api_key(a)
        assert len(hash_api_key(a)) == 64 and a not in hash_api_key(a)

    def test_is_admin_key(self):
        assert is_admin_key("test-admin-key")
        assert not is_admin_key("nope")
        assert not is_admin_key(None)
        assert not is_admin_key("")


class TestRequireAdmin:
    async def test_admin_key_or_token(self):
        from fastapi.security import HTTPAuthorizationCredentials

        assert await require_admin("test-admin-key", None) == "admin-key"
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=create_access_token("u"))
        assert await require_admin(None, creds) == "u"

    async def test_rejects_others(self):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await require_admin("bad", None)
        assert exc.value.status_code == 401
