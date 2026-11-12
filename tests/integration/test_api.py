"""API-level tests against src.main using httpx ASGITransport."""

import asyncio
import os
from typing import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.database.base import Base, get_session
from src.main import app

TEST_DB_URL = "sqlite+aiosqlite:///./test_api_observability.db"


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    try:
        os.remove("./test_api_observability.db")
    except FileNotFoundError:
        pass


@pytest.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session


@pytest.fixture
async def client(db_session):
    """Override the get_session dependency to use the test session."""

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()


class TestHealth:
    async def test_health_endpoint(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}


class TestProjectsAPI:
    async def test_create_and_list_projects(self, client):
        resp = await client.post(
            "/projects/",
            json={"name": "my-app", "team": "platform"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "my-app"
        assert data["team"] == "platform"
        assert "id" in data
        assert "created_at" in data

        # List projects
        resp = await client.get("/projects/")
        assert resp.status_code == 200
        projects = resp.json()
        assert len(projects) == 1
        assert projects[0]["name"] == "my-app"

    async def test_get_project_by_id(self, client):
        create_resp = await client.post(
            "/projects/",
            json={"name": "single-app", "team": "team-a"},
        )
        project_id = create_resp.json()["id"]

        resp = await client.get(f"/projects/{project_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == project_id
        assert resp.json()["name"] == "single-app"

    async def test_get_project_not_found(self, client):
        resp = await client.get("/projects/nonexistent-id")
        assert resp.status_code == 404


class TestTracesAPI:
    async def test_list_traces_empty(self, client):
        resp = await client.get("/traces/")
        assert resp.status_code == 200
        assert resp.json() == []


class TestMetricsAPI:
    async def test_latency_endpoint(self, client):
        resp = await client.get("/metrics/latency")
        assert resp.status_code == 200
        data = resp.json()
        assert "p50_ms" in data
        assert "p95_ms" in data
        assert "p99_ms" in data

    async def test_cost_endpoint(self, client):
        resp = await client.get("/metrics/cost")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cost_usd" in data
        assert "average_cost_per_trace_usd" in data

    async def test_error_rate_endpoint(self, client):
        resp = await client.get("/metrics/error-rate")
        assert resp.status_code == 200
        data = resp.json()
        assert "error_rate" in data
        assert "total_traces" in data
        assert "error_traces" in data


class TestComparisonsAPI:
    async def test_compare_versions(self, client):
        resp = await client.get("/comparisons/v1/v2")
        assert resp.status_code == 200
        data = resp.json()
        assert "version_a" in data
        assert "version_b" in data
        assert "diff" in data


class TestAlertsAPI:
    async def test_create_and_list_alert_rules(self, client):
        resp = await client.post(
            "/alerts/",
            json={
                "name": "high error rate",
                "metric": "error_rate",
                "threshold": 0.05,
                "operator": ">",
                "enabled": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "high error rate"
        assert data["threshold"] == 0.05
        assert "id" in data

        resp = await client.get("/alerts/")
        assert resp.status_code == 200
        rules = resp.json()
        assert len(rules) == 1


class TestIngestionAPI:
    async def test_ingest_trace_without_api_key(self, client):
        # Ingestion requires an API key; without VALID_API_KEYS configured,
        # the endpoint returns 503.
        resp = await client.post(
            "/ingestion/trace",
            json={
                "trace_id": "trace-api-test",
                "span_id": "span-1",
                "name": "llm_call",
                "start_time": "2024-01-01T00:00:00+00:00",
                "end_time": "2024-01-01T00:00:01+00:00",
                "duration_ms": 1000.0,
            },
        )
        assert resp.status_code == 503
