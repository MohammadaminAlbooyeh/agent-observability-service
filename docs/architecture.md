# Architecture

## Components

| Path | Responsibility |
|---|---|
| `src/main.py` | App factory: middleware, routers, static files, lifespan (alert scheduler) |
| `src/ingestion/trace_receiver.py` | `/ingestion/trace` and `/ingestion/batch` |
| `src/api/routes/` | Admin REST API: traces, metrics, comparisons, alerts, projects, auth |
| `src/api/middleware/` | Auth (project keys, admin keys, JWT), rate limit, request ID, error handler |
| `src/services/` | Business logic; each service takes an `AsyncSession` |
| `src/evaluators/` | Rule-based checks, LLM judge (OpenAI-compatible API), token cost table |
| `src/dashboard/` | Jinja2 dashboard with cookie-based login |
| `src/database/` | SQLAlchemy models and async engine; schema managed by Alembic (`alembic/`) |
| `sdk/` | Client library: buffered HTTP client and context-manager tracer |

## Data model

```
projects (id, name, team, api_key_hash)
   │ 1..n (ON DELETE SET NULL)
traces (id, trace_id UNIQUE, name, version, trace_metadata, project_id, created_at)
   │ 1..n (ON DELETE CASCADE)
   ├── spans (id, trace_id, span_id, parent_id, name, start/end, duration_ms,
   │          cost_usd, error, span_metadata)   UNIQUE(trace_id, span_id)
   └── evaluations (id, trace_id, judge, score, rationale, details)
alert_rules (id, metric, operator, threshold, window_minutes, channel,
             project_id → projects ON DELETE CASCADE, last_triggered_at)
```

`cost_usd`, `error`, and `version` are taken from span metadata at ingestion and stored as columns,
so metrics are SQL aggregates instead of JSON scans.

## Request flow

1. **Ingestion** — the agent posts spans with its project key. `get_ingest_project` resolves the
   key hash to a project. `TraceService.ingest_spans` upserts the trace, skips spans it already
   has, computes the derived columns, and commits the whole batch in one transaction.
2. **Reads** — admin routes call services that build filtered SQL (`MetricFilter`: project, time
   window, version).
3. **Alerts** — a background task runs `AlertService.evaluate_all()` every
   `ALERT_EVAL_INTERVAL_SECONDS`: one metrics snapshot per (project, window), comparison, and
   notification through `NotificationService`, with a cooldown kept in `last_triggered_at`.
4. **Evaluation** — `POST /traces/{id}/evaluate` runs rule-based checks plus the LLM judge (when
   configured) and stores an `evaluations` row.

## Middleware order

`RequestIDMiddleware` (outermost, so every response has `X-Request-ID`) → `RateLimitMiddleware`
→ routes. Unhandled exceptions are logged with the request ID and returned as a generic 500.
