"""add participant_metric table for single storage

Revision ID: 174f323110bc
Revises: db797a3f587a
Create Date: 2025-11-11 14:29:41.381639

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '174f323110bc'
down_revision: Union[str, None] = 'db797a3f587a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create participant_metric table
    op.create_table('participant_metric',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('participant_id', sa.UUID(), nullable=False),
    sa.Column('metric_code', sa.String(length=50), nullable=False),
    sa.Column('value', sa.Numeric(precision=4, scale=2), nullable=False),
    sa.Column('confidence', sa.Numeric(precision=4, scale=3), nullable=True),
    sa.Column('last_source_report_id', sa.UUID(), nullable=True),
    sa.Column('updated_at', postgresql.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('confidence IS NULL OR (confidence >= 0 AND confidence <= 1)', name='participant_metric_confidence_check'),
    sa.CheckConstraint('value >= 1 AND value <= 10', name='participant_metric_value_range_check'),
    sa.ForeignKeyConstraint(['last_source_report_id'], ['report.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['participant_id'], ['participant.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('participant_id', 'metric_code', name='participant_metric_unique')
    )
    op.create_index('ix_participant_metric_metric_code', 'participant_metric', ['metric_code'], unique=False)
    op.create_index('ix_participant_metric_participant_id', 'participant_metric', ['participant_id'], unique=False)

    # Backfill data from extracted_metric
    # For each participant and metric_code, select the most recent value based on report.uploaded_at
    # On tie, prefer higher confidence
    op.execute("""
        INSERT INTO participant_metric (id, participant_id, metric_code, value, confidence, last_source_report_id, updated_at)
        SELECT
            gen_random_uuid() as id,
            r.participant_id,
            md.code as metric_code,
            em.value,
            em.confidence,
            em.report_id as last_source_report_id,
            COALESCE(r.uploaded_at, r.extracted_at, now()) as updated_at
        FROM extracted_metric em
        INNER JOIN metric_def md ON em.metric_def_id = md.id
        INNER JOIN report r ON em.report_id = r.id
        WHERE (r.participant_id, md.code, r.uploaded_at, COALESCE(em.confidence, 0)) IN (
            SELECT
                r2.participant_id,
                md2.code,
                MAX(r2.uploaded_at) as max_uploaded_at,
                MAX(COALESCE(em2.confidence, 0)) as max_confidence
            FROM extracted_metric em2
            INNER JOIN metric_def md2 ON em2.metric_def_id = md2.id
            INNER JOIN report r2 ON em2.report_id = r2.id
            GROUP BY r2.participant_id, md2.code
        )
        ON CONFLICT (participant_id, metric_code) DO NOTHING
    """)


def downgrade() -> None:
    # Drop participant_metric table and indexes
    op.drop_index('ix_participant_metric_participant_id', table_name='participant_metric')
    op.drop_index('ix_participant_metric_metric_code', table_name='participant_metric')
    op.drop_table('participant_metric')
