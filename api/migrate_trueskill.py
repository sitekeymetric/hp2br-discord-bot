#!/usr/bin/env python3
"""
Migration script to export TrueSkill user and match data as SQL statements
for direct import into SQLite3 database
"""

import httpx
import sys
import os
import uuid
from datetime import datetime

# Add the api directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from database.models import MatchStatus
except ImportError:
    # Define MatchStatus enum if import fails
    class MatchStatus:
        COMPLETED = "completed"

# Configuration
TRUESKILL_SERVICE_URL = "http://192.168.192.10:8081"
TARGET_GUILD_ID = 696226047229952110

def fetch_trueskill_players():
    """Fetch player data from TrueSkill service"""
    try:
        with httpx.Client() as client:
            response = client.get(f"{TRUESKILL_SERVICE_URL}/players")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        print(f"Error fetching TrueSkill players: {e}")
        return None

def fetch_trueskill_games():
    """Fetch game data from TrueSkill service"""
    try:
        with httpx.Client() as client:
            response = client.get(f"{TRUESKILL_SERVICE_URL}/games")
            response.raise_for_status()
            return response.json()
    except httpx.RequestError as e:
        print(f"Error fetching TrueSkill games: {e}")
        return None

def escape_sql_string(value):
    """Escape single quotes in SQL strings"""
    if value is None:
        return "NULL"
    return f"'{str(value).replace(chr(39), chr(39) + chr(39))}'"

def generate_player_sql(trueskill_players, output_file):
    """Generate SQL INSERT statements for TrueSkill players"""
    migrated_count = 0
    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    
    output_file.write("-- TrueSkill Players Migration\n")
    output_file.write("-- Generated on: " + current_time + "\n\n")
    
    # Create table if not exists
    output_file.write("""-- Create users table if it doesn't exist
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    username TEXT NOT NULL,
    region_code TEXT,
    rating_mu REAL DEFAULT 1500.0,
    rating_sigma REAL DEFAULT 350.0,
    games_played INTEGER DEFAULT 0,
    wins INTEGER DEFAULT 0,
    losses INTEGER DEFAULT 0,
    draws INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, user_id)
);

""")
    
    for player in trueskill_players:
        user_id = player["user_id"]
        username = escape_sql_string(player["username"])
        region = escape_sql_string(player["region"] if player["region"] != "Unknown" else None)
        games_played = player["games_played"]
        wins = player["wins"]
        losses = player["losses"]
        draws = player["draws"]
        
        # Use INSERT OR REPLACE to handle existing users
        sql = f"""INSERT OR REPLACE INTO users (
    guild_id, user_id, username, region_code, rating_mu, rating_sigma,
    games_played, wins, losses, draws, created_at, last_updated
) VALUES (
    {TARGET_GUILD_ID}, {user_id}, {username}, {region}, 1500.0, 350.0,
    {games_played}, {wins}, {losses}, {draws}, '{current_time}', '{current_time}'
);
"""
        output_file.write(sql)
        migrated_count += 1
        print(f"Generated SQL for user: {player['username']} (ID: {user_id})")
    
    output_file.write(f"\n-- Migrated {migrated_count} players\n\n")
    return migrated_count

