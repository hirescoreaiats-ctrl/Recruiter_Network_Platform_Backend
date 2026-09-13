"""Add staged requirement sourcing plans.

Revision ID: 8c14f7a9d2e1
Revises: 71d9a34c2e10
Create Date: 2026-09-13
"""
from alembic import op
import sqlalchemy as sa


revision = "8c14f7a9d2e1"
down_revision = "71d9a34c2e10"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "requirement_sourcing_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("requirement_id", sa.Integer(), nullable=False),
        sa.Column("portal_status", sa.String(length=30), nullable=False),
        sa.Column("portal_match_count", sa.Integer(), nullable=False),
        sa.Column("database_status", sa.String(length=30), nullable=False),
        sa.Column("database_match_count", sa.Integer(), nullable=False),
        sa.Column("object_storage_match_count", sa.Integer(), nullable=False),
        sa.Column("external_status", sa.String(length=30), nullable=False),
        sa.Column("current_stage", sa.String(length=40), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("last_scanned_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by_user_id", sa.Integer(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requirement_id"),
    )
    with op.batch_alter_table("requirement_sourcing_plans") as batch:
        batch.create_index(batch.f("ix_requirement_sourcing_plans_external_status"), ["external_status"], unique=False)
        batch.create_index(batch.f("ix_requirement_sourcing_plans_requirement_id"), ["requirement_id"], unique=True)


def downgrade():
    with op.batch_alter_table("requirement_sourcing_plans") as batch:
        batch.drop_index(batch.f("ix_requirement_sourcing_plans_requirement_id"))
        batch.drop_index(batch.f("ix_requirement_sourcing_plans_external_status"))
    op.drop_table("requirement_sourcing_plans")
