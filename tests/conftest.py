"""Shared fixtures. Set TEST_DATABASE_URL to run against Postgres (CI does)."""

import asyncio
import os
import tempfile
from collections.abc import AsyncIterator

_default_db = f"sqlite+aiosqlite:///{tempfile.gettempdir()}/obs_test_{os.getpid()}.db"
TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", _default_db)

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ["JWT_SECRET"] = "test-secret-do-not-use-in-prod"
os.environ["ADMIN_API_KEYS"] = "test-admin-key"
os.environ["ALERT_EVAL_INTERVAL_SECONDS"] = "0"
os.environ["RATE_LIMIT_CALLS"] = "100000"

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

import src.database.models.sqlalchemy_models  # noqa: E402,F401
from src.database.base import Base, get_session  # noqa: E402

ADMIN_KEY = "test-admin-key"
ADMIN_HEADERS = {"X-API-Key": ADMIN_KEY}


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_engine() -> AsyncIterator:
    engine = create_async_engine(TEST_DB_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def session_factory(test_engine):
    return async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def db_session(session_factory) -> AsyncIterator[AsyncSession]:
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(session_factory) -> AsyncIterator[AsyncClient]:
    """API client; each request gets its own session on the test database."""
    from src.main import app

    async def override_get_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return dict(ADMIN_HEADERS)


@pytest.fixture
async def project(client) -> dict:
    """A project created through the API, including its one-time ingestion key."""
    resp = await client.post("/projects/", json={"name": "proj-a"}, headers=ADMIN_HEADERS)
    assert resp.status_code == 201
    return resp.json()
