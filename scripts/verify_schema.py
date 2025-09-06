#!/usr/bin/env python3
"""
Schema verification script
Verifies that the database schema matches the requirements
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, inspect
from app.core.config import settings


def verify_schema():
    """Verify the database schema matches requirements"""
    print("Verifying database schema...")
    
    try:
        engine = create_engine(settings.DATABASE_URL)
        inspector = inspect(engine)
        
        # Expected tables
        expected_tables = {
            'users': ['id', 'email', 'full_name', 'google_id', 'credentials', 'bot_name', 'enable_backend_tasks', 'profile_picture'],
            'bots': ['id', 'bot_id', 'user_id', 'platform', 'bot_name', 'video_download_url', 'transcript_url', 'meeting_id'],
            'meetings': ['id', 'user_id', 'title', 'start_time', 'end_time', 'transcript', 'summary', 'meeting_url', 'calendar_id', 'calendar_event_id'],
            'calendar_events': ['id', 'user_id', 'event_id', 'summary', 'start_time', 'end_time', 'meeting_url', 'participants'],
            'emails': ['id', 'user_id', 'message_id', 'subject', 'sender', 'snippet']
        }
        
        # Get actual tables
        actual_tables = inspector.get_table_names()
        
        print(f"Found tables: {actual_tables}")
        
        # Check each expected table
        for table_name, expected_columns in expected_tables.items():
            if table_name not in actual_tables:
                print(f"❌ Missing table: {table_name}")
                return False
            
            # Check columns
            actual_columns = [col['name'] for col in inspector.get_columns(table_name)]
            print(f"Table {table_name}: {actual_columns}")
            
            for col in expected_columns:
                if col not in actual_columns:
                    print(f"❌ Missing column {col} in table {table_name}")
                    return False
        
        print("✅ Schema verification passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying schema: {e}")
        return False


if __name__ == "__main__":
    success = verify_schema()
    sys.exit(0 if success else 1)