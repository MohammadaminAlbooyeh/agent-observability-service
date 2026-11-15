# SDK Usage

The SDK lives in `sdk/` and depends only on `httpx`. It isn't published to PyPI yet: copy the
`sdk/` directory into your agent project (or add this repo to `PYTHONPATH`) and
`pip install httpx`.

## Basic usage

```python
from sdk import ObservabilityClient, Tracer

client = ObservabilityClient(base_url="http://localhost:8000", api_key="obs_...project key...")
tracer = Tracer(client, version="v2")  # version + any kwargs are added to every span

with tracer.trace("agent_run", output=None) as root:      # starts a new trace
    with tracer.span("llm_call") as span:                   # child of agent_run
        response = call_llm(...)
        span.set_usage("gpt-4", input_tokens=812, output_tokens=154)  # → cost_usd
    with tracer.span("tool_call", tool="web_search"):
        run_tool(...)
    root.set("output", response.text)                        # used by evaluation

client.close()  # flushes; also happens automatically at interpreter exit
```

- `tracer.span()` nests under the currently open span; with no open span it starts a new trace.
- Nesting is tracked with `contextvars`, so it works in threads and across `asyncio` tasks.
- An exception inside a span records `error: true`, `error_type`, and `error_message`, then is
  re-raised.
- `span.set(key, value)` attaches metadata. Keys the service understands are listed in
  [api-reference.md](api-reference.md#ingestion-project-key-or-admin-key).

## Delivery

- Spans are buffered and sent to `POST /ingestion/batch` when `batch_size` (default 50) is
  reached, on `client.flush()`, on `client.close()` / `with ObservabilityClient(...)` exit, and at
  exit.
- Network errors and `409/429/5xx` are retried with backoff (`max_retries`, default 3). Other
  errors (e.g. `401` for a bad key) are logged on the `agent_observability` logger and dropped.
  The SDK never raises into your agent code. `flush()` returns `False` if anything was dropped.
- The server deduplicates `(trace_id, span_id)`, so retries can't create duplicate spans.
- `flush()` is a blocking HTTP call. In async agents, keep `batch_size` large or call
  `await asyncio.to_thread(client.flush)`.

## Constructor

```python
ObservabilityClient(base_url, api_key, batch_size=50, timeout=10.0, max_retries=3, transport=None)
Tracer(client, version=None, **default_metadata)
```
