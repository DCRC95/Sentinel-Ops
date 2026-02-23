"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-02-23 15:10:00
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contractors",
        sa.Column("contractor_id", sa.String(length=36), nullable=False),
        sa.Column("handle", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("contractor_id"),
    )

    op.create_table(
        "cases",
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deadline_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint("case_id"),
    )

    op.create_table(
        "submissions",
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column("contractor_id", sa.String(length=36), nullable=False),
        sa.Column("chain", sa.String(length=8), nullable=False),
        sa.Column("address", sa.String(length=256), nullable=False),
        sa.Column("scam_type", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.String(length=1024), nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload_json", sa.Text(), nullable=False),
        sa.Column("submission_hash", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["case_id"], ["cases.case_id"]),
        sa.ForeignKeyConstraint(["contractor_id"], ["contractors.contractor_id"]),
        sa.PrimaryKeyConstraint("submission_id"),
    )

    op.create_table(
        "submission_events",
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("event_payload_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.submission_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )


def downgrade() -> None:
    op.drop_table("submission_events")
    op.drop_table("submissions")
    op.drop_table("cases")
    op.drop_table("contractors")
