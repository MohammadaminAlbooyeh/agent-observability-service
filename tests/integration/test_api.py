"""End-to-end API tests against src.main via httpx ASGITransport."""

from datetime import datetime, timedelta, timezone

import pytest

from src.api.middleware.auth import create_access_token

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def span(trace_id, span_id, name="step", parent_id=None, ms=100.0, **metadata):
    return {
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_id": parent_id,
        "name": name,
        "start_time": T0.isoformat(),
        "end_time": (T0 + timedelta(milliseconds=ms)).isoformat(),
        "metadata": metadata,
    }


def key_headers(project):
    return {"X-API-Key": project["api_key"]}


class TestHealthAndAuth:
    async def test_health_is_public(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}
        assert "X-Request-ID" in resp.headers

    @pytest.mark.parametrize(
        "method,path",
        [
            ("get", "/traces/"),
            ("get", "/traces/x"),
            ("post", "/traces/x/evaluate"),
            ("get", "/metrics/summary"),
            ("get", "/metrics/latency"),
            ("get", "/metrics/cost"),
            ("get", "/metrics/error-rate"),
            ("get", "/comparisons/a/b"),
            ("get", "/alerts/"),
            ("post", "/alerts/evaluate"),
            ("get", "/projects/"),
            ("post", "/projects/"),
        ],
    )
    async def test_admin_routes_require_auth(self, client, method, path):
        resp = await getattr(client, method)(path)
        assert resp.status_code == 401

    async def test_project_key_cannot_read(self, client, project):
        resp = await client.get("/traces/", headers=key_headers(project))
        assert resp.status_code == 401

    async def test_token_exchange_and_bearer_access(self, client):
        assert (await client.post("/auth/token", json={"api_key": "wrong"})).status_code == 401
        resp = await client.post("/auth/token", json={"api_key": "test-admin-key"})
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        resp = await client.get("/traces/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    async def test_expired_bearer_rejected(self, client):
        token = create_access_token("admin", expires_delta=timedelta(seconds=-1))
        resp = await client.get("/traces/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


class TestProjects:
    async def test_create_returns_key_once(self, client, admin_headers, project):
        assert project["api_key"].startswith("obs_")
        resp = await client.get(f"/projects/{project['id']}", headers=admin_headers)
        assert resp.status_code == 200
        assert "api_key" not in resp.json()
        listed = (await client.get("/projects/", headers=admin_headers)).json()
        assert [p["name"] for p in listed] == ["proj-a"]

    async def test_not_found(self, client, admin_headers):
        assert (await client.get("/projects/nope", headers=admin_headers)).status_code == 404

    async def test_rotate_key_invalidates_old(self, client, admin_headers, project):
        resp = await client.post(f"/projects/{project['id']}/rotate-key", headers=admin_headers)
        new_key = resp.json()["api_key"]
        assert new_key != project["api_key"]
        old = await client.post("/ingestion/trace", json=span("t", "s"), headers=key_headers(project))
        assert old.status_code == 401
        new = await client.post("/ingestion/trace", json=span("t", "s"), headers={"X-API-Key": new_key})
        assert new.status_code == 201

    async def test_delete_keeps_traces_unassigned(self, client, admin_headers, project):
        await client.post("/ingestion/trace", json=span("t-del", "s"), headers=key_headers(project))
        resp = await client.delete(f"/projects/{project['id']}", headers=admin_headers)
        assert resp.status_code == 204
        trace = (await client.get("/traces/t-del", headers=admin_headers)).json()
        assert trace["project_id"] is None


class TestIngestion:
    async def test_requires_valid_key(self, client):
        assert (await client.post("/ingestion/trace", json=span("t", "s"))).status_code == 401
        resp = await client.post(
            "/ingestion/trace", json=span("t", "s"), headers={"X-API-Key": "bogus"}
        )
        assert resp.status_code == 401

    async def test_single_span_assigned_to_project(self, client, admin_headers, project):
        resp = await client.post(
            "/ingestion/trace", json=span("t1", "s1", ms=250), headers=key_headers(project)
        )
        assert resp.status_code == 201
        assert resp.json()["duration_ms"] == 250.0
        traces = (await client.get(f"/traces/?project_id={project['id']}", headers=admin_headers)).json()
        assert [t["trace_id"] for t in traces] == ["t1"]

    async def test_batch_builds_tree_and_dedupes(self, client, admin_headers, project):
        batch = [
            span("t2", "root", name="agent", version="v1", output="hi"),
            span("t2", "llm", name="llm", parent_id="root", model="gpt-4",
                 input_tokens=1000, output_tokens=1000),
            span("t2", "tool", name="tool", parent_id="llm", error=True),
        ]
        resp = await client.post("/ingestion/batch", json=batch, headers=key_headers(project))
        assert resp.status_code == 201
        assert resp.json()["count"] == 3

        again = await client.post("/ingestion/batch", json=batch, headers=key_headers(project))
        assert again.status_code == 201

        trace = (await client.get("/traces/t2", headers=admin_headers)).json()
        assert len(trace["spans"]) == 3
        assert trace["name"] == "agent"
        assert trace["version"] == "v1"
        assert trace["error"] is True
        assert trace["cost_usd"] == pytest.approx(0.09)
        root = trace["tree"]
        assert [n["span_id"] for n in root] == ["root"]
        assert root[0]["children"][0]["children"][0]["span_id"] == "tool"

    async def test_batch_is_atomic(self, client, admin_headers, project):
        bad = [span("t3", "a"), {**span("t3", "b"), "start_time": "not-a-date"}]
        resp = await client.post("/ingestion/batch", json=bad, headers=key_headers(project))
        assert resp.status_code == 422
        assert (await client.get("/traces/t3", headers=admin_headers)).status_code == 404

    async def test_empty_and_oversized_batch(self, client, project):
        resp = await client.post("/ingestion/batch", json=[], headers=key_headers(project))
        assert resp.status_code == 400
        big = [span("t", f"s{i}") for i in range(1001)]
        resp = await client.post("/ingestion/batch", json=big, headers=key_headers(project))
        assert resp.status_code == 422

    async def test_cannot_write_to_other_projects_trace(self, client, admin_headers, project):
        other = (await client.post("/projects/", json={"name": "b"}, headers=admin_headers)).json()
        await client.post("/ingestion/trace", json=span("shared", "s1"), headers=key_headers(project))
        resp = await client.post("/ingestion/trace", json=span("shared", "s2"), headers=key_headers(other))
        assert resp.status_code == 403

    async def test_unix_timestamp_accepted(self, client, project):
        payload = {**span("t-unix", "s"), "start_time": 1767225600.0, "end_time": 1767225601.5}
        resp = await client.post("/ingestion/trace", json=payload, headers=key_headers(project))
        assert resp.status_code == 201
        assert resp.json()["duration_ms"] == 1500.0


class TestMetricsAndComparisons:
    async def _seed(self, client, project):
        batch = []
        for i, (version, ms, err) in enumerate(
            [("v1", 100, False), ("v1", 300, True), ("v2", 50, False), ("v2", 70, False)]
        ):
            batch.append(span(f"m{i}", "root", ms=ms, version=version, cost_usd=0.5, error=err))
        resp = await client.post("/ingestion/batch", json=batch, headers=key_headers(project))
        assert resp.status_code == 201

    async def test_metrics(self, client, admin_headers, project):
        await self._seed(client, project)
        summary = (await client.get("/metrics/summary", headers=admin_headers)).json()
        assert summary["total_traces"] == 4
        assert summary["error_traces"] == 1
        assert summary["error_rate"] == 25.0
        assert summary["total_cost_usd"] == 2.0
        assert summary["average_cost_per_trace_usd"] == 0.5
        assert summary["p50_ms"] == 85.0

        latency = (await client.get("/metrics/latency", headers=admin_headers)).json()
        assert set(latency) == {"p50_ms", "p95_ms", "p99_ms"}
        scoped = (await client.get("/metrics/error-rate?project_id=none", headers=admin_headers)).json()
        assert scoped["total_traces"] == 0
        windowed = (await client.get("/metrics/cost?window_minutes=5", headers=admin_headers)).json()
        assert windowed["total_cost_usd"] == 2.0

    async def test_compare_versions(self, client, admin_headers, project):
        await self._seed(client, project)
        data = (await client.get("/comparisons/v1/v2", headers=admin_headers)).json()
        assert data["version_a"]["total_traces"] == 2
        assert data["version_a"]["error_rate"] == 50.0
        assert data["version_b"]["error_rate"] == 0.0
        assert data["diff"]["error_rate"] == -50.0
        assert data["diff"]["p50_ms"] == 60.0 - 200.0


class TestAlerts:
    async def test_crud(self, client, admin_headers, project):
        body = {"name": "errors", "metric": "error_rate", "threshold": 5, "operator": ">",
                "project_id": project["id"]}
        resp = await client.post("/alerts/", json=body, headers=admin_headers)
        assert resp.status_code == 201
        rule = resp.json()
        assert rule["window_minutes"] == 60

        resp = await client.patch(f"/alerts/{rule['id']}", json={"threshold": 10, "enabled": False},
                                  headers=admin_headers)
        assert resp.json()["threshold"] == 10
        assert resp.json()["enabled"] is False
        assert len((await client.get(f"/alerts/?project_id={project['id']}", headers=admin_headers)).json()) == 1

        assert (await client.delete(f"/alerts/{rule['id']}", headers=admin_headers)).status_code == 204
        assert (await client.get(f"/alerts/{rule['id']}", headers=admin_headers)).status_code == 404

    @pytest.mark.parametrize(
        "patch",
        [{"metric": "bogus"}, {"operator": "!="}, {"channel": "ftp://x"}, {"window_minutes": 0}],
    )
    async def test_validation(self, client, admin_headers, patch):
        body = {"name": "r", "metric": "error_rate", "threshold": 1, "operator": ">", **patch}
        assert (await client.post("/alerts/", json=body, headers=admin_headers)).status_code == 422

    async def test_unknown_project(self, client, admin_headers):
        body = {"name": "r", "metric": "error_rate", "threshold": 1, "operator": ">", "project_id": "x"}
        assert (await client.post("/alerts/", json=body, headers=admin_headers)).status_code == 404

    async def test_evaluate_fires_once_then_cooldown(self, client, admin_headers, project):
        await client.post("/ingestion/trace", json=span("a1", "s", error=True), headers=key_headers(project))
        body = {"name": "errors", "metric": "error_rate", "threshold": 50, "operator": ">=", "channel": "log"}
        rule = (await client.post("/alerts/", json=body, headers=admin_headers)).json()

        first = (await client.post("/alerts/evaluate", headers=admin_headers)).json()
        assert first == [
            {"rule_id": rule["id"], "rule_name": "errors", "metric": "error_rate", "operator": ">=",
             "threshold": 50.0, "value": 100.0, "breached": True, "notified": True, "in_cooldown": False}
        ]
        second = (await client.post("/alerts/evaluate", headers=admin_headers)).json()
        assert second[0]["notified"] is False
        assert second[0]["in_cooldown"] is True
        stored = (await client.get(f"/alerts/{rule['id']}", headers=admin_headers)).json()
        assert stored["last_triggered_at"] is not None


class TestEvaluation:
    async def test_rule_based_evaluation(self, client, admin_headers, project):
        await client.post(
            "/ingestion/trace",
            json=span("e1", "root", output='{"answer": 42}', keyword="answer"),
            headers=key_headers(project),
        )
        resp = await client.post("/traces/e1/evaluate", headers=admin_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["judge"] == "rule_based"
        assert data["score"] == 1.0

        resp = await client.post("/traces/e1/evaluate", json={"keyword": "missing"}, headers=admin_headers)
        assert resp.json()["score"] == 0.0
        assert "keyword" in resp.json()["rationale"]

        trace = (await client.get("/traces/e1", headers=admin_headers)).json()
        assert [e["score"] for e in trace["evaluations"]] == [1.0, 0.0]

    async def test_missing_trace(self, client, admin_headers):
        assert (await client.post("/traces/nope/evaluate", headers=admin_headers)).status_code == 404


class TestDashboard:
    async def test_login_flow(self, client, project):
        resp = await client.get("/dashboard")
        assert resp.status_code == 303
        assert resp.headers["location"] == "/dashboard/login"

        resp = await client.post("/dashboard/login", data={"api_key": "wrong"})
        assert resp.status_code == 401

        resp = await client.post("/dashboard/login", data={"api_key": "test-admin-key"})
        assert resp.status_code == 303
        assert "httponly" in resp.headers["set-cookie"].lower()

        await client.post("/ingestion/trace", json=span("d1", "root", name="agent"),
                          headers=key_headers(project))
        page = await client.get("/dashboard")
        assert page.status_code == 200
        assert "d1" in page.text
        detail = await client.get("/dashboard/traces/d1")
        assert detail.status_code == 200
        assert "agent" in detail.text
        assert (await client.get("/dashboard/traces/zzz")).status_code == 404

        await client.post("/dashboard/logout")
        client.cookies.clear()
        assert (await client.get("/dashboard")).status_code == 303

    async def test_static_css_served(self, client):
        assert (await client.get("/static/css/dashboard.css")).status_code == 200
