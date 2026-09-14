"""Add vendor interview schedules.

Revision ID: b18f62dc021a
Revises: 8c14f7a9d2e1
Create Date: 2026-09-14
"""
from alembic import op
import sqlalchemy as sa


revision = "b18f62dc021a"
down_revision = "8c14f7a9d2e1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "interview_schedules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("interview_round", sa.String(length=80), nullable=False),
        sa.Column("interviewer_name", sa.String(length=160), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("meeting_type", sa.String(length=40), nullable=False),
        sa.Column("meeting_link", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["application_id"], ["applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("interview_schedules") as batch:
        batch.create_index(batch.f("ix_interview_schedules_application_id"), ["application_id"], unique=False)
        batch.create_index(batch.f("ix_interview_schedules_created_by_user_id"), ["created_by_user_id"], unique=False)
        batch.create_index(batch.f("ix_interview_schedules_scheduled_at"), ["scheduled_at"], unique=False)
        batch.create_index(batch.f("ix_interview_schedules_status"), ["status"], unique=False)


def downgrade():
    with op.batch_alter_table("interview_schedules") as batch:
        batch.drop_index(batch.f("ix_interview_schedules_status"))
        batch.drop_index(batch.f("ix_interview_schedules_scheduled_at"))
        batch.drop_index(batch.f("ix_interview_schedules_created_by_user_id"))
        batch.drop_index(batch.f("ix_interview_schedules_application_id"))
    op.drop_table("interview_schedules")
