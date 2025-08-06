#!/usr/bin/env python3
"""
Database Initialization Script
Creates the database and all tables
"""

import sys
import os
from pathlib import Path

# Add the API directory to Python path
api_dir = Path(__file__).parent
sys.path.insert(0, str(api_dir))

from database.connection import create_tables

def main():
    """Initialize the database"""
    print("🗄️  Initializing Database")
    print("=" * 30)
    
    try:
        print("🔄 Creating database tables...")
        create_tables()
        print("✅ Database initialized successfully!")
        
        # Check if database file was created
        db_path = api_dir / "team_balance.db"
        if db_path.exists():
            print(f"📁 Database created at: {db_path}")
            print(f"📊 Database size: {db_path.stat().st_size} bytes")
        else:
            print("⚠️  Database file not found, but tables may have been created in memory")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize database: {e}")
        return False

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
