"""Initialize database and run soft delete migration"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from database.models import Base
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get database URL from environment or use default"""
    return os.getenv("DATABASE_URL", "sqlite:///./hp2br.db")

def main():
    """Initialize database and add soft delete column"""
    
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    try:
        # Create all tables
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created")
        
        # Add deleted_at column if it doesn't exist
        with engine.connect() as conn:
            # Check if column already exists (SQLite specific)
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]  # row[1] is column name
            
            if 'deleted_at' in columns:
                logger.info("Column 'deleted_at' already exists in users table")
            else:
                # Add the deleted_at column
                logger.info("Adding deleted_at column to users table...")
                conn.execute(text("""
                    ALTER TABLE users 
                    ADD COLUMN deleted_at TIMESTAMP NULL
                """))
                conn.commit()
                logger.info("✅ Successfully added deleted_at column to users table")
        
        logger.info("🎉 Database initialization and migration complete!")
        
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        raise

if __name__ == "__main__":
    main()
