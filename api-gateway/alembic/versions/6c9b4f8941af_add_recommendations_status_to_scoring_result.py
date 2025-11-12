"""add_recommendations_status_to_scoring_result

Revision ID: 6c9b4f8941af
Revises: db797a3f587a
Create Date: 2025-11-12 12:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "6c9b4f8941af"
down_revision: Union[str, None] = "db797a3f587a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scoring_result",
        sa.Column(
            "recommendations_status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "scoring_result",
        sa.Column("recommendations_error", sa.Text(), nullable=True),
    )

    op.create_check_constraint(
        "scoring_result_recommendations_status_check",
        "scoring_result",
        "recommendations_status IN ('pending', 'ready', 'error', 'disabled')",
    )

    # Mark existing records with recommendations as ready
    op.execute(
        "UPDATE scoring_result SET recommendations_status = 'ready' "
        "WHERE recommendations IS NOT NULL AND jsonb_array_length(recommendations) > 0"
    )


def downgrade() -> None:
    op.drop_constraint(
        "scoring_result_recommendations_status_check",
        "scoring_result",
        type_="check",
    )
    op.drop_column("scoring_result", "recommendations_error")
    op.drop_column("scoring_result", "recommendations_status")

