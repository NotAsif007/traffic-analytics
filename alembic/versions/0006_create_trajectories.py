"""Create trajectories and trajectory_points tables

Revision ID: 0006_create_trajectories
Revises: 0005_create_vehicle_identities
Create Date: 2026-08-30 17:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_create_trajectories"
down_revision: str | None = "0005_create_vehicle_identities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # trajectories
    # -----------------------------------------------------------------------
    op.create_table(
        "trajectories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trajectory_id", sa.String(64), nullable=False),
        sa.Column("vehicle_identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0.8"),
        sa.Column("total_distance_m", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("total_travel_time_s", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("average_speed_kmh", sa.Numeric(6, 2), nullable=True),
        sa.Column("points_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("ordered_camera_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("ordered_camera_names", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "route_geometry",
            geoalchemy2.types.Geometry(
                geometry_type="LINESTRING",
                srid=4326,
                from_text="ST_GeomFromEWKT",
                name="geometry",
            ),
            nullable=True,
        ),
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
        sa.CheckConstraint(
            "start_time <= end_time",
            name="ck_trajectories_time_order",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'terminated')",
            name="ck_trajectories_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_trajectories_confidence",
        ),
        sa.CheckConstraint(
            "total_distance_m >= 0",
            name="ck_trajectories_distance_positive",
        ),
        sa.CheckConstraint(
            "total_travel_time_s >= 0",
            name="ck_trajectories_time_positive",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_identity_id"], ["vehicle_identities.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trajectory_id", name="uq_trajectories_trajectory_id"),
    )

    op.create_index("ix_trajectories_trajectory_id", "trajectories", ["trajectory_id"], unique=True)
    op.create_index("ix_trajectories_vehicle_identity_id", "trajectories", ["vehicle_identity_id"])
    op.create_index("ix_trajectories_start_time", "trajectories", ["start_time"])
    op.create_index("ix_trajectories_end_time", "trajectories", ["end_time"])
    op.create_index("ix_trajectories_status", "trajectories", ["status"])
    op.create_index(
        "ix_trajectories_identity_time",
        "trajectories",
        ["vehicle_identity_id", "start_time", "end_time"],
    )

    # -----------------------------------------------------------------------
    # trajectory_points
    # -----------------------------------------------------------------------
    op.create_table(
        "trajectory_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trajectory_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("plate_text", sa.String(20), nullable=True),
        sa.Column("plate_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("speed_kmh", sa.Numeric(6, 2), nullable=True),
        sa.Column("segment_distance_m", sa.Float(), nullable=True),
        sa.Column("segment_duration_s", sa.Float(), nullable=True),
        sa.Column("is_interpolated", sa.Boolean(), nullable=False, server_default="false"),
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
            "sequence_order >= 1",
            name="ck_trajectory_points_sequence_order",
        ),
        sa.ForeignKeyConstraint(["trajectory_id"], ["trajectories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["vehicle_observations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["track_id"], ["vehicle_tracks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_trajectory_points_trajectory_id", "trajectory_points", ["trajectory_id"])
    op.create_index("ix_trajectory_points_camera_id", "trajectory_points", ["camera_id"])
    op.create_index("ix_trajectory_points_timestamp", "trajectory_points", ["timestamp"])
    op.create_index(
        "ix_trajectory_points_traj_seq",
        "trajectory_points",
        ["trajectory_id", "sequence_order"],
    )


def downgrade() -> None:
    op.drop_table("trajectory_points")
    op.drop_table("trajectories")
