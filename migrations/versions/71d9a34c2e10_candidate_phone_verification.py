"""Candidate mobile verification status."""
from alembic import op
import sqlalchemy as sa

revision = "71d9a34c2e10"
down_revision = "58aeb6401c32"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("phone_verified_at", sa.DateTime(), nullable=True))
    # Existing candidate accounts predate the OTP flow and must keep their access.
    op.execute("UPDATE users SET phone_verified_at = created_at WHERE role = 'candidate'")


def downgrade():
    with op.batch_alter_table("users") as batch:
        batch.drop_column("phone_verified_at")
