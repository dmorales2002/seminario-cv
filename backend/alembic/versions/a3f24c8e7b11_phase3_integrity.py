"""Complete phase 3 vacancy and application integrity.

Revision ID: a3f24c8e7b11
Revises: 915d079f2d49
"""
from typing import Sequence, Union

from alembic import op

revision: str = "a3f24c8e7b11"
down_revision: Union[str, Sequence[str], None] = "915d079f2d49"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE vacancystatus ADD VALUE IF NOT EXISTS 'PAUSED'")
    op.create_unique_constraint(
        "uq_application_vacancy_candidate",
        "applications",
        ["vacancy_id", "candidate_id"],
    )
    op.create_check_constraint(
        "ck_application_ai_score",
        "applications",
        "ai_score IS NULL OR (ai_score >= 0 AND ai_score <= 100)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_application_ai_score", "applications", type_="check")
    op.drop_constraint("uq_application_vacancy_candidate", "applications", type_="unique")
    # PostgreSQL cannot remove an enum value safely in place. PAUSED is retained.
