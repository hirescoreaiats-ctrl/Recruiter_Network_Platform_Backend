"""candidate job preferences

Revision ID: 4b7a2d91c6ef
Revises: 3ce10ed55bd1
Create Date: 2026-08-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4b7a2d91c6ef"
down_revision: Union[str, Sequence[str], None] = "3ce10ed55bd1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_job_preferences",
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("query_text", sa.Text(), nullable=True),
        sa.Column("desired_titles", sa.Text(), nullable=False),
        sa.Column("skills", sa.Text(), nullable=False),
        sa.Column("countries", sa.Text(), nullable=False),
        sa.Column("locations", sa.Text(), nullable=False),
        sa.Column("work_modes", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("candidate_profile_id"),
    )
    with op.batch_alter_table("candidate_job_preferences", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_candidate_job_preferences_status"), ["status"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("candidate_job_preferences", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_candidate_job_preferences_status"))
    op.drop_table("candidate_job_preferences")
