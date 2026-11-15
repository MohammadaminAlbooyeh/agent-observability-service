"""SDK tests: payload contract, nesting, error capture, retries."""

import asyncio
import json

import httpx
import pytest

from sdk import ObservabilityClient, Tracer


class Recorder:
    def __init__(self, statuses=None):
        self.requests: list[httpx.Request] = []
        self.statuses = list(statuses or [])

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status = self.statuses.pop(0) if self.statuses else 201
        return httpx.Response(status, json={})

    @property
    def spans(self) -> list[dict]:
        return [s for r in self.requests for s in json.loads(r.content)]


def make_client(recorder, **kwargs) -> ObservabilityClient:
    kwargs.setdefault("max_retries", 2)
    return ObservabilityClient(
        "http://obs.local/", "proj-key", transport=httpx.MockTransport(recorder), **kwargs
    )


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("sdk.client.time.sleep", lambda _: None)


def test_nesting_and_payload():
    rec = Recorder()
    client = make_client(rec)
    tracer = Tracer(client, version="v3", env="test")
    with tracer.trace("agent") as root:
        with tracer.span("llm") as llm:
            llm.set_usage("gpt-4", 10, 5)
        with tracer.span("tool"):
            pass
    assert client.flush()

    req = rec.requests[0]
    assert req.url.path == "/ingestion/batch"
    assert req.headers["X-API-Key"] == "proj-key"
    spans = {s["name"]: s for s in rec.spans}
    assert {s["trace_id"] for s in spans.values()} == {root.trace_id}
    assert spans["agent"]["parent_id"] is None
    assert spans["llm"]["parent_id"] == root.span_id
    assert spans["tool"]["parent_id"] == root.span_id
    assert spans["llm"]["metadata"] == {
        "version": "v3", "env": "test", "model": "gpt-4", "input_tokens": 10, "output_tokens": 5
    }
    assert spans["agent"]["start_time"].endswith("+00:00")
    assert spans["agent"]["duration_ms"] >= 0


def test_separate_traces_do_not_share_ids():
    rec = Recorder()
    client = make_client(rec)
    tracer = Tracer(client)
    with tracer.span("a"):
        pass
    with tracer.span("b"):
        pass
    client.flush()
    assert len({s["trace_id"] for s in rec.spans}) == 2


def test_exception_marks_error_and_propagates():
    rec = Recorder()
    client = make_client(rec)
    with pytest.raises(ValueError):
        with Tracer(client).span("boom"):
            raise ValueError("bad input")
    client.flush()
    meta = rec.spans[0]["metadata"]
    assert meta["error"] is True
    assert meta["error_type"] == "ValueError"
    assert meta["error_message"] == "bad input"


def test_asyncio_tasks_get_their_own_parent():
    rec = Recorder()
    client = make_client(rec)
    tracer = Tracer(client)

    async def child(name):
        with tracer.span(name):
            await asyncio.sleep(0)

    async def main():
        with tracer.trace("root") as root:
            await asyncio.gather(child("c1"), child("c2"))
        return root

    root = asyncio.new_event_loop().run_until_complete(main())
    client.flush()
    spans = {s["name"]: s for s in rec.spans}
    assert spans["c1"]["parent_id"] == root.span_id
    assert spans["c2"]["parent_id"] == root.span_id


def test_auto_flush_at_batch_size():
    rec = Recorder()
    client = make_client(rec, batch_size=2)
    tracer = Tracer(client)
    for _ in range(3):
        with tracer.span("s"):
            pass
    assert len(rec.requests) == 1
    client.close()
    assert len(rec.spans) == 3


def test_retries_transient_errors_then_succeeds():
    rec = Recorder(statuses=[503, 429, 201])
    client = make_client(rec)
    with Tracer(client).span("s"):
        pass
    assert client.flush() is True
    assert len(rec.requests) == 3


def test_gives_up_without_raising():
    rec = Recorder(statuses=[500, 500, 500])
    client = make_client(rec)
    with Tracer(client).span("s"):
        pass
    assert client.flush() is False
    assert len(rec.requests) == 3


def test_client_error_not_retried():
    rec = Recorder(statuses=[401])
    client = make_client(rec)
    with Tracer(client).span("s"):
        pass
    assert client.flush() is False
    assert len(rec.requests) == 1
