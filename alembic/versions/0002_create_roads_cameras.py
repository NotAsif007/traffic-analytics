"""Create roads, cameras, camera_connections tables

Revision ID: 0002_create_roads_cameras
Revises: 0001_enable_postgis
Create Date: 2026-08-30 13:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects import postgresql

revision: str = "0002_create_roads_cameras"
down_revision: str | None = "0001_enable_postgis"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # roads
    # -----------------------------------------------------------------------
    op.create_table(
        "roads",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("road_type", sa.String(64), nullable=True),
        sa.Column(
            "geometry",
            Geometry(geometry_type="LINESTRING", srid=4326),
            nullable=True,
        ),
        sa.Column("direction", sa.String(32), nullable=True),
        sa.Column("speed_limit_kmh", sa.Integer(), nullable=True),
        sa.Column("lane_count", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_roads_name", "roads", ["name"])
    op.create_index("ix_roads_external_id", "roads", ["external_id"])
    op.create_index("ix_roads_geometry", "roads", ["geometry"], postgresql_using="gist")

    # -----------------------------------------------------------------------
    # cameras
    # -----------------------------------------------------------------------
    op.create_table(
        "cameras",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("camera_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "location",
            Geometry(geometry_type="POINT", srid=4326),
            nullable=True,
        ),
        sa.Column("road_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("direction", sa.String(32), nullable=True),
        sa.Column("fov_degrees", sa.Integer(), nullable=True),
        sa.Column("lane_count", sa.Integer(), nullable=True),
        sa.Column("lane_coverage", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("timezone", sa.String(64), nullable=False, server_default="Asia/Kolkata"),
        sa.Column("height_m", sa.Integer(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["road_id"], ["roads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("camera_id", name="uq_cameras_camera_id"),
    )
    op.create_index("ix_cameras_camera_id", "cameras", ["camera_id"], unique=True)
    op.create_index("ix_cameras_road_id", "cameras", ["road_id"])
    op.create_index("ix_cameras_status", "cameras", ["status"])
    op.create_index("ix_cameras_location", "cameras", ["location"], postgresql_using="gist")

    # -----------------------------------------------------------------------
    # camera_connections
    # -----------------------------------------------------------------------
    op.create_table(
        "camera_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("destination_camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("road_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("min_travel_time_s", sa.Integer(), nullable=False),
        sa.Column("max_travel_time_s", sa.Integer(), nullable=False),
        sa.Column("avg_travel_time_s", sa.Integer(), nullable=True),
        sa.Column("distance_m", sa.Numeric(10, 2), nullable=True),
        sa.Column("connection_type", sa.String(32), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_camera_id <> destination_camera_id",
            name="ck_camera_connections_no_self_loop",
        ),
        sa.CheckConstraint(
            "min_travel_time_s > 0",
            name="ck_camera_connections_min_travel_positive",
        ),
        sa.CheckConstraint(
            "max_travel_time_s > 0",
            name="ck_camera_connections_max_travel_positive",
        ),
        sa.CheckConstraint(
            "min_travel_time_s <= max_travel_time_s",
            name="ck_camera_connections_travel_time_order",
        ),
        sa.CheckConstraint(
            "distance_m IS NULL OR distance_m > 0",
            name="ck_camera_connections_distance_positive",
        ),
        sa.ForeignKeyConstraint(["source_camera_id"], ["cameras.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["destination_camera_id"], ["cameras.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["road_id"], ["roads.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_camera_connections_source_camera_id",
        "camera_connections",
        ["source_camera_id"],
    )
    op.create_index(
        "ix_camera_connections_destination_camera_id",
        "camera_connections",
        ["destination_camera_id"],
    )
    op.create_index(
        "uix_camera_connections_source_dest",
        "camera_connections",
        ["source_camera_id", "destination_camera_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("camera_connections")
    op.drop_table("cameras")
    op.drop_table("roads")
