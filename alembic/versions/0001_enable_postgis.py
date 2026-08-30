"""Enable PostGIS extension

This is the first migration and must run before any spatial tables are created.
It enables the PostGIS extension in PostgreSQL, which provides the geometry
types (POINT, LINESTRING, POLYGON, etc.) used throughout this project.

The postgis/postgis Docker image already has the extension available;
this migration activates it in the target database.

Revision ID: 0001
Revises: (none — this is the initial revision)
Create Date: 2026-08-30 12:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_enable_postgis"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Enable the PostGIS extension."""
    # CREATE EXTENSION IF NOT EXISTS is idempotent and safe to run multiple times.
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")
    # pgcrypto provides gen_random_uuid() as a fallback for older PostgreSQL versions
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")


def downgrade() -> None:
    """
    Drop PostGIS extension.

    WARNING: This will fail if any tables use geometry columns.
    Downgrade is provided for completeness but should not be run in production.
    """
    op.execute("DROP EXTENSION IF EXISTS postgis_topology")
    op.execute("DROP EXTENSION IF EXISTS postgis CASCADE")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
