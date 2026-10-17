"""Store the original resume file in the database instead of a public blob URL.

Revision ID: f7a1d3c9b2e4
Revises: dac55688d5c4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f7a1d3c9b2e4"
down_revision: Union[str, Sequence[str], None] = "dac55688d5c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resumes", sa.Column("file_data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("resumes", "file_data")
