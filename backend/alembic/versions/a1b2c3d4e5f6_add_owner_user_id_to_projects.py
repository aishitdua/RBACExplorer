"""add owner_user_id to projects

Revision ID: a1b2c3d4e5f6
Revises: e54c4c2d9945
Create Date: 2026-04-26 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "e54c4c2d9945"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add owner_user_id column (nullable so existing rows survive)
    op.add_column(
        "projects",
        sa.Column("owner_user_id", sa.String(256), nullable=True),
    )
    op.create_index("ix_projects_owner_user_id", "projects", ["owner_user_id"])

    # Drop the old single-column unique constraint on slug
    op.drop_constraint("projects_slug_key", "projects", type_="unique")

    # Add the new composite unique constraint on (owner_user_id, slug)
    op.create_unique_constraint(
        "uq_projects_owner_slug", "projects", ["owner_user_id", "slug"]
    )


def downgrade() -> None:
    # Remove composite constraint
    op.drop_constraint("uq_projects_owner_slug", "projects", type_="unique")

    # Restore original single-column unique constraint on slug
    op.create_unique_constraint("projects_slug_key", "projects", ["slug"])

    # Drop index and column
    op.drop_index("ix_projects_owner_user_id", table_name="projects")
    op.drop_column("projects", "owner_user_id")
