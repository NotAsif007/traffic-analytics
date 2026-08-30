"""
Alembic environment configuration.

Key behaviours:
- DSN is read from the ALEMBIC_DATABASE_URL environment variable (sync psycopg2)
- All SQLAlchemy models are imported so Alembic can detect schema changes
- GeoAlchemy2 types are registered for PostGIS column support
- Supports both offline (SQL script) and online (live DB) migration modes
"""

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# Make sure the project root is importable
# ---------------------------------------------------------------------------
# When alembic is run from the project root, `app` is on the path.
# This guard handles cases where it's run from a different directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Import the declarative base and ALL models
# ---------------------------------------------------------------------------
# Every model module must be imported here so Alembic can see the tables.
# Import the Base AFTER models so the metadata is populated.
from app.db.base import Base  # noqa: E402

# Import all model modules to populate Base.metadata
import app.models  # noqa: E402, F401 — registers Road, Camera, CameraConnection

# ---------------------------------------------------------------------------
# Alembic Config
# ---------------------------------------------------------------------------
config = context.config

# Apply logging configuration from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use our declarative base's metadata for autogenerate
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Read DSN from environment (never from alembic.ini)
# ---------------------------------------------------------------------------
def get_url() -> str:
    url = os.environ.get("ALEMBIC_DATABASE_URL")
    if not url:
        raise ValueError(
            "ALEMBIC_DATABASE_URL environment variable is not set. "
            "Set it to a synchronous psycopg2 DSN: "
            "postgresql+psycopg2://user:pass@host:port/db"
        )
    return url


# ---------------------------------------------------------------------------
# Offline mode — generates SQL script without connecting to DB
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Compare server defaults to detect changes
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — connects to the DB and runs migrations
# ---------------------------------------------------------------------------
def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # No connection pooling for migration runs
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
