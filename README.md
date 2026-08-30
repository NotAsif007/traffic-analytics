# Traffic Analytics Backend

**PS 26127 — SIH 2026**  
City-Wide AI Engine for Multi-Camera ANPR Trajectory Tracking and Urban Traffic Analytics.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL + PostGIS](https://img.shields.io/badge/PostgreSQL-16+PostGIS-blue.svg)](https://postgis.net/)

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/) (v4.x+)
- Docker Compose v2 (bundled with Docker Desktop)

### 1. Clone and configure

```bash
git clone <repo-url>
cd traffic-analytics

# Create your local .env from the template
copy .env.example .env
```

The defaults in `.env.example` are pre-configured for `docker compose`. You don't need to edit `.env` to get started.

### 2. Start the stack

```bash
docker compose up --build
```

This will:
1. Start PostgreSQL 16 with PostGIS 3.4
2. Start Redis 7
3. Run database migrations (`alembic upgrade head`)
4. Start the FastAPI application

### 3. Verify the API is running

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:

```json
{
  "status": "ok",
  "version": "0.1.0",
  "environment": "development",
  "components": {
    "database": {
      "status": "ok",
      "latency_ms": 1.23,
      "detail": "PostgreSQL connection established."
    }
  }
}
```

### 4. Interactive API docs

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json

---

## Development Setup (without Docker)

### Prerequisites

- Python 3.12+
- PostgreSQL 16 with PostGIS extension
- Redis 7

### 1. Create virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -e ".[dev]"
```

### 3. Configure environment

```bash
copy .env.example .env
# Edit .env with your local DB credentials
```

### 4. Run migrations

```bash
alembic upgrade head
```

### 5. Start the development server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Running Tests

### Unit tests (no database required)

```bash
pytest tests/unit/ -v -m unit
```

### Integration tests (requires PostgreSQL)

Set up a separate test database first:

```bash
# If using docker compose, start just the DB:
docker compose up db -d

# Or use your local PostgreSQL and create a test DB:
# createdb traffic_test
```

Set the test database environment variables:

```bash
# Windows (PowerShell)
$env:TEST_DATABASE_URL = "postgresql+asyncpg://traffic_user:traffic_pass@localhost:5432/traffic_test"
$env:TEST_ALEMBIC_DATABASE_URL = "postgresql+psycopg2://traffic_user:traffic_pass@localhost:5432/traffic_test"

# Linux/Mac
export TEST_DATABASE_URL="postgresql+asyncpg://traffic_user:traffic_pass@localhost:5432/traffic_test"
export TEST_ALEMBIC_DATABASE_URL="postgresql+psycopg2://traffic_user:traffic_pass@localhost:5432/traffic_test"
```

```bash
pytest tests/integration/ -v -m integration
```

### All tests

```bash
pytest -v
```

### With coverage

```bash
pytest --cov=app --cov-report=term-missing --cov-report=html
```

---

## Project Structure

```
traffic-analytics/
├── app/
│   ├── main.py              # FastAPI application factory
│   ├── config.py            # Pydantic settings (from env vars)
│   ├── core/
│   │   ├── exceptions.py    # Domain exceptions
│   │   ├── errors.py        # HTTP error handler registration
│   │   └── logging.py       # Structured logging (structlog)
│   ├── db/
│   │   ├── base.py          # SQLAlchemy DeclarativeBase
│   │   └── session.py       # Async engine + session factory
│   ├── models/
│   │   └── mixins.py        # UUID + timestamp mixins
│   ├── schemas/
│   │   ├── common.py        # Error envelope, pagination
│   │   └── health.py        # Health check schemas
│   ├── repositories/
│   │   └── base.py          # Generic CRUD repository
│   ├── services/
│   │   └── health.py        # DB connectivity check service
│   └── api/
│       ├── deps.py          # FastAPI dependency injection
│       └── v1/
│           ├── router.py    # v1 router aggregator
│           └── health.py    # /health, /health/ready endpoints
├── alembic/
│   ├── env.py               # Migration environment
│   └── versions/
│       └── 0001_enable_postgis.py   # First migration
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── unit/
│   │   └── test_health_service.py
│   └── integration/
│       └── test_health_api.py
├── docs/
│   ├── context.md           # Current state + decisions log
│   ├── spec.md              # Technical specification
│   └── architecture.md      # Architecture reference
├── Dockerfile               # Multi-stage build
├── docker-compose.yml       # Full stack (DB + Redis + API + migrate)
├── alembic.ini              # Alembic config (no credentials)
├── pyproject.toml           # Dependencies + tool config
└── .env.example             # Environment template
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Full health check with DB connectivity test |
| `GET` | `/api/v1/health/ready` | Lightweight readiness probe |

All domain endpoints (cameras, observations, vehicles, etc.) are planned for Phase 1b.

---

## Error Responses

All API errors return a consistent JSON envelope:

```json
{
  "error": {
    "code": "NOT_FOUND",
    "message": "Camera not found",
    "details": {
      "resource": "Camera",
      "identifier": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
    }
  }
}
```

---

## Database Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Check current migration version
alembic current

# Generate a new migration from model changes
alembic revision --autogenerate -m "add camera table"

# Rollback one step
alembic downgrade -1

# View migration history
alembic history
```

> **Important:** Set `ALEMBIC_DATABASE_URL` (psycopg2 sync DSN) before running alembic commands.

---

## Docker Commands

```bash
# Start all services
docker compose up

# Start with rebuild
docker compose up --build

# Start only the database (for local development)
docker compose up db redis

# View logs
docker compose logs api
docker compose logs api -f   # follow

# Stop all services
docker compose down

# Stop and remove volumes (clean slate)
docker compose down -v

# Run migrations manually in the container
docker compose run --rm migrate alembic upgrade head

# Open a shell in the API container
docker compose exec api bash
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `DATABASE_URL` | ✅ | — | Async DSN: `postgresql+asyncpg://...` |
| `ALEMBIC_DATABASE_URL` | ✅ | — | Sync DSN: `postgresql+psycopg2://...` |
| `REDIS_URL` | | `redis://localhost:6379/0` | Redis DSN |
| `APP_NAME` | | `traffic-analytics` | Application name |
| `APP_ENV` | | `development` | `development` / `staging` / `production` |
| `DEBUG` | | `false` | Enable SQL echo and debug mode |
| `LOG_LEVEL` | | `INFO` | Log verbosity |
| `LOG_FORMAT` | | `json` | `json` (production) or `console` (development) |
| `CORS_ORIGINS` | | `[]` | Comma-separated allowed CORS origins |
| `DB_POOL_SIZE` | | `20` | SQLAlchemy connection pool size |
| `DB_MAX_OVERFLOW` | | `10` | Max overflow connections |

---

## Development Phases

| Phase | Status | Description |
|---|---|---|
| **1 — Foundation** | ✅ **Complete** | FastAPI, PostgreSQL, migrations, health API, tests |
| **1b — Domain APIs** | 🔜 Next | Camera, Observation, Identity, Blacklist, Alert APIs |
| **2 — Spatial & Trajectories** | Planned | Roads, topology, trajectories, async workers |
| **3 — AI Integration** | Planned | Worker mode, embeddings, multi-signal matching |
| **4 — Hardening** | Planned | Auth, rate limiting, performance, demo data |

---

## Documentation

| Document | Description |
|---|---|
| [docs/context.md](docs/context.md) | Current state, architectural decisions, what's next |
| [docs/spec.md](docs/spec.md) | Technical specification and requirements |
| [docs/architecture.md](docs/architecture.md) | Architecture reference, layer rules, diagrams |
