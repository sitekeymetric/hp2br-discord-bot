#!/usr/bin/env python3
"""
Pending Matches Cleanup Script
Safely clean up old pending matches that were never completed
"""

import sqlite3
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

def cleanup_pending_matches(dry_run=True, max_age_hours=24.0, min_age_hours=1.0):
    """
    Clean up pending matches based on age criteria
    
    Args:
        dry_run: If True, only show what would be cleaned up
        max_age_hours: Matches older than this will be cancelled
        min_age_hours: Matches newer than this will be kept (safety buffer)
    """
    
    # Find database
    db_path = "team_balance.db"
    if not os.path.exists(db_path):
        print("❌ Database file not found: team_balance.db")
        return False
    
    print(f"🧹 Pending Matches Cleanup Script")
    print(f"{'=' * 50}")
    print(f"📊 Database: {db_path}")
    print(f"🔍 Mode: {'DRY RUN' if dry_run else 'LIVE CLEANUP'}")
    print(f"⏰ Max Age: {max_age_hours} hours")
    print(f"🛡️  Min Age: {min_age_hours} hours (safety buffer)")
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get current pending matches with details
        cursor.execute("""
            SELECT m.match_id, m.guild_id, m.created_by, m.start_time, m.total_teams,
                   COUNT(mp.user_id) as player_count,
                   (julianday('now') - julianday(m.start_time)) * 24 as hours_old
            FROM matches m
            LEFT JOIN match_players mp ON m.match_id = mp.match_id
            WHERE m.status = 'PENDING'
            GROUP BY m.match_id, m.guild_id, m.created_by, m.start_time, m.total_teams
            ORDER BY m.start_time DESC
        """)
        
        pending_matches = cursor.fetchall()
        
        if not pending_matches:
            print("✅ No pending matches found!")
            return True
        
        print(f"📋 Found {len(pending_matches)} pending matches:")
        print()
        
        # Categorize matches
        to_cancel = []
        to_keep = []
        
        for match in pending_matches:
            match_id, guild_id, created_by, start_time, total_teams, player_count, hours_old = match
            
            print(f"🎮 Match {match_id[:8]}...")
            print(f"   📅 Created: {start_time}")
            print(f"   ⏰ Age: {hours_old:.1f} hours")
            print(f"   👥 Players: {player_count}")
            print(f"   🏆 Teams: {total_teams}")
            
            if hours_old > max_age_hours:
                print(f"   ❌ TOO OLD - Will be cancelled (>{max_age_hours}h)")
                to_cancel.append(match)
            elif hours_old < min_age_hours:
                print(f"   ✅ TOO NEW - Will be kept (<{min_age_hours}h safety buffer)")
                to_keep.append(match)
            else:
                print(f"   ⚠️  IN RANGE - Will be cancelled ({min_age_hours}h-{max_age_hours}h)")
                to_cancel.append(match)
            print()
        
        print(f"📊 Summary:")
        print(f"   ❌ To Cancel: {len(to_cancel)} matches")
        print(f"   ✅ To Keep: {len(to_keep)} matches")
        print()
        
        if not to_cancel:
            print("✅ No matches need to be cancelled!")
            return True
        
        if dry_run:
            print("🔍 DRY RUN - No changes will be made")
            print("   Run with --live to actually clean up these matches")
            return True
        
        # Perform actual cleanup
        print("🧹 Performing cleanup...")
        
        cancelled_count = 0
        for match in to_cancel:
            match_id = match[0]
            try:
                # Update match status to CANCELLED
                cursor.execute("""
                    UPDATE matches 
                    SET status = 'CANCELLED', 
                        result_type = 'CANCELLED',
                        end_time = CURRENT_TIMESTAMP
                    WHERE match_id = ?
                """, (match_id,))
                
                # Update all match players to cancelled
                cursor.execute("""
                    UPDATE match_players 
                    SET result = 'PENDING'
                    WHERE match_id = ?
                """, (match_id,))
                
                cancelled_count += 1
                print(f"   ✅ Cancelled match {match_id[:8]}...")
                
            except Exception as e:
                print(f"   ❌ Failed to cancel match {match_id[:8]}: {e}")
        
        # Commit changes
        conn.commit()
        
        print(f"\n✅ Cleanup completed!")
        print(f"   ❌ Cancelled: {cancelled_count} matches")
        print(f"   ✅ Kept: {len(to_keep)} matches")
        
        return True
        
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def show_current_status():
    """Show current status of all matches"""
    db_path = "team_balance.db"
    if not os.path.exists(db_path):
        print("❌ Database file not found")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM matches
            GROUP BY status
            ORDER BY count DESC
        """)
        
        results = cursor.fetchall()
        
        print("📊 Current Match Status:")
        for status, count in results:
            print(f"   {status}: {count} matches")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up pending matches")
    parser.add_argument("--live", action="store_true", help="Actually perform cleanup (default is dry run)")
    parser.add_argument("--max-age", type=float, default=24.0, help="Max age in hours (default: 24 - 1 day)")
    parser.add_argument("--min-age", type=float, default=1.0, help="Min age in hours for safety (default: 1)")
    parser.add_argument("--status", action="store_true", help="Just show current status")
    
    args = parser.parse_args()
    
    if args.status:
        show_current_status()
    else:
        success = cleanup_pending_matches(
            dry_run=not args.live,
            max_age_hours=args.max_age,
            min_age_hours=args.min_age
        )
        
        if not success:
            sys.exit(1)
