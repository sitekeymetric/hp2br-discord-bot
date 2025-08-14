"""
Database migration for Advanced Rating System v3.0.0
Adds detailed tracking fields for rating calculation breakdown
"""

import sqlite3
import json
from datetime import datetime
from typing import Dict, Any


class AdvancedRatingMigration:
    """Migration to add advanced rating tracking fields"""
    
    def __init__(self, db_path: str = "team_balance.db"):
        self.db_path = db_path
    
    def run_migration(self) -> bool:
        """Execute the migration"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print("🚀 Starting Advanced Rating System v3.0.0 Migration...")
            
            # Step 1: Add new columns to match_players table
            self._add_match_players_columns(cursor)
            
            # Step 2: Add new columns to matches table
            self._add_matches_columns(cursor)
            
            # Step 3: Create migration log table
            self._create_migration_log(cursor)
            
            # Step 4: Log this migration
            self._log_migration(cursor)
            
            conn.commit()
            conn.close()
            
            print("✅ Advanced Rating System v3.0.0 Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            return False
    
    def _add_match_players_columns(self, cursor):
        """Add detailed rating calculation columns to match_players"""
        print("📊 Adding rating calculation tracking columns...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(match_players)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            ("base_score", "REAL"),
            ("opponent_multiplier", "REAL"),
            ("individual_adjustment", "REAL"), 
            ("curve_multiplier", "REAL"),
            ("preliminary_change", "REAL"),
            ("max_change_limit", "REAL"),
            ("opponent_avg_rating", "REAL"),
            ("team_avg_rating", "REAL"),
            ("rating_tier_before", "TEXT"),
            ("rating_tier_after", "TEXT")
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE match_players ADD COLUMN {column_name} {column_type}")
                    print(f"  ✅ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        raise e
                    print(f"  ⚠️  Column {column_name} already exists")
    
    def _add_matches_columns(self, cursor):
        """Add team rating tracking to matches table"""
        print("🏆 Adding team rating tracking columns...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(matches)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            ("team_ratings", "TEXT"),  # JSON field for team rating data
            ("rating_system_version", "TEXT"),  # Track which rating system was used
            ("avg_opponent_strength", "REAL"),  # Average opponent strength for the match
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f"ALTER TABLE matches ADD COLUMN {column_name} {column_type}")
                    print(f"  ✅ Added column: {column_name}")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e).lower():
                        raise e
                    print(f"  ⚠️  Column {column_name} already exists")
    
    def _create_migration_log(self, cursor):
        """Create migration log table if it doesn't exist"""
        print("📝 Creating migration log table...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS migration_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                migration_name TEXT NOT NULL,
                version TEXT NOT NULL,
                executed_at DATETIME NOT NULL,
                description TEXT,
                success BOOLEAN NOT NULL DEFAULT TRUE
            )
        """)
        print("  ✅ Migration log table ready")
    
    def _log_migration(self, cursor):
        """Log this migration execution"""
        cursor.execute("""
            INSERT INTO migration_log (migration_name, version, executed_at, description, success)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "add_advanced_rating_tracking",
            "v3.0.0",
            datetime.utcnow().isoformat(),
            "Added detailed rating calculation tracking for Advanced Rating System v3.0.0",
            True
        ))
        print("  ✅ Migration logged")
    
    def rollback_migration(self) -> bool:
        """Rollback the migration (remove added columns)"""
        print("🔄 Rolling back Advanced Rating System v3.0.0 Migration...")
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # SQLite doesn't support DROP COLUMN directly, so we need to recreate tables
            print("⚠️  SQLite doesn't support DROP COLUMN. Manual rollback required.")
            print("To rollback, you would need to:")
            print("1. Export existing data")
            print("2. Drop and recreate tables without new columns")
            print("3. Re-import data")
            
            conn.close()
            return False
            
        except Exception as e:
            print(f"❌ Rollback failed: {str(e)}")
            return False
    
    def verify_migration(self) -> bool:
        """Verify that the migration was applied correctly"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            print("🔍 Verifying migration...")
            
            # Check match_players columns
            cursor.execute("PRAGMA table_info(match_players)")
            match_players_columns = [column[1] for column in cursor.fetchall()]
            
            required_mp_columns = [
                "base_score", "opponent_multiplier", "individual_adjustment",
                "curve_multiplier", "preliminary_change", "max_change_limit",
                "opponent_avg_rating", "team_avg_rating", "rating_tier_before", "rating_tier_after"
            ]
            
            missing_mp_columns = [col for col in required_mp_columns if col not in match_players_columns]
            if missing_mp_columns:
                print(f"❌ Missing match_players columns: {missing_mp_columns}")
                return False
            
            # Check matches columns
            cursor.execute("PRAGMA table_info(matches)")
            matches_columns = [column[1] for column in cursor.fetchall()]
            
            required_matches_columns = ["team_ratings", "rating_system_version", "avg_opponent_strength"]
            missing_matches_columns = [col for col in required_matches_columns if col not in matches_columns]
            if missing_matches_columns:
                print(f"❌ Missing matches columns: {missing_matches_columns}")
                return False
            
            # Check migration log
            cursor.execute("SELECT COUNT(*) FROM migration_log WHERE migration_name = 'add_advanced_rating_tracking'")
            log_count = cursor.fetchone()[0]
            if log_count == 0:
                print("❌ Migration not found in log")
                return False
            
            conn.close()
            print("✅ Migration verification successful!")
            return True
            
        except Exception as e:
            print(f"❌ Migration verification failed: {str(e)}")
            return False


def run_migration():
    """Run the migration from command line"""
    migration = AdvancedRatingMigration()
    success = migration.run_migration()
    
    if success:
        migration.verify_migration()
    
    return success


if __name__ == "__main__":
    run_migration()
