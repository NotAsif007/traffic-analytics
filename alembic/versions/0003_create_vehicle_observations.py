"""Create vehicle_observations table

Revision ID: 0003_create_vehicle_observations
Revises: 0002_create_roads_cameras
Create Date: 2026-08-30 14:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_create_vehicle_observations"
down_revision: str | None = "0002_create_roads_cameras"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Enable pg_trgm for fuzzy/partial plate text search
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "vehicle_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        # Source / idempotency
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_observation_id", sa.String(128), nullable=False),
        # Camera
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        # Temporal
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frame_number", sa.Integer(), nullable=True),
        # Vehicle detection
        sa.Column("vehicle_class", sa.String(64), nullable=True),
        sa.Column("vehicle_color", sa.String(32), nullable=True),
        sa.Column("bounding_box", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("detection_confidence", sa.Numeric(5, 4), nullable=True),
        # Plate reading
        sa.Column("plate_text", sa.String(20), nullable=True),
        sa.Column("plate_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("plate_bbox", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("plate_region", sa.String(16), nullable=True),
        # Media references
        sa.Column("frame_path", sa.String(512), nullable=True),
        sa.Column("crop_path", sa.String(512), nullable=True),
        sa.Column("plate_crop_path", sa.String(512), nullable=True),
        # Embedding reference
        sa.Column("embedding_id", sa.String(128), nullable=True),
        sa.Column("embedding_model", sa.String(64), nullable=True),
        # Kinematics
        sa.Column("estimated_speed_kmh", sa.Numeric(6, 2), nullable=True),
        sa.Column("direction", sa.String(32), nullable=True),
        sa.Column("lane", sa.Integer(), nullable=True),
        # Lifecycle
        sa.Column("status", sa.String(32), nullable=False, server_default="detected"),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        # Metadata
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        # Audit timestamps
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
        # Constraints
        sa.CheckConstraint(
            "detection_confidence IS NULL OR (detection_confidence >= 0 AND detection_confidence <= 1)",
            name="ck_vehicle_obs_detection_confidence",
        ),
        sa.CheckConstraint(
            "plate_confidence IS NULL OR (plate_confidence >= 0 AND plate_confidence <= 1)",
            name="ck_vehicle_obs_plate_confidence",
        ),
        sa.CheckConstraint(
            "status IN ('detected', 'processed', 'validated', 'associated', 'rejected')",
            name="ck_vehicle_obs_status",
        ),
        sa.CheckConstraint(
            "estimated_speed_kmh IS NULL OR estimated_speed_kmh >= 0",
            name="ck_vehicle_obs_speed_positive",
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Idempotency index — unique per (source, source_observation_id)
    op.create_index(
        "uix_vehicle_obs_source_obs_id",
        "vehicle_observations",
        ["source", "source_observation_id"],
        unique=True,
    )

    # Compound index for time-range queries per camera
    op.create_index(
        "ix_vehicle_obs_camera_time",
        "vehicle_observations",
        ["camera_id", "observed_at"],
    )

    # Individual column indexes
    op.create_index("ix_vehicle_obs_source", "vehicle_observations", ["source"])
    op.create_index("ix_vehicle_obs_observed_at", "vehicle_observations", ["observed_at"])
    op.create_index("ix_vehicle_obs_vehicle_class", "vehicle_observations", ["vehicle_class"])
    op.create_index("ix_vehicle_obs_plate_text", "vehicle_observations", ["plate_text"])
    op.create_index("ix_vehicle_obs_status", "vehicle_observations", ["status"])

    # Trigram index on plate_text for fast ILIKE / partial-match queries
    op.create_index(
        "ix_vehicle_obs_plate_text_trgm",
        "vehicle_observations",
        ["plate_text"],
        postgresql_using="gin",
        postgresql_ops={"plate_text": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_table("vehicle_observations")
