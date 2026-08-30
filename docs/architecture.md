# Architecture — Traffic Analytics Backend

> See also: [spec.md](spec.md) | [context.md](context.md)

---

## Module Structure

```
app/
├── main.py            ← FastAPI factory + lifespan (startup/shutdown)
├── config.py          ← All settings from environment variables
│
├── core/              ← Shared primitives, no domain logic
│   ├── exceptions.py  ← Domain exceptions (no HTTP coupling)
│   ├── errors.py      ← Maps exceptions → HTTP error envelopes
│   └── logging.py     ← Structured logging (structlog)
│
├── db/                ← Database infrastructure
│   ├── base.py        ← SQLAlchemy DeclarativeBase
│   └── session.py     ← Async engine, session factory, get_db()
│
├── models/            ← SQLAlchemy ORM models (DB representation)
│   └── mixins.py      ← UUIDMixin, TimestampMixin
│
├── schemas/           ← Pydantic models (API representation)
│   ├── common.py      ← Error envelope, pagination, base config
│   └── health.py      ← Health check response schemas
│
├── repositories/      ← Data access layer (all SQL here, nowhere else)
│   └── base.py        ← Generic async CRUD base repository
│
├── services/          ← Business logic (no SQLAlchemy, no FastAPI)
│   └── health.py      ← DB connectivity check + health aggregation
│
└── api/               ← HTTP layer (no business logic)
    ├── deps.py        ← All FastAPI Depends() definitions
    └── v1/
        ├── router.py  ← Aggregates all v1 routers
        └── health.py  ← GET /health, GET /health/ready
```

---

## Layer Dependency Rules

```
Route Handlers  →  Services  →  Repositories  →  SQLAlchemy
                ↓
              Schemas (Pydantic)
```

**Rules enforced by convention and code review:**

| Layer | May import | Must NOT import |
|---|---|---|
| `api/` | `services/`, `schemas/`, `core/`, `config` | `models/`, `repositories/`, `db/` |
| `services/` | `repositories/`, `schemas/`, `core/`, `config` | `api/`, `fastapi` |
| `repositories/` | `models/`, `db/`, `core/` | `api/`, `services/`, `schemas/` |
| `models/` | `db/base.py` | Everything else |
| `schemas/` | `pydantic` | `models/`, `db/`, `repositories/` |
| `core/` | Standard library, `config` | `api/`, `services/`, `models/`, `db/` |

---

## Request Lifecycle

```
HTTP Request
    │
    ▼
FastAPI Router (app/api/v1/health.py)
    │  1. Validates path, query params, request body via Pydantic
    │  2. Resolves Depends() — injects DB session, service instances
    │
    ▼
Service (app/services/health.py)
    │  3. Executes business logic
    │  4. Calls repository methods if DB access needed
    │  5. Raises domain exceptions on errors
    │
    ▼
Repository (app/repositories/*)
    │  6. Executes SQL via SQLAlchemy async session
    │  7. Returns ORM model instances
    │
    ▼
Service
    │  8. Converts ORM → Pydantic schema
    │
    ▼
Route Handler
    │  9. Returns Pydantic schema (FastAPI serialises to JSON)
    │
    ▼
HTTP Response

─── On Exception ─────────────────────────────────────────────
Domain Exception → app/core/errors.py → Consistent JSON envelope
Pydantic Error  → RequestValidationError handler → 422 envelope
Unhandled       → Generic handler → 500 + logged traceback
```

---

## Database Architecture

### Connection strategy

- **Application:** Async engine with `asyncpg`, connection pool (size: configurable via `DB_POOL_SIZE`)
- **Alembic migrations:** Separate sync engine with `psycopg2`, `NullPool` (no pooling for CLI tools)
- **Tests:** Separate test DB, `create_all()` for speed, SAVEPOINT per test for isolation

### Session lifecycle

```
get_db() FastAPI dependency
    │
    ├── factory()  → AsyncSession
    │
    │  yield session to route handler
    │
    ├── success → commit()
    └── exception → rollback()
    └── finally → close()
```

### Schema management

All schema changes via Alembic migrations. Never use `create_all()` in production.  
Migration naming: `YYYYMMDD_HHMM_<revision>_<slug>.py`

First migration always: enable PostGIS extension.

---

## Error Handling Architecture

```
Exception hierarchy:
    TrafficAnalyticsError (base)
    ├── NotFoundError        → 404 NOT_FOUND
    ├── ValidationError      → 422 VALIDATION_ERROR
    ├── ConflictError        → 409 CONFLICT
    ├── DatabaseError        → 503 DATABASE_ERROR
    └── ServiceUnavailableError → 503 SERVICE_UNAVAILABLE

Plus framework exceptions:
    RequestValidationError  → 422 REQUEST_VALIDATION_ERROR
    StarletteHTTPException  → pass-through with envelope
    Exception (unhandled)   → 500 INTERNAL_ERROR + traceback log
```

All error responses share the same JSON envelope — clients only need one error handler.

---

## Configuration Architecture

```
Environment Variables / .env file
    │
    ▼
app/config.py  (Pydantic BaseSettings)
    │
    ├── @lru_cache → singleton Settings instance
    │
    └── Injected via Depends(get_settings)
```

Tests clear the cache with `get_settings.cache_clear()` and provide overridden Settings.

---

## Testing Architecture

```
tests/
├── unit/         No DB, no network. Services tested with mocked sessions.
├── integration/  Real PostgreSQL (test DB). Uses create_tables + SAVEPOINT isolation.
└── e2e/          (Phase 2) Full pipeline from observation ingest to alert.
```

### Test isolation strategy

```
Session start: CREATE all tables
    │
    ├── Test 1:
    │     BEGIN TRANSACTION
    │     ├── SAVEPOINT sp1
    │     │   test runs
    │     └── ROLLBACK TO sp1
    │
    ├── Test 2: (same session, clean state)
    │     SAVEPOINT sp2 ...
    │
Session end: DROP all tables
```

This avoids slow table truncation while guaranteeing isolation.

---

## Docker Architecture

```
docker-compose services:

  db (postgis/postgis:16-3.4-alpine)
    └── healthcheck: pg_isready
    └── volume: postgres_data

  redis (redis:7.4-alpine)
    └── healthcheck: redis-cli ping
    └── volume: redis_data

  migrate (runtime image, one-shot)
    └── depends_on: db (healthy)
    └── runs: alembic upgrade head
    └── exits with 0 on success

  api (runtime image)
    └── depends_on: db (healthy), redis (healthy), migrate (completed)
    └── runs: uvicorn app.main:app
    └── healthcheck: GET /api/v1/health
```

The `migrate` service ensures migrations always run before the API starts. On subsequent `docker compose up`, if there are no new migrations, it completes instantly.

---

## Future Architecture (Phase 2+)

### Async Worker Architecture

```
Observation Ingest API
    │
    └── Enqueue "observation.created" to Redis
            │
            ├── Matching Worker (reads queue)
            │       → Scores candidates
            │       → Creates VehicleMatch + updates VehicleIdentity
            │
            └── Blacklist Worker (reads queue)
                    → Checks plate against blacklist
                    → Creates Alert if matched
```

### AI Integration

```
AI Pipeline (external process)
    │
    └── POST /api/v1/observations/ingest
            │
            └── VehicleObservation + PlateObservation created
```

The AI pipeline is decoupled — it calls the REST API. No AI code lives in the domain layer.
