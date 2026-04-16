"""increase_bot_max_responses_default

Revision ID: 4776e838991f
Revises: bb1ce091d837
Create Date: 2026-04-11 13:52:10.863393

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4776e838991f'
down_revision = 'bb1ce091d837'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update existing meetings to have higher max_responses (9999 = effectively unlimited for testing)
    op.execute("UPDATE meetings SET bot_max_responses = 9999 WHERE bot_max_responses = 10")

    # Change column default for new meetings
    op.alter_column('meetings', 'bot_max_responses',
                    existing_type=sa.Integer(),
                    server_default='9999',
                    nullable=False)


def downgrade() -> None:
    # Revert to original default
    op.alter_column('meetings', 'bot_max_responses',
                    existing_type=sa.Integer(),
                    server_default='10',
                    nullable=False)

    # Revert existing meetings
    op.execute("UPDATE meetings SET bot_max_responses = 10 WHERE bot_max_responses = 9999")