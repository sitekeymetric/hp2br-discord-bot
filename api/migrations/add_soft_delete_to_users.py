"""Add soft delete support to users table

This migration adds a deleted_at column to the users table to support soft deletes.
This preserves match history integrity while allowing users to be "deleted".

Usage:
    python add_soft_delete_to_users.py

"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment or use default"""
    import os
    return os.getenv("DATABASE_URL", "sqlite:///./hp2br.db")

def run_migration():
    """Add deleted_at column to users table"""
    
    # Get database URL
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Check if column already exists (SQLite specific)
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]  # row[1] is column name
            
            if 'deleted_at' in columns:
                logger.info("Column 'deleted_at' already exists in users table")
                return
            
            # Add the deleted_at column
            logger.info("Adding deleted_at column to users table...")
            conn.execute(text("""
                ALTER TABLE users 
                ADD COLUMN deleted_at TIMESTAMP NULL
            """))
            
            conn.commit()
            logger.info("✅ Successfully added deleted_at column to users table")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    run_migration()
