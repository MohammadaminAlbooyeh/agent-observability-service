# Agent Observability Service

A FastAPI-based service for ingesting, storing, querying, and evaluating traces and spans from AI agents.

## Project Structure

See the repository layout above. Key directories:

- `src/` — Application source code
- `sdk/` — Thin client library for agent projects
- `tests/` — Unit and integration tests
- `scripts/` — Database init and seeding scripts
- `docker/` — Docker compose and Dockerfile
- `docs/` — Architecture, SDK usage, and API reference

## Getting Started

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env with your settings
uvicorn src.main:app --reload
```

## License

MIT
