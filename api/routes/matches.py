from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from services.match_service import MatchService
from services.user_service import UserService
from services.rating_service import GlickoRatingService, Rating
from schemas.match_schemas import MatchCreate, MatchPlayerCreate, MatchResultUpdate, MatchResponse, MatchPlayerResponse
from typing import List
from uuid import UUID

router = APIRouter(prefix="/matches", tags=["matches"])

@router.post("/", response_model=MatchResponse)
def create_match(match_data: MatchCreate, db: Session = Depends(get_db)):
    """Create a new match"""
    return MatchService.create_match(db, match_data)

@router.get("/{guild_id}", response_model=List[MatchResponse])
def get_guild_matches(guild_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Get guild's match history"""
    return MatchService.get_guild_matches(db, guild_id, limit)

@router.get("/match/{match_id}", response_model=MatchResponse)
def get_match(match_id: UUID, db: Session = Depends(get_db)):
    """Get specific match details"""
    match = MatchService.get_match(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return match

@router.post("/{match_id}/players", response_model=MatchPlayerResponse)
def add_player_to_match(match_id: UUID, player_data: MatchPlayerCreate, db: Session = Depends(get_db)):
    """Add player to match"""
    match_player = MatchService.add_player_to_match(db, match_id, player_data)
    if not match_player:
        raise HTTPException(status_code=404, detail="User not found")
    return match_player

@router.get("/{match_id}/players", response_model=List[MatchPlayerResponse])
def get_match_players(match_id: UUID, db: Session = Depends(get_db)):
    """Get all players in match"""
    return MatchService.get_match_players(db, match_id)

@router.put("/{match_id}/result")
def update_match_result(match_id: UUID, result_data: MatchResultUpdate, db: Session = Depends(get_db)):
    """Record match result, update player ratings, and clean up pending matches for involved players"""
    match = MatchService.get_match(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    
    # Get players involved in this match before updating
    players = MatchService.get_match_players(db, match_id)
    player_ids = [p.user_id for p in players]
    
    # Update match result (this includes cleanup of pending matches for these players)
    updated_match = MatchService.update_match_result(db, match_id, result_data)
    if not updated_match:
        raise HTTPException(status_code=400, detail="Failed to update match result")
    
    # Group players by team
    teams = {}
    for player in players:
        if player.team_number not in teams:
            teams[player.team_number] = []
        teams[player.team_number].append(player)
    
    # Calculate new ratings based on match result
    if result_data.result_type == "win_loss" and result_data.winning_team:
        # Handle win/loss scenario
        for team_num, team_players in teams.items():
            team_ratings = [Rating(p.rating_mu_before, p.rating_sigma_before) for p in team_players]
            
            if team_num == result_data.winning_team:
                # Winning team
                score = 1.0
            else:
                # Losing team
                score = 0.0
            
            # Simple rating update for each player
            updated_ratings = GlickoRatingService.update_ratings(team_ratings, [score] * len(team_ratings))
            
            # Update database
            for player, new_rating in zip(team_players, updated_ratings):
                player.rating_mu_after = new_rating.mu
                player.rating_sigma_after = new_rating.sigma
                
                # Update user's current rating (only from COMPLETED matches)
                UserService.update_user_rating(db, player.guild_id, player.user_id, new_rating.mu, new_rating.sigma)
                
                # Update user's stats (legacy - kept for compatibility)
                result_str = "win" if team_num == result_data.winning_team else "loss"
                UserService.update_user_stats(db, player.guild_id, player.user_id, result_str)
    
    elif result_data.result_type == "draw":
        # Handle draw scenario
        for team_num, team_players in teams.items():
            team_ratings = [Rating(p.rating_mu_before, p.rating_sigma_before) for p in team_players]
            updated_ratings = GlickoRatingService.update_ratings(team_ratings, [0.5] * len(team_ratings))
            
            # Update database
            for player, new_rating in zip(team_players, updated_ratings):
                player.rating_mu_after = new_rating.mu
                player.rating_sigma_after = new_rating.sigma
                
                # Update user's current rating (only from COMPLETED matches)
                UserService.update_user_rating(db, player.guild_id, player.user_id, new_rating.mu, new_rating.sigma)
                
                # Update user's stats (legacy - kept for compatibility)
                UserService.update_user_stats(db, player.guild_id, player.user_id, "draw")
    
    db.commit()
    
    # Return success message with cleanup info
    cleanup_count = 0  # The cleanup was already done in update_match_result
    return {
        "message": "Match result updated successfully",
        "cleanup_performed": True,
        "players_involved": len(player_ids),
        "note": "Any pending matches for involved players have been automatically cancelled"
    }

@router.get("/{guild_id}/completed", response_model=List[MatchResponse])
def get_guild_completed_matches(guild_id: int, limit: int = 50, db: Session = Depends(get_db)):
    """Get only completed matches for a guild (for statistics and ratings)"""
    return MatchService.get_guild_completed_matches(db, guild_id, limit)

@router.get("/user/{guild_id}/{user_id}/completed", response_model=List[MatchPlayerResponse])
def get_user_completed_match_history(guild_id: int, user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """Get only completed match history for a specific user (for statistics and ratings)"""
    return MatchService.get_user_completed_match_history(db, guild_id, user_id, limit)

@router.delete("/{match_id}")
def cancel_match(match_id: UUID, db: Session = Depends(get_db)):
    """Cancel a match"""
    match = MatchService.cancel_match(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return {"message": "Match cancelled successfully"}

@router.get("/user/{guild_id}/{user_id}/history", response_model=List[MatchPlayerResponse])
def get_user_match_history(guild_id: int, user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """Get match history for a specific user"""
    return MatchService.get_user_match_history(db, guild_id, user_id, limit)