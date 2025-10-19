"""Add recording fields to bot table

Revision ID: 004_add_recording_fields
Revises: 003_update_user_oauth
Create Date: 2025-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_recording_fields'
down_revision = '003_update_user_oauth'
branch_labels = None
depends_on = None


def upgrade():
    # Add new recording-related columns to bots table
    op.add_column('bots', sa.Column('recording_status', sa.String(), nullable=True, default='pending'))
    op.add_column('bots', sa.Column('recording_data', sa.JSON(), nullable=True))
    op.add_column('bots', sa.Column('video_recording_url', sa.String(), nullable=True))
    op.add_column('bots', sa.Column('recording_expires_at', sa.DateTime(), nullable=True))
    op.add_column('bots', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('bots', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Set default values for existing records
    op.execute("UPDATE bots SET recording_status = 'not_requested' WHERE recording_status IS NULL")
    op.execute("UPDATE bots SET created_at = NOW() WHERE created_at IS NULL")


def downgrade():
    # Remove the recording-related columns
    op.drop_column('bots', 'updated_at')
    op.drop_column('bots', 'created_at')
    op.drop_column('bots', 'recording_expires_at')
    op.drop_column('bots', 'video_recording_url')
    op.drop_column('bots', 'recording_data')
    op.drop_column('bots', 'recording_status')