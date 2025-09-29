"""Add missing columns to meetings table

Revision ID: 002
Revises: 001
Create Date: 2025-09-07 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add missing columns to meetings table
    op.add_column('meetings', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('meetings', sa.Column('platform', sa.String(), nullable=True))
    op.add_column('meetings', sa.Column('scheduled_time', sa.DateTime(), nullable=True))
    op.add_column('meetings', sa.Column('duration_minutes', sa.Integer(), nullable=True))
    op.add_column('meetings', sa.Column('digital_twin_id', sa.Integer(), nullable=True))
    op.add_column('meetings', sa.Column('status', sa.String(), nullable=True))
    op.add_column('meetings', sa.Column('auto_join', sa.Boolean(), nullable=True))
    op.add_column('meetings', sa.Column('action_items', sa.JSON(), nullable=True))
    op.add_column('meetings', sa.Column('participants', sa.JSON(), nullable=True))
    op.add_column('meetings', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('meetings', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Update existing columns to match model
    # Make meeting_url not nullable for new requirements
    op.alter_column('meetings', 'meeting_url', nullable=False)
    
    # Set default values for new columns on existing records
    op.execute("UPDATE meetings SET platform = 'unknown' WHERE platform IS NULL")
    op.execute("UPDATE meetings SET status = 'scheduled' WHERE status IS NULL")
    op.execute("UPDATE meetings SET auto_join = true WHERE auto_join IS NULL")
    op.execute("UPDATE meetings SET duration_minutes = 60 WHERE duration_minutes IS NULL")
    op.execute("UPDATE meetings SET scheduled_time = start_time WHERE scheduled_time IS NULL")
    op.execute("UPDATE meetings SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL")
    
    # Make platform not nullable after setting default values
    op.alter_column('meetings', 'platform', nullable=False)


def downgrade() -> None:
    # Remove the added columns
    op.drop_column('meetings', 'updated_at')
    op.drop_column('meetings', 'created_at')
    op.drop_column('meetings', 'participants')
    op.drop_column('meetings', 'action_items')
    op.drop_column('meetings', 'auto_join')
    op.drop_column('meetings', 'status')
    op.drop_column('meetings', 'digital_twin_id')
    op.drop_column('meetings', 'duration_minutes')
    op.drop_column('meetings', 'scheduled_time')
    op.drop_column('meetings', 'platform')
    op.drop_column('meetings', 'description')
    
    # Revert meeting_url nullable change
    op.alter_column('meetings', 'meeting_url', nullable=True)
