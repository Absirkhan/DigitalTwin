"""Add bot speaking functionality

Revision ID: eb72f31d3f86
Revises: f8a52e412ae7
Create Date: 2026-03-30 20:07:34.218342

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eb72f31d3f86'
down_revision = 'f8a52e412ae7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add bot speaking column to users table
    op.add_column('users', sa.Column('enable_bot_speaking', sa.Boolean(), nullable=False, server_default='false'))

    # Add bot speaking columns to meetings table
    op.add_column('meetings', sa.Column('bot_response_style', sa.String(length=20), nullable=False, server_default='professional'))
    op.add_column('meetings', sa.Column('bot_response_enabled', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('meetings', sa.Column('bot_response_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('meetings', sa.Column('bot_max_responses', sa.Integer(), nullable=False, server_default='10'))

    # Create bot_responses table
    op.create_table(
        'bot_responses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('bot_id', sa.String(), nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=False),
        sa.Column('trigger_text', sa.Text(), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('response_style', sa.String(length=20), nullable=False),
        sa.Column('audio_url', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('success', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('idx_bot_responses_meeting', 'bot_responses', ['meeting_id'])
    op.create_index('idx_bot_responses_timestamp', 'bot_responses', ['timestamp'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_bot_responses_timestamp', table_name='bot_responses')
    op.drop_index('idx_bot_responses_meeting', table_name='bot_responses')

    # Drop bot_responses table
    op.drop_table('bot_responses')

    # Remove columns from meetings table
    op.drop_column('meetings', 'bot_max_responses')
    op.drop_column('meetings', 'bot_response_count')
    op.drop_column('meetings', 'bot_response_enabled')
    op.drop_column('meetings', 'bot_response_style')

    # Remove column from users table
    op.drop_column('users', 'enable_bot_speaking')