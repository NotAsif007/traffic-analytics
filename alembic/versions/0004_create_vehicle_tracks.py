"""Create vehicle_tracks and track_points tables

Revision ID: 0004_create_vehicle_tracks
Revises: 0003_create_vehicle_observations
Create Date: 2026-08-30 15:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_create_vehicle_tracks"
down_revision: str | None = "0003_create_vehicle_observations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # vehicle_tracks
    # -----------------------------------------------------------------------
    op.create_table(
        "vehicle_tracks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_id", sa.String(64), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0.0"),
        sa.Column("vehicle_class", sa.String(64), nullable=True),
        sa.Column("vehicle_color", sa.String(32), nullable=True),
        sa.Column("best_plate_text", sa.String(20), nullable=True),
        sa.Column("best_plate_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("points_count", sa.Integer(), nullable=False, server_default="0"),
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
            name="ck_vehicle_tracks_time_order",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'lost', 'terminated')",
            name="ck_vehicle_tracks_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_vehicle_tracks_confidence",
        ),
        sa.CheckConstraint(
            "best_plate_confidence IS NULL OR (best_plate_confidence >= 0 AND best_plate_confidence <= 1)",
            name="ck_vehicle_tracks_best_plate_confidence",
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_vehicle_tracks_track_id", "vehicle_tracks", ["track_id"])
    op.create_index("ix_vehicle_tracks_camera_id", "vehicle_tracks", ["camera_id"])
    op.create_index("ix_vehicle_tracks_start_time", "vehicle_tracks", ["start_time"])
    op.create_index("ix_vehicle_tracks_end_time", "vehicle_tracks", ["end_time"])
    op.create_index("ix_vehicle_tracks_status", "vehicle_tracks", ["status"])
    op.create_index("ix_vehicle_tracks_vehicle_class", "vehicle_tracks", ["vehicle_class"])
    op.create_index("ix_vehicle_tracks_best_plate_text", "vehicle_tracks", ["best_plate_text"])
    op.create_index(
        "ix_vehicle_tracks_camera_time",
        "vehicle_tracks",
        ["camera_id", "start_time", "end_time"],
    )

    # -----------------------------------------------------------------------
    # track_points
    # -----------------------------------------------------------------------
    op.create_table(
        "track_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("track_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frame_number", sa.Integer(), nullable=True),
        sa.Column("bounding_box", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="1.0"),
        sa.Column("estimated_speed_kmh", sa.Numeric(6, 2), nullable=True),
        sa.Column("plate_text", sa.String(20), nullable=True),
        sa.Column("plate_confidence", sa.Numeric(5, 4), nullable=True),
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
            "confidence >= 0 AND confidence <= 1",
            name="ck_track_points_confidence",
        ),
        sa.CheckConstraint(
            "plate_confidence IS NULL OR (plate_confidence >= 0 AND plate_confidence <= 1)",
            name="ck_track_points_plate_confidence",
        ),
        sa.ForeignKeyConstraint(["track_id"], ["vehicle_tracks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["vehicle_observations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_track_points_track_id", "track_points", ["track_id"])
    op.create_index("ix_track_points_observation_id", "track_points", ["observation_id"])
    op.create_index("ix_track_points_camera_id", "track_points", ["camera_id"])
    op.create_index("ix_track_points_timestamp", "track_points", ["timestamp"])
    op.create_index(
        "ix_track_points_track_time",
        "track_points",
        ["track_id", "timestamp"],
    )


def downgrade() -> None:
    op.drop_table("track_points")
    op.drop_table("vehicle_tracks")
