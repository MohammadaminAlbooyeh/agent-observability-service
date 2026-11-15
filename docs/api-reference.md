# API Reference

Interactive OpenAPI docs are served at `/docs` (Swagger UI) and `/redoc`.

## Authentication

- **Project key** — `X-API-Key: obs_...`, returned once when a project is created. Ingestion only.
- **Admin** — `X-API-Key: <one of ADMIN_API_KEYS>` or `Authorization: Bearer <jwt>`.

Errors use `{"detail": ...}`. Every response carries `X-Request-ID` (sent value is echoed back).
`429` responses include `Retry-After`.

## Ingestion (project key or admin key)

| Method | Path | Description |
|---|---|---|
| `POST` | `/ingestion/trace` | Ingest one span → `201` span |
| `POST` | `/ingestion/batch` | Ingest a JSON array of up to 1000 spans atomically → `201 {"count", "spans"}` |

Span body:

```json
{
  "trace_id": "string (1-64)",
  "span_id": "string (1-64), unique within the trace",
  "parent_id": "string | null",
  "name": "string",
  "start_time": "ISO-8601 or unix seconds",
  "end_time": "ISO-8601 or unix seconds | null",
  "duration_ms": "number | null (computed from end_time when omitted)",
  "metadata": {}
}
```

Recognised metadata keys:

| Key | Effect |
|---|---|
| `version` | Sets the trace version (used by comparisons and the `version` filter) |
| `cost_usd` | Span cost |
| `model` + `input_tokens`/`output_tokens` (or `prompt_tokens`/`completion_tokens`) | Cost computed from the built-in price table when `cost_usd` is absent |
| `error: true` or `status: "error"` | Marks the span (and so the trace) as errored |
| `output`, `reference`, `schema`, `min_len`, `max_len`, `keyword` (root span) | Inputs for evaluation |

Behaviour: re-sending a span with the same `(trace_id, span_id)` is a no-op (safe retries).
The root span (no `parent_id`) names the trace and its metadata is merged into the trace.
Writing to a trace owned by another project returns `403`; a concurrent-write race returns `409`
(retry).

## Auth

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/token` | `{"api_key": "<admin key>"}` → `{"access_token", "token_type", "expires_in"}` |

## Projects (admin)

| Method | Path | Description |
|---|---|---|
| `POST` | `/projects/` | `{"name", "team"?}` → `201` project **with `api_key`** (shown once) |
| `GET` | `/projects/` | List projects |
| `GET` | `/projects/{id}` | Get a project |
| `POST` | `/projects/{id}/rotate-key` | Issue a new key; the old key stops working |
| `DELETE` | `/projects/{id}` | Delete project and its alert rules; traces are kept, unassigned |

## Traces (admin)

| Method | Path | Description |
|---|---|---|
| `GET` | `/traces/?project_id=&version=&limit=50&offset=0` | Recent traces with `span_count`, `error`, `cost_usd` (`limit` ≤ 500) |
| `GET` | `/traces/{trace_id}` | Trace with `spans` (flat, by start time), nested `tree`, and `evaluations` |
| `POST` | `/traces/{trace_id}/evaluate` | Run evaluation → `201`; optional body overrides `output`, `reference`, `schema`, `min_len`, `max_len`, `keyword` |

Evaluation score: rule-based checks only → `1.0` pass / `0.0` fail. When `LLM_BASE_URL` and
`LLM_API_KEY` are set: `0.5 × rules + 0.5 × mean(accuracy, relevance)` from the LLM judge.

## Metrics (admin)

All accept `?project_id=` and `?window_minutes=` (traces created in the last N minutes).

| Method | Path | Response |
|---|---|---|
| `GET` | `/metrics/summary` | All metrics below in one object |
| `GET` | `/metrics/latency` | `p50_ms`, `p95_ms`, `p99_ms` of root-span (end-to-end) duration |
| `GET` | `/metrics/cost` | `total_cost_usd`, `average_cost_per_trace_usd` |
| `GET` | `/metrics/error-rate` | `error_rate` (% of traces with an errored span), `total_traces`, `error_traces` |

## Comparisons (admin)

| Method | Path | Description |
|---|---|---|
| `GET` | `/comparisons/{version_a}/{version_b}?project_id=&window_minutes=` | Per-version `total_traces`, `p50_ms`, `p95_ms`, `error_rate`, `average_cost_per_trace_usd` and `diff` (b − a) |

## Alerts (admin)

| Method | Path | Description |
|---|---|---|
| `POST` | `/alerts/` | Create rule → `201` |
| `GET` | `/alerts/?project_id=` | List rules |
| `GET` | `/alerts/{id}` | Get rule |
| `PATCH` | `/alerts/{id}` | Partial update |
| `DELETE` | `/alerts/{id}` | Delete → `204` |
| `POST` | `/alerts/evaluate` | Evaluate all enabled rules now; returns per-rule results |

Rule body:

```json
{
  "name": "High error rate",
  "metric": "error_rate | p50_ms | p95_ms | p99_ms | total_cost_usd | average_cost_per_trace_usd | total_traces | error_traces",
  "operator": "> | < | >= | <= | ==",
  "threshold": 5,
  "window_minutes": 60,
  "channel": "log | https://hooks.slack.com/services/... | any http(s) webhook",
  "project_id": "optional; omit for all projects",
  "enabled": true
}
```

Rules are evaluated every `ALERT_EVAL_INTERVAL_SECONDS` (default 60; `0` disables). A breached
rule notifies once, then is silent for `ALERT_COOLDOWN_SECONDS` (default 900). Webhooks receive
`{"text": "...", "payload": {...rule, "value": ...}}`. A failed delivery does not start the
cooldown.

## Dashboard

`/dashboard/login` (admin key) → `/dashboard` (metrics + recent traces, project filter) →
`/dashboard/traces/{trace_id}` (span tree, metadata, evaluations).

## Health

`GET /health` → `{"status": "ok"}` (no auth, not rate limited).
