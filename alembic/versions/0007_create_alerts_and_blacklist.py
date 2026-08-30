"""Create blacklist_entries and alerts tables

Revision ID: 0007_create_alerts_and_blacklist
Revises: 0006_create_trajectories
Create Date: 2026-08-30 18:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_create_alerts_and_blacklist"
down_revision: str | None = "0006_create_trajectories"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # blacklist_entries
    # -----------------------------------------------------------------------
    op.create_table(
        "blacklist_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("plate_text", sa.String(20), nullable=False),
        sa.Column("reason", sa.String(255), nullable=False),
        sa.Column("priority", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
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
            "priority IN ('low', 'medium', 'high', 'critical')",
            name="ck_blacklist_entries_priority",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_blacklist_entries_plate_text", "blacklist_entries", ["plate_text"])
    op.create_index("ix_blacklist_entries_priority", "blacklist_entries", ["priority"])
    op.create_index("ix_blacklist_entries_is_active", "blacklist_entries", ["is_active"])
    op.create_index(
        "ix_blacklist_active_plate",
        "blacklist_entries",
        ["plate_text", "is_active"],
    )

    # -----------------------------------------------------------------------
    # alerts
    # -----------------------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("alert_code", sa.String(64), nullable=False),
        sa.Column("alert_type", sa.String(64), nullable=False),
        sa.Column("severity", sa.String(32), nullable=False, server_default="medium"),
        sa.Column("status", sa.String(32), nullable=False, server_default="NEW"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0.9"),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("camera_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("vehicle_identity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trajectory_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("observation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("blacklist_entry_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("evidence", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("acknowledged_by", sa.String(128), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.String(128), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_by", sa.String(128), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
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
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="ck_alerts_severity",
        ),
        sa.CheckConstraint(
            "status IN ('NEW', 'ACKNOWLEDGED', 'RESOLVED', 'DISMISSED')",
            name="ck_alerts_status",
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1",
            name="ck_alerts_confidence",
        ),
        sa.ForeignKeyConstraint(["camera_id"], ["cameras.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["vehicle_identity_id"], ["vehicle_identities.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["trajectory_id"], ["trajectories.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["observation_id"], ["vehicle_observations.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["blacklist_entry_id"], ["blacklist_entries.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_code", name="uq_alerts_alert_code"),
    )

    op.create_index("ix_alerts_alert_code", "alerts", ["alert_code"], unique=True)
    op.create_index("ix_alerts_alert_type", "alerts", ["alert_type"])
    op.create_index("ix_alerts_severity", "alerts", ["severity"])
    op.create_index("ix_alerts_status", "alerts", ["status"])
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])
    op.create_index("ix_alerts_type_status", "alerts", ["alert_type", "status"])


def downgrade() -> None:
    op.drop_table("alerts")
    op.drop_table("blacklist_entries")
