#!/usr/bin/env python3
"""
Historical OpenSkill Calculation
Process all completed matches to calculate OpenSkill ratings from scratch
"""

import sqlite3
import sys
import os
from pathlib import Path
from datetime import datetime
import json

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

def calculate_openskill_from_history():
    """Calculate OpenSkill ratings from all historical matches"""
    
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
        
        # Check if OpenSkill tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='openskill_ratings'")
        if not cursor.fetchone():
            print("❌ OpenSkill tables not found. Please run create_openskill_tables.py first.")
            return False
        
        print("🔄 Processing historical matches for OpenSkill calculation...")
        
        # Get all completed matches ordered by creation date
        cursor.execute("""
            SELECT match_id, guild_id, created_at, total_teams
            FROM matches 
            WHERE status = 'completed'
            ORDER BY created_at ASC
        """)
        
        matches = cursor.fetchall()
        print(f"   📋 Found {len(matches)} completed matches to process")
        
        if not matches:
            print("   ⚠️  No completed matches found")
            return True
        
        # Reset all OpenSkill ratings to defaults before processing
        print("🔄 Resetting OpenSkill ratings to defaults...")
        cursor.execute("""
            UPDATE openskill_ratings 
            SET mu = 25.0, sigma = 8.333, games_played = 0, last_updated = CURRENT_TIMESTAMP
        """)
        
        # Clear existing OpenSkill match history
        cursor.execute("DELETE FROM openskill_match_history")
        
        processed_matches = 0
        failed_matches = 0
        
        # Process each match chronologically
        for match_id, guild_id, created_at, total_teams in matches:
            try:
                # Get match players and their team placements
                cursor.execute("""
                    SELECT user_id, team_number, team_placement
                    FROM match_players 
                    WHERE match_id = ? AND team_placement IS NOT NULL
                    ORDER BY team_number
                """, (match_id,))
                
                players = cursor.fetchall()
                
                if not players:
                    print(f"   ⚠️  Skipping match {match_id}: No players with placements")
                    continue
                
                # Group players by team and get their placements
                teams = {}
                team_placements = {}
                
                for user_id, team_number, team_placement in players:
                    if team_number not in teams:
                        teams[team_number] = []
                        team_placements[team_number] = team_placement
                    teams[team_number].append(user_id)
                
                # Simulate OpenSkill processing using the API logic
                success = process_match_openskill_simulation(
                    cursor, match_id, guild_id, teams, team_placements
                )
                
                if success:
                    processed_matches += 1
                    if processed_matches % 10 == 0:
                        print(f"   ✅ Processed {processed_matches}/{len(matches)} matches...")
                else:
                    failed_matches += 1
                    
            except Exception as e:
                print(f"   ❌ Failed to process match {match_id}: {e}")
                failed_matches += 1
                continue
        
        # Commit all changes
        conn.commit()
        
        print(f"\n✅ Historical OpenSkill calculation completed!")
        print(f"   📊 Processed: {processed_matches} matches")
        print(f"   ❌ Failed: {failed_matches} matches")
        
        # Show final statistics
        cursor.execute("SELECT COUNT(*) FROM openskill_ratings WHERE games_played > 0")
        active_users = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM openskill_match_history")
        total_history_entries = cursor.fetchone()[0]
        
        print(f"\n📈 Final Statistics:")
        print(f"   👥 Active OpenSkill Users: {active_users}")
        print(f"   📋 OpenSkill History Entries: {total_history_entries}")
        
        # Show top 10 OpenSkill ratings
        cursor.execute("""
            SELECT or.user_id, u.username, or.mu, or.sigma, or.games_played,
                   (or.mu * 60) as display_rating
            FROM openskill_ratings or
            JOIN users u ON or.guild_id = u.guild_id AND or.user_id = u.user_id
            WHERE or.games_played > 0
            ORDER BY or.mu DESC
            LIMIT 10
        """)
        
        top_players = cursor.fetchall()
        if top_players:
            print(f"\n🏆 Top 10 OpenSkill Players:")
            for i, (user_id, username, mu, sigma, games, display_rating) in enumerate(top_players, 1):
                print(f"   {i:2d}. {username}: {display_rating:.0f} ({mu:.1f}±{sigma:.1f}) - {games} games")
        
        return True
        
    except Exception as e:
        print(f"❌ Historical calculation failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def process_match_openskill_simulation(cursor, match_id, guild_id, teams, team_placements):
    """
    Simulate OpenSkill processing for a historical match
    This mimics the logic from OpenSkillDataService but works with raw SQL
    """
    try:
        # Import OpenSkill service (this requires the service to be available)
        from services.openskill_service import openskill_service, OpenSkillRating
        
        # Get current OpenSkill ratings for all players
        players_by_team = {}
        
        for team_num, user_ids in teams.items():
            players_by_team[team_num] = []
            
            for user_id in user_ids:
                # Get current OpenSkill rating
                cursor.execute("""
                    SELECT mu, sigma FROM openskill_ratings 
                    WHERE guild_id = ? AND user_id = ?
                """, (guild_id, user_id))
                
                rating_data = cursor.fetchone()
                if rating_data:
                    mu, sigma = rating_data
                else:
                    # Create default rating if not exists
                    mu, sigma = 25.0, 8.333
                    cursor.execute("""
                        INSERT OR IGNORE INTO openskill_ratings 
                        (guild_id, user_id, mu, sigma, games_played, created_at, last_updated)
                        VALUES (?, ?, ?, ?, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """, (guild_id, user_id, mu, sigma))
                
                player_data = {
                    'guild_id': guild_id,
                    'user_id': user_id,
                    'team_number': team_num,
                    'team_placement': team_placements[team_num],
                    'openskill_mu_before': mu,
                    'openskill_sigma_before': sigma
                }
                
                players_by_team[team_num].append(player_data)
        
        # Calculate new OpenSkill ratings
        updated_players = openskill_service.calculate_match_ratings(
            players_by_team, team_placements
        )
        
        # Update database with new ratings and history
        for team_num, players in updated_players.items():
            for player in players:
                # Update user's current rating
                cursor.execute("""
                    UPDATE openskill_ratings 
                    SET mu = ?, sigma = ?, games_played = games_played + 1, 
                        last_updated = CURRENT_TIMESTAMP
                    WHERE guild_id = ? AND user_id = ?
                """, (
                    player['openskill_mu_after'], 
                    player['openskill_sigma_after'],
                    player['guild_id'], 
                    player['user_id']
                ))
                
                # Record match history
                cursor.execute("""
                    INSERT INTO openskill_match_history 
                    (match_id, guild_id, user_id, team_number, team_placement,
                     total_competitors, guild_teams_count, external_teams_count, competition_type,
                     mu_before, sigma_before, mu_after, sigma_after, rating_change,
                     display_rating_before, display_rating_after, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    match_id,
                    player['guild_id'],
                    player['user_id'],
                    player['team_number'],
                    player['team_placement'],
                    player['total_competitors'],
                    player['guild_teams_count'],
                    player['external_teams_count'],
                    player['competition_type'],
                    player['openskill_mu_before'],
                    player['openskill_sigma_before'],
                    player['openskill_mu_after'],
                    player['openskill_sigma_after'],
                    player['rating_change'],
                    player['display_rating_before'],
                    player['display_rating_after']
                ))
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error processing match {match_id}: {e}")
        return False

if __name__ == "__main__":
    print("🚀 OpenSkill Historical Calculation Script")
    print("=" * 50)
    
    success = calculate_openskill_from_history()
    
    if success:
        print("\n🎉 Historical calculation completed!")
        print("✅ OpenSkill ratings are now ready for use")
        print("📊 You can now compare both rating systems")
    else:
        print("\n❌ Historical calculation failed. Please check the errors above.")
        sys.exit(1)
