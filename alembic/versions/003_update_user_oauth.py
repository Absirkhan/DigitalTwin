"""Update user table for OAuth authentication

Revision ID: 003_update_user_oauth
Revises: 002_add_missing_meeting_columns
Create Date: 2025-09-30 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_update_user_oauth'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Check if columns exist before operations
    conn = op.get_bind()
    
    # Check if hashed_password column exists and drop it
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'hashed_password'
    """)).fetchone()
    
    if result:
        op.drop_column('users', 'hashed_password')
    
    # Check if is_active column exists before adding it
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'is_active'
    """)).fetchone()
    
    if not result:
        op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=True, default=True))
    
    # Check if oauth_tokens column exists before adding it
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'oauth_tokens'
    """)).fetchone()
    
    if not result:
        op.add_column('users', sa.Column('oauth_tokens', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Create unique constraint on google_id if it doesn't exist
    result = conn.execute(sa.text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'users' AND constraint_name = 'uq_users_google_id'
    """)).fetchone()
    
    if not result:
        op.create_unique_constraint('uq_users_google_id', 'users', ['google_id'])
    
    # Set default value for is_active on existing records
    op.execute("UPDATE users SET is_active = true WHERE is_active IS NULL")
    
    # Check if credentials column exists and drop it
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'credentials'
    """)).fetchone()
    
    if result:
        op.drop_column('users', 'credentials')


def downgrade():
    # Add back the old columns
    conn = op.get_bind()
    
    # Check if hashed_password column exists before adding it
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'hashed_password'
    """)).fetchone()
    
    if not result:
        op.add_column('users', sa.Column('hashed_password', sa.VARCHAR(), nullable=True))
    
    # Check if credentials column exists before adding it
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'credentials'
    """)).fetchone()
    
    if not result:
        op.add_column('users', sa.Column('credentials', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Remove unique constraint if it exists
    result = conn.execute(sa.text("""
        SELECT constraint_name 
        FROM information_schema.table_constraints 
        WHERE table_name = 'users' AND constraint_name = 'uq_users_google_id'
    """)).fetchone()
    
    if result:
        op.drop_constraint('uq_users_google_id', 'users', type_='unique')
    
    # Remove OAuth columns if they exist
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'oauth_tokens'
    """)).fetchone()
    
    if result:
        op.drop_column('users', 'oauth_tokens')
    
    result = conn.execute(sa.text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'users' AND column_name = 'is_active'
    """)).fetchone()
    
    if result:
        op.drop_column('users', 'is_active')