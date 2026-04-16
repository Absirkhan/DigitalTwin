"""enable_bot_speaking_by_default

Revision ID: 9e3599156453
Revises: eb72f31d3f86
Create Date: 2026-04-04 17:18:20.946902

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9e3599156453'
down_revision = 'eb72f31d3f86'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change default values for new records
    op.alter_column('users', 'enable_bot_speaking',
                    existing_type=sa.Boolean(),
                    server_default='true',
                    existing_nullable=False)

    op.alter_column('meetings', 'bot_response_enabled',
                    existing_type=sa.Boolean(),
                    server_default='true',
                    existing_nullable=False)

    # Update ALL existing users to enable bot speaking
    op.execute("UPDATE users SET enable_bot_speaking = true WHERE enable_bot_speaking = false")

    # Update ALL existing meetings to enable bot responses
    op.execute("UPDATE meetings SET bot_response_enabled = true WHERE bot_response_enabled = false")


def downgrade() -> None:
    # Revert to old defaults (disabled by default)
    op.alter_column('users', 'enable_bot_speaking',
                    existing_type=sa.Boolean(),
                    server_default='false',
                    existing_nullable=False)

    op.alter_column('meetings', 'bot_response_enabled',
                    existing_type=sa.Boolean(),
                    server_default='false',
                    existing_nullable=False)