# Agent Observability Service

A FastAPI service for ingesting, storing, querying, and evaluating traces and spans from AI agents:
nested span trees, latency/cost/error metrics, version comparisons, alerting, LLM-as-judge
evaluation, and a server-rendered dashboard.

## System Architecture

```mermaid
flowchart TD
    SDK["Agent + SDK\n(sdk/)"] -->|"POST /ingestion/batch\nX-API-Key: project key"| API[FastAPI app\nsrc/main.py]
    Admin["Admin / dashboard user"] -->|"admin key or JWT"| API

    API --> Ingestion[Ingestion\nsrc/ingestion]
    API --> Routes[REST API\nsrc/api]
    API --> Dashboard[Dashboard\nsrc/dashboard]

    Ingestion --> Services[Services\nsrc/services]
    Routes --> Services
    Dashboard --> Services
    Scheduler["Alert scheduler\n(background task)"] --> Services

    Services --> Evaluators[Evaluators\nsrc/evaluators]
    Services --> DB[(Postgres / SQLite\nSQLAlchemy + Alembic)]
    Services -->|webhook| Notify[Slack / webhook]
    Evaluators -->|optional| LLM[OpenAI-compatible LLM]
```

## Project Structure

- `src/` — application (API routes, middleware, services, evaluators, dashboard, models)
- `sdk/` — Python client library for agents ([docs/sdk-usage.md](docs/sdk-usage.md))
- `alembic/` — database migrations
- `tests/` — unit and integration tests (SQLite by default, Postgres in CI)
- `scripts/` — `init_db.py` (run migrations) and `seed_sample_traces.py`
- `docker/` — Dockerfile and entrypoint; `docker-compose.yml` is at the repo root
- `docs/` — [architecture](docs/architecture.md), [API reference](docs/api-reference.md), [SDK usage](docs/sdk-usage.md)

## Getting Started

### Docker

```bash
cp .env.example .env   # set JWT_SECRET and ADMIN_API_KEYS
docker compose up --build
```

The app runs migrations on start and listens on <http://localhost:8000>.

### Local

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env   # set DATABASE_URL (SQLite works: sqlite+aiosqlite:///./observability.db)
alembic upgrade head
uvicorn src.main:app --reload
```

### First steps

```bash
# 1. Create a project; the response includes its ingestion API key (shown once)
curl -X POST localhost:8000/projects/ -H "X-API-Key: $ADMIN_KEY" \
     -H "Content-Type: application/json" -d '{"name": "my-agent"}'

# 2. Send spans with the SDK (see docs/sdk-usage.md) or directly:
curl -X POST localhost:8000/ingestion/batch -H "X-API-Key: $PROJECT_KEY" \
     -H "Content-Type: application/json" \
     -d '[{"trace_id": "t1", "span_id": "s1", "name": "agent_run",
           "start_time": "2026-01-01T00:00:00Z", "end_time": "2026-01-01T00:00:01Z",
           "metadata": {"version": "v1"}}]'

# 3. Open the dashboard and log in with an admin key
open http://localhost:8000/dashboard
```

Optional: `python -m scripts.seed_sample_traces` loads 20 sample traces.
Interactive API docs are at `/docs`.

## Authentication

| Who | Credential | Access |
|---|---|---|
| Agents | Project API key (`X-API-Key`), created with the project | `/ingestion/*` only; spans are assigned to that project |
| Admins | Key from `ADMIN_API_KEYS` (`X-API-Key`) or a JWT from `POST /auth/token` (`Authorization: Bearer`) | All read/management APIs |
| Dashboard | Admin key at `/dashboard/login` → HttpOnly JWT cookie | Dashboard pages |

Project keys are stored only as SHA-256 hashes; rotate with `POST /projects/{id}/rotate-key`.

## Configuration

All settings are environment variables (see [.env.example](.env.example)). `JWT_SECRET` is required.

## Development

```bash
pytest                                  # SQLite
TEST_DATABASE_URL=postgresql+asyncpg://user:pass@localhost/obs_test pytest   # Postgres
ruff check src tests sdk scripts alembic
alembic check                           # models and migrations are in sync
```

After changing models: `alembic revision --autogenerate -m "describe change"`.

## Known limitations

- Rate limiting and the alert scheduler are per process. Running several replicas multiplies the
  rate limit and runs the scheduler on each; the per-rule cooldown stored in the database limits
  duplicate notifications but does not fully prevent them. Use one scheduler instance
  (`ALERT_EVAL_INTERVAL_SECONDS=0` elsewhere) and a proxy- or Redis-based limiter at scale.
- Latency percentiles are computed in Python from root-span durations, filtered in SQL; very large
  windows load one float per trace.

## License

MIT
