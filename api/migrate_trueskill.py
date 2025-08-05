#!/usr/bin/env python3
"""
Migration script to import TrueSkill user and match data into the local database
(excluding rating information)
"""

import httpx
import sys
import os
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

# Add the api directory to the path so we can import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import get_db, create_tables
from database.models import User, Match, MatchStatus

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

def migrate_players(db: Session, trueskill_players):
    """Migrate TrueSkill players to local database (excluding ratings)"""
    migrated_count = 0
    updated_count = 0
    
    for player in trueskill_players:
        user_id = player["user_id"]
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            User.guild_id == TARGET_GUILD_ID,
            User.user_id == user_id
        ).first()
        
        if existing_user:
            # Update existing user with TrueSkill data (excluding ratings)
            existing_user.username = player["username"]
            existing_user.region_code = player["region"] if player["region"] != "Unknown" else None
            existing_user.games_played = player["games_played"]
            existing_user.wins = player["wins"]
            existing_user.losses = player["losses"]
            existing_user.draws = player["draws"]
            existing_user.last_updated = datetime.utcnow()
            # Keep existing rating_mu and rating_sigma values
            
            updated_count += 1
            print(f"Updated user: {player['username']} (ID: {user_id}) - kept existing ratings")
        else:
            # Create new user with default ratings
            new_user = User(
                guild_id=TARGET_GUILD_ID,
                user_id=user_id,
                username=player["username"],
                region_code=player["region"] if player["region"] != "Unknown" else None,
                rating_mu=1500.0,  # Default rating
                rating_sigma=350.0,  # Default rating
                games_played=player["games_played"],
                wins=player["wins"],
                losses=player["losses"],
                draws=player["draws"],
                created_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            
            db.add(new_user)
            migrated_count += 1
            print(f"Added new user: {player['username']} (ID: {user_id}) - default ratings applied")
    
    return migrated_count, updated_count

def migrate_matches(db: Session, trueskill_games):
    """Migrate TrueSkill games to local database as basic match records"""
    migrated_count = 0
    skipped_count = 0
    
    for game in trueskill_games:
        game_id = game["game_id"]
        
        # Check if match already exists
        existing_match = db.query(Match).filter(Match.match_id == game_id).first()
        
        if existing_match:
            skipped_count += 1
            print(f"Skipped existing match: {game_id}")
            continue
        
        # Parse timestamps
        try:
            created_at = datetime.strptime(game["created_at"], "%Y-%m-%d %H:%M:%S")
            completed_at = datetime.strptime(game["completed_at"], "%Y-%m-%d %H:%M:%S")
        except ValueError as e:
            print(f"Error parsing timestamps for game {game_id}: {e}")
            continue
        
        # Create new match record
        new_match = Match(
            match_id=game_id,  # Use the TrueSkill game_id directly
            guild_id=TARGET_GUILD_ID,
            created_by=0,  # Unknown creator, using 0 as placeholder
            start_time=created_at,
            end_time=completed_at,
            status=MatchStatus.COMPLETED,  # All TrueSkill games are completed
            total_teams=2,  # Assuming 2 teams (common for most games)
            created_at=created_at
        )
        
        db.add(new_match)
        migrated_count += 1
        print(f"Added match: {game_id} ({created_at})")
    
    return migrated_count, skipped_count

def main():
    print("TrueSkill Data Migration Script")
    print("=" * 40)
    print(f"Source: {TRUESKILL_SERVICE_URL}")
    print(f"Target Guild ID: {TARGET_GUILD_ID}")
    print("Note: Rating information will NOT be migrated")
    print()
    
    # Ensure database tables exist
    create_tables()
    
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
    print("Preview of players to migrate:")
    for i, player in enumerate(trueskill_players[:5]):
        print(f"  {i+1}. {player['username']} (ID: {player['user_id']}) - {player['games_played']} games")
    
    if len(trueskill_players) > 5:
        print(f"  ... and {len(trueskill_players) - 5} more players")
    
    if trueskill_games:
        print(f"\nPreview of games to migrate:")
        for i, game in enumerate(trueskill_games[:3]):
            print(f"  {i+1}. Game {game['game_id']} - {game['created_at']}")
        if len(trueskill_games) > 3:
            print(f"  ... and {len(trueskill_games) - 3} more games")
    
    print()
    
    # Confirm migration
    confirm = input("Proceed with migration? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Migration cancelled.")
        return 0
    
    # Get database session
    db = next(get_db())
    
    try:
        # Migrate players
        print("\nMigrating players...")
        player_migrated, player_updated = migrate_players(db, trueskill_players)
        
        # Migrate matches
        if trueskill_games:
            print("\nMigrating matches...")
            match_migrated, match_skipped = migrate_matches(db, trueskill_games)
        else:
            match_migrated, match_skipped = 0, 0
        
        # Commit all changes
        db.commit()
        
        print(f"\nMigration completed successfully!")
        print(f"Players - New: {player_migrated}, Updated: {player_updated}")
        print(f"Matches - New: {match_migrated}, Skipped: {match_skipped}")
        print(f"Total processed: {player_migrated + player_updated + match_migrated}")
        
        return 0
        
    except Exception as e:
        db.rollback()
        print(f"Error during migration: {e}")
        return 1
    finally:
        db.close()

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
