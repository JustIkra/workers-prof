"""add_metric_def_name_ru

Revision ID: f8d4d2f6244a
Revises: 6c9b4f8941af
Create Date: 2025-11-13 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from app.services.metric_localization import METRIC_DISPLAY_NAMES_RU

# revision identifiers, used by Alembic.
revision: str = "f8d4d2f6244a"
down_revision: Union[str, None] = "6c9b4f8941af"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "metric_def",
        sa.Column("name_ru", sa.String(length=255), nullable=True),
    )

    connection = op.get_bind()
    update_stmt = sa.text(
        "UPDATE metric_def SET name_ru = :name_ru "
        "WHERE code = :code AND (name_ru IS NULL OR name_ru = '')"
    )
    for code, display_name in METRIC_DISPLAY_NAMES_RU.items():
        connection.execute(update_stmt, {"name_ru": display_name, "code": code})

    # Fallback: copy existing name into name_ru when mapping is missing
    connection.execute(
        sa.text(
            "UPDATE metric_def SET name_ru = name WHERE name_ru IS NULL OR name_ru = ''"
        )
    )


def downgrade() -> None:
    op.drop_column("metric_def", "name_ru")



