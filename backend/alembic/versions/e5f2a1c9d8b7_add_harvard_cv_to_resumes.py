"""Add harvard_cv column to resumes.

Revision ID: e5f2a1c9d8b7
Revises: c5b7194d2e08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e5f2a1c9d8b7"
down_revision: Union[str, Sequence[str], None] = "c5b7194d2e08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("harvard_cv", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "harvard_cv")