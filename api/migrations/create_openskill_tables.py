#!/usr/bin/env python3
"""
Migration: Create OpenSkill tables for parallel rating system
This creates new tables alongside existing placement rating system
"""

import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

def create_openskill_tables():
    """Create OpenSkill tables for parallel rating system"""
    
    # Database paths to check
    db_paths = [
        "team_balance.db",
        "hp2br.db",
        "../team_balance.db",
        "../hp2br.db"
    ]
    
    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break
    
    if not db_path:
        print("❌ No database file found. Checked paths:")
        for path in db_paths:
            print(f"   - {path}")
        return False
    
    print(f"📊 Using database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Creating OpenSkill tables...")
        
        # Create openskill_ratings table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS openskill_ratings (
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                mu REAL NOT NULL DEFAULT 25.0,
                sigma REAL NOT NULL DEFAULT 8.333,
                games_played INTEGER NOT NULL DEFAULT 0,
                last_updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id),
                FOREIGN KEY (guild_id, user_id) REFERENCES users(guild_id, user_id)
            )
        """)
        print("   ✅ Created openskill_ratings table")
        
        # Create openskill_match_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS openskill_match_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id TEXT NOT NULL,
                guild_id BIGINT NOT NULL,
                user_id BIGINT NOT NULL,
                team_number INTEGER NOT NULL,
                team_placement INTEGER NOT NULL,
                total_competitors INTEGER NOT NULL,
                guild_teams_count INTEGER NOT NULL,
                external_teams_count INTEGER NOT NULL,
                mu_before REAL NOT NULL,
                sigma_before REAL NOT NULL,
                mu_after REAL NOT NULL,
                sigma_after REAL NOT NULL,
                rating_change REAL NOT NULL,
                display_rating_before REAL NOT NULL,
                display_rating_after REAL NOT NULL,
                competition_type VARCHAR(20) NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (match_id) REFERENCES matches(match_id),
                FOREIGN KEY (guild_id, user_id) REFERENCES users(guild_id, user_id)
            )
        """)
        print("   ✅ Created openskill_match_history table")
        
        # Create indexes for performance
        print("🔄 Creating indexes...")
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_openskill_ratings_guild ON openskill_ratings(guild_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_openskill_history_match ON openskill_match_history(match_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_openskill_history_user ON openskill_match_history(guild_id, user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_openskill_history_created ON openskill_match_history(created_at)")
        
        print("   ✅ Created performance indexes")
        
        # Initialize OpenSkill ratings for existing users
        print("🔄 Initializing OpenSkill ratings for existing users...")
        
        cursor.execute("""
            INSERT OR IGNORE INTO openskill_ratings (guild_id, user_id, mu, sigma, games_played, created_at, last_updated)
            SELECT guild_id, user_id, 25.0, 8.333, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            FROM users
            WHERE is_deleted = 0 OR is_deleted IS NULL
        """)
        
        initialized_users = cursor.rowcount
        print(f"   ✅ Initialized OpenSkill ratings for {initialized_users} users")
        
        # Commit changes
        conn.commit()
        print("✅ OpenSkill tables created successfully!")
        
        # Show summary
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_deleted = 0 OR is_deleted IS NULL")
        total_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM matches WHERE status = 'completed'")
        total_matches = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM openskill_ratings")
        openskill_users = cursor.fetchone()[0]
        
        print(f"\n📊 Database Summary:")
        print(f"   👥 Total Active Users: {total_users}")
        print(f"   🎮 Completed Matches: {total_matches}")
        print(f"   🆕 OpenSkill Users Initialized: {openskill_users}")
        print(f"   📋 Ready for historical calculation")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 OpenSkill Tables Creation Script")
    print("=" * 50)
    
    success = create_openskill_tables()
    
    if success:
        print("\n🎉 Tables created successfully! Next steps:")
        print("1. Install OpenSkill: pip install openskill==5.0.0")
        print("2. Run historical rating calculation")
        print("3. Test with new matches")
    else:
        print("\n❌ Table creation failed. Please check the errors above.")
        sys.exit(1)