def generate_matches_sql(trueskill_games, output_file):
    """Generate SQL INSERT statements for TrueSkill games as match records"""
    migrated_count = 0
    
    output_file.write("-- TrueSkill Games Migration\n\n")
    
    # Create table if not exists
    output_file.write("""-- Create matches table if it doesn't exist
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id TEXT UNIQUE NOT NULL,
    guild_id INTEGER NOT NULL,
    created_by INTEGER NOT NULL,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    status TEXT DEFAULT 'completed',
    total_teams INTEGER DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

""")
    
    for game in trueskill_games:
        game_id = escape_sql_string(game["game_id"])
        
        # Parse timestamps
        try:
            created_at = datetime.strptime(game["created_at"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
            completed_at = datetime.strptime(game["completed_at"], "%Y-%m-%d %H:%M:%S").strftime("%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            print(f"Error parsing timestamps for game {game['game_id']}: {e}")
            continue
        
        # Use INSERT OR IGNORE to avoid duplicates
        sql = f"""INSERT OR IGNORE INTO matches (
    match_id, guild_id, created_by, start_time, end_time, status, total_teams, created_at
) VALUES (
    {game_id}, {TARGET_GUILD_ID}, 0, '{created_at}', '{completed_at}', 'completed', 2, '{created_at}'
);
"""
        output_file.write(sql)
        migrated_count += 1
        print(f"Generated SQL for match: {game['game_id']} ({created_at})")
    
    output_file.write(f"\n-- Migrated {migrated_count} matches\n\n")
    return migrated_count

def main():
    print("TrueSkill Data SQL Export Script")
    print("=" * 40)
    print(f"Source: {TRUESKILL_SERVICE_URL}")
    print(f"Target Guild ID: {TARGET_GUILD_ID}")
    print("Note: Rating information will NOT be migrated")
    print()
    
    # Fetch TrueSkill data
    print("Fetching TrueSkill players...")
    trueskill_players = fetch_trueskill_players()
    
    print("Fetching TrueSkill games...")
    trueskill_games = fetch_trueskill_games()
    
    if not trueskill_players:
        print("Failed to fetch TrueSkill players. Exiting.")
        return 1
    
    if not trueskill_games:
        print("Failed to fetch TrueSkill games. Continuing with players only.")
        trueskill_games = []
    
    print(f"Found {len(trueskill_players)} players and {len(trueskill_games)} games")
    print()
    
    # Show preview of data
    print("Preview of players to export:")
    for i, player in enumerate(trueskill_players[:5]):
        print(f"  {i+1}. {player['username']} (ID: {player['user_id']}) - {player['games_played']} games")
    
    if len(trueskill_players) > 5:
        print(f"  ... and {len(trueskill_players) - 5} more players")
    
    if trueskill_games:
        print(f"\nPreview of games to export:")
        for i, game in enumerate(trueskill_games[:3]):
            print(f"  {i+1}. Game {game['game_id']} - {game['created_at']}")
        if len(trueskill_games) > 3:
            print(f"  ... and {len(trueskill_games) - 3} more games")
    
    print()
    
    # Get output filename
    default_filename = f"trueskill_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
    filename = input(f"Output filename (default: {default_filename}): ").strip()
    if not filename:
        filename = default_filename
    
    # Confirm export
    confirm = input(f"Proceed with SQL export to '{filename}'? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Export cancelled.")
        return 0
    
    try:
        with open(filename, 'w', encoding='utf-8') as output_file:
            # Write header
            output_file.write("-- TrueSkill Data Migration SQL Export\n")
            output_file.write(f"-- Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            output_file.write(f"-- Source: {TRUESKILL_SERVICE_URL}\n")
            output_file.write(f"-- Target Guild ID: {TARGET_GUILD_ID}\n")
            output_file.write("-- \n")
            output_file.write("-- Usage: sqlite3 your_database.db < " + filename + "\n")
            output_file.write("-- \n\n")
            
            # Begin transaction
            output_file.write("BEGIN TRANSACTION;\n\n")
            
            # Export players
            print(f"\nGenerating SQL for players...")
            player_count = generate_player_sql(trueskill_players, output_file)
            
            # Export matches
            if trueskill_games:
                print(f"\nGenerating SQL for matches...")
                match_count = generate_matches_sql(trueskill_games, output_file)
            else:
                match_count = 0
            
            # Commit transaction
            output_file.write("COMMIT;\n\n")
            
            # Write summary
            output_file.write(f"-- Migration Summary:\n")
            output_file.write(f"-- Players exported: {player_count}\n")
            output_file.write(f"-- Matches exported: {match_count}\n")
            output_file.write(f"-- Total records: {player_count + match_count}\n")
        
        print(f"\nSQL export completed successfully!")
        print(f"Output file: {filename}")
        print(f"Players exported: {player_count}")
        print(f"Matches exported: {match_count}")
        print(f"Total records: {player_count + match_count}")
        print(f"\nTo import into SQLite3:")
        print(f"  sqlite3 your_database.db < {filename}")
        
        return 0
        
    except Exception as e:
        print(f"Error during export: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
