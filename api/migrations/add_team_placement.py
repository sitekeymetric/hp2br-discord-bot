#!/usr/bin/env python3
"""
Database Migration: Add team_placement column to match_players table
Version: v2.0.0
Date: 2025-08-05
"""

import sqlite3
import os
import sys
from pathlib import Path

def run_migration():
    """Add team_placement column to match_players table"""
    
    # Get database path (relative to API directory)
    db_path = Path(__file__).parent.parent / "team_balance.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        print("Please make sure the database exists before running migration.")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(match_players)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'team_placement' in columns:
            print("✅ Column 'team_placement' already exists. Migration not needed.")
            conn.close()
            return True
        
        print("🔄 Adding team_placement column to match_players table...")
        
        # Add the new column
        cursor.execute("""
            ALTER TABLE match_players 
            ADD COLUMN team_placement INTEGER
        """)
        
        # Commit changes
        conn.commit()
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(match_players)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'team_placement' in columns:
            print("✅ Successfully added team_placement column!")
            
            # Show current table structure
            print("\n📊 Updated match_players table structure:")
            cursor.execute("PRAGMA table_info(match_players)")
            for column in cursor.fetchall():
                print(f"  - {column[1]} ({column[2]})")
            
            conn.close()
            return True
        else:
            print("❌ Failed to add team_placement column")
            conn.close()
            return False
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🗄️  Database Migration: Add team_placement column")
    print("=" * 50)
    
    success = run_migration()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("The placement-based rating system is now ready to use.")
    else:
        print("\n💥 Migration failed!")
        print("Please check the error messages above and try again.")
        sys.exit(1)
