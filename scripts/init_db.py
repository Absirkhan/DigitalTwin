#!/usr/bin/env python3
"""
Database initialization script
Creates the database schema using Alembic migrations
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from alembic.config import Config
from alembic import command
from app.core.config import settings


def init_database():
    """Initialize the database with the schema"""
    print("Initializing database...")
    
    # Get alembic config
    alembic_cfg = Config(str(project_root / "alembic.ini"))
    
    try:
        # Run migrations
        print("Running database migrations...")
        command.upgrade(alembic_cfg, "head")
        print("✅ Database initialized successfully!")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)