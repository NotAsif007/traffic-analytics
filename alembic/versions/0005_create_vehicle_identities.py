"""Create vehicle_identities and vehicle_matches tables

Revision ID: 0005_create_vehicle_identities
Revises: 0004_create_vehicle_tracks
Create Date: 2026-08-30 16:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_create_vehicle_identities"
down_revision: str | None = "0004_create_vehicle_tracks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # vehicle_identities
    # -----------------------------------------------------------------------
    op.create_table(
        "vehicle_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("identity_code", sa.String(64), nullable=False),
        sa.Column("primary_plate", sa.String(20), nullable=True),
        sa.Column("plate_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("vehicle_class", sa.String(64), nullable=True),
        sa.Column("vehicle_color", sa.String(32), nullable=True),
        sa.Column("vehicle_make", sa.String(64), nullable=True),
        sa.Column("vehicle_model", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="candidate"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_sightings", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0.5"),
        sa.Column("reid_embedding_id", sa.String(128), nullable=True),
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
            "first_seen_at <= last_seen_at",
            name="ck_vehicle_identities_time_order",
        ),
        sa.CheckConstraint(
            "status IN ('candidate', 'accepted', 'rejected', 'needs_review')",
            name="ck_vehicle_identities_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_vehicle_identities_confidence",
        ),
        sa.CheckConstraint(
            "plate_confidence IS NULL OR (plate_confidence >= 0 AND plate_confidence <= 1)",
            name="ck_vehicle_identities_plate_confidence",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("identity_code", name="uq_vehicle_identities_identity_code"),
    )

    op.create_index("ix_vehicle_identities_identity_code", "vehicle_identities", ["identity_code"], unique=True)
    op.create_index("ix_vehicle_identities_primary_plate", "vehicle_identities", ["primary_plate"])
    op.create_index("ix_vehicle_identities_status", "vehicle_identities", ["status"])
    op.create_index("ix_vehicle_identities_first_seen_at", "vehicle_identities", ["first_seen_at"])
    op.create_index("ix_vehicle_identities_last_seen_at", "vehicle_identities", ["last_seen_at"])
    op.create_index("ix_vehicle_identities_vehicle_class", "vehicle_identities", ["vehicle_class"])

    # -----------------------------------------------------------------------
    # vehicle_matches
    # -----------------------------------------------------------------------
    op.create_table(
        "vehicle_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vehicle_identity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_observation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_track_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_observation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_track_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("target_camera_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("match_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="accepted"),
        sa.Column("signals", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
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
            "match_score >= 0 AND match_score <= 1",
            name="ck_vehicle_matches_match_score",
        ),
        sa.CheckConstraint(
            "status IN ('candidate', 'accepted', 'rejected', 'needs_review')",
            name="ck_vehicle_matches_status",
        ),
        sa.ForeignKeyConstraint(
            ["vehicle_identity_id"], ["vehicle_identities.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["source_observation_id"], ["vehicle_observations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_observation_id"], ["vehicle_observations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["source_track_id"], ["vehicle_tracks.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["target_track_id"], ["vehicle_tracks.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["source_camera_id"], ["cameras.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_camera_id"], ["cameras.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_vehicle_matches_identity_id", "vehicle_matches", ["vehicle_identity_id"])
    op.create_index("ix_vehicle_matches_status", "vehicle_matches", ["status"])
    op.create_index(
        "ix_vehicle_matches_cameras",
        "vehicle_matches",
        ["source_camera_id", "target_camera_id"],
    )


def downgrade() -> None:
    op.drop_table("vehicle_matches")
    op.drop_table("vehicle_identities")
