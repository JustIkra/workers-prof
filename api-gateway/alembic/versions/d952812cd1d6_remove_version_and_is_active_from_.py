"""remove_version_and_is_active_from_weight_table

Revision ID: d952812cd1d6
Revises: 07516eea5685
Create Date: 2025-11-12 11:34:29.552624

Simplifies weight_table model by removing versioning mechanism.
Keeps only one weight table per professional activity.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd952812cd1d6'
down_revision: Union[str, None] = '07516eea5685'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove version and is_active fields from weight_table.
    Keep only the active version for each professional activity.
    """
    from sqlalchemy import inspect

    # Get connection and inspector
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if weight_table exists
    if 'weight_table' not in inspector.get_table_names():
        # Table doesn't exist yet, skip this migration
        return

    # Drop indexes and constraints that depend on version and is_active
    # Check if index exists before dropping
    indexes = inspector.get_indexes('weight_table')
    if any(idx['name'] == 'uq_weight_table_prof_activity_active' for idx in indexes):
        op.drop_index('uq_weight_table_prof_activity_active', table_name='weight_table')

    # Check if constraints exist before dropping
    unique_constraints = inspector.get_unique_constraints('weight_table')
    if any(uc['name'] == 'weight_table_prof_activity_version_unique' for uc in unique_constraints):
        op.drop_constraint('weight_table_prof_activity_version_unique', 'weight_table', type_='unique')

    check_constraints = inspector.get_check_constraints('weight_table')
    if any(cc['name'] == 'weight_table_version_positive' for cc in check_constraints):
        op.drop_constraint('weight_table_version_positive', 'weight_table', type_='check')

    # Delete inactive versions (keep only active ones)
    op.execute("DELETE FROM weight_table WHERE is_active = false")

    # Drop version and is_active columns
    columns = [col['name'] for col in inspector.get_columns('weight_table')]
    if 'version' in columns:
        op.drop_column('weight_table', 'version')
    if 'is_active' in columns:
        op.drop_column('weight_table', 'is_active')

    # Add unique constraint on prof_activity_id (one table per activity)
    # Check if constraint already exists
    unique_constraints = inspector.get_unique_constraints('weight_table')
    if not any(uc['name'] == 'uq_weight_table_prof_activity' for uc in unique_constraints):
        op.create_unique_constraint(
            'uq_weight_table_prof_activity',
            'weight_table',
            ['prof_activity_id']
        )


def downgrade() -> None:
    """
    Restore version and is_active fields.
    This is a destructive operation - version history cannot be recovered.
    """
    # Drop the unique constraint
    op.drop_constraint('uq_weight_table_prof_activity', 'weight_table', type_='unique')

    # Add back version and is_active columns
    op.add_column('weight_table',
                  sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('weight_table',
                  sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))

    # Restore constraints and indexes
    op.create_check_constraint('weight_table_version_positive', 'weight_table', 'version > 0')
    op.create_unique_constraint(
        'weight_table_prof_activity_version_unique',
        'weight_table',
        ['prof_activity_id', 'version']
    )
    op.create_index(
        'uq_weight_table_prof_activity_active',
        'weight_table',
        ['prof_activity_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true')
    )

    # Remove server defaults after initial values are set
    op.alter_column('weight_table', 'version', server_default=None)
    op.alter_column('weight_table', 'is_active', server_default=None)
