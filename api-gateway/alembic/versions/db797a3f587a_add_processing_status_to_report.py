"""add_processing_status_to_report

Revision ID: db797a3f587a
Revises: 3f65e4700d4a
Create Date: 2025-11-11 11:07:59.973928

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db797a3f587a'
down_revision: Union[str, None] = '3f65e4700d4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old CHECK constraint
    op.drop_constraint('report_status_check', 'report', type_='check')

    # Create new CHECK constraint with PROCESSING status
    op.create_check_constraint(
        'report_status_check',
        'report',
        "status IN ('UPLOADED', 'PROCESSING', 'EXTRACTED', 'FAILED')"
    )


def downgrade() -> None:
    # Drop new CHECK constraint
    op.drop_constraint('report_status_check', 'report', type_='check')

    # Restore old CHECK constraint without PROCESSING
    op.create_check_constraint(
        'report_status_check',
        'report',
        "status IN ('UPLOADED', 'EXTRACTED', 'FAILED')"
    )
