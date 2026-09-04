"""Employer product mode and detailed company onboarding."""
from alembic import op
import sqlalchemy as sa

revision = "58aeb6401c32"
down_revision = "4b7a2d91c6ef"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("companies") as batch:
        batch.add_column(sa.Column("product_mode", sa.String(20), nullable=False, server_default="complete"))
        batch.add_column(sa.Column("company_size", sa.String(40), nullable=True))
        batch.add_column(sa.Column("industry", sa.String(160), nullable=True))
        batch.add_column(sa.Column("hiring_requirements", sa.Text(), nullable=True))
        batch.add_column(sa.Column("consent_accepted_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("companies") as batch:
        for name in ["consent_accepted_at", "hiring_requirements", "industry", "company_size", "product_mode"]:
            batch.drop_column(name)
