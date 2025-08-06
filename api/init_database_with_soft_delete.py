"""Initialize database and ensure soft delete support

This script:
1. Creates all database tables if they don't exist
2. Adds deleted_at column to users table if missing
3. Uses the same database configuration as the API

Usage:
    python init_database_with_soft_delete.py

"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL - same as API configuration"""
    return os.getenv("DATABASE_URL", "sqlite:///./team_balance.db")

def main():
    """Initialize database and ensure soft delete support"""
    
    database_url = get_database_url()
    logger.info(f"Using database: {database_url}")
    engine = create_engine(database_url)
    
    try:
        # Step 1: Create all tables if they don't exist
        logger.info("Step 1: Creating database tables...")
        try:
            from database.models import Base
            Base.metadata.create_all(bind=engine)
            logger.info("✅ Database tables created/verified")
        except Exception as e:
            logger.error(f"❌ Failed to create tables: {e}")
            raise
        
        # Step 2: Add deleted_at column if missing
        logger.info("Step 2: Checking for deleted_at column...")
        with engine.connect() as conn:
            # Check if deleted_at column exists
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]  # row[1] is column name
            
            if 'deleted_at' in columns:
                logger.info("✅ Column 'deleted_at' already exists in users table")
            else:
                # Add the deleted_at column
                logger.info("Adding deleted_at column to users table...")
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN deleted_at TIMESTAMP NULL
                """))
                conn.commit()
                logger.info("✅ Successfully added deleted_at column to users table")
                
                # Verify the column was added
                result = conn.execute(text("PRAGMA table_info(users)"))
                columns = [row[1] for row in result.fetchall()]
                if 'deleted_at' in columns:
                    logger.info("✅ Verified: deleted_at column is now present")
                else:
                    logger.error("❌ Column was not added successfully")
                    raise Exception("Failed to add deleted_at column")
        
        # Step 3: Show final table structure
        logger.info("Step 3: Final database structure:")
        with engine.connect() as conn:
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = result.fetchall()
            logger.info("Users table columns:")
            for col in columns:
                logger.info(f"  - {col[1]} ({col[2]})")
        
        logger.info("🎉 Database initialization and migration complete!")
        logger.info("The API server can now be started safely.")
        
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise

if __name__ == "__main__":
    main()
