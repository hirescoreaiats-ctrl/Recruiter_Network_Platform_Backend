"""Repair the one constraint missed by an interrupted local SQLite migration."""

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect

from app.database import engine


def repair():
    if engine.dialect.name != "sqlite":
        print("No repair needed: database is not SQLite.")
        return
    with engine.begin() as connection:
        foreign_keys = inspect(connection).get_foreign_keys("requirement_partners")
        if any(fk.get("referred_table") == "requirement_commercial_terms" for fk in foreign_keys):
            print("Accepted-terms foreign key is already present.")
            return
        operations = Operations(MigrationContext.configure(connection))
        with operations.batch_alter_table("requirement_partners") as batch:
            batch.create_foreign_key(
                "fk_requirement_partners_accepted_terms",
                "requirement_commercial_terms",
                ["accepted_commercial_terms_id"],
                ["id"],
            )
    print("Accepted-terms foreign key repaired without resetting data.")


if __name__ == "__main__":
    repair()
