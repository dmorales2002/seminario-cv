"""Add phase 4 analysis engine fields.

Revision ID: c5b7194d2e08
Revises: a3f24c8e7b11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c5b7194d2e08"
down_revision: Union[str, Sequence[str], None] = "a3f24c8e7b11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vacancies", sa.Column("ai_criteria", postgresql.JSONB(), nullable=True))
    op.add_column("vacancies", sa.Column("criteria_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("resumes", sa.Column("extracted_profile", postgresql.JSONB(), nullable=True))
    op.add_column("resumes", sa.Column("profile_extracted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("applications", sa.Column("analysis_status", sa.String(length=20), server_default="PENDING", nullable=False))
    op.add_column("applications", sa.Column("analysis_error", sa.Text(), nullable=True))
    op.add_column("applications", sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("applications", sa.Column("analyzer_version", sa.String(length=100), nullable=True))
    op.create_check_constraint(
        "ck_application_analysis_status",
        "applications",
        "analysis_status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_application_analysis_status", "applications", type_="check")
    op.drop_column("applications", "analyzer_version")
    op.drop_column("applications", "analyzed_at")
    op.drop_column("applications", "analysis_error")
    op.drop_column("applications", "analysis_status")
    op.drop_column("resumes", "profile_extracted_at")
    op.drop_column("resumes", "extracted_profile")
    op.drop_column("vacancies", "criteria_updated_at")
    op.drop_column("vacancies", "ai_criteria")
