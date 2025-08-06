from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User, MatchPlayer, MatchStatus, PlayerResult, ResultType
from services.match_service import MatchService
from services.user_service import UserService
from services.rating_service import GlickoRatingService, Rating
from schemas.match_schemas import MatchCreate, MatchPlayerCreate, MatchResultUpdate, MatchResponse, MatchPlayerResponse
from typing import List
from uuid import UUID
from datetime import datetime

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
    
    elif result_data.result_type == "forfeit":
        # Handle forfeit scenario - all players lose, small rating decrease
        for team_num, team_players in teams.items():
            team_ratings = [Rating(p.rating_mu_before, p.rating_sigma_before) for p in team_players]
            # Use 0.25 score for forfeit (worse than draw, but not as bad as full loss)
            updated_ratings = GlickoRatingService.update_ratings(team_ratings, [0.25] * len(team_ratings))
            
            # Update database
            for player, new_rating in zip(team_players, updated_ratings):
                player.rating_mu_after = new_rating.mu
                player.rating_sigma_after = new_rating.sigma
                
                # Update user's current rating (only from COMPLETED matches)
                UserService.update_user_rating(db, player.guild_id, player.user_id, new_rating.mu, new_rating.sigma)
                
                # Update user's stats (legacy - kept for compatibility)
                UserService.update_user_stats(db, player.guild_id, player.user_id, "loss")
    
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

@router.get("/user/{guild_id}/{user_id}/completed")
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

@router.put("/{match_id}/placement-result")
def record_placement_result(match_id: str, team_placements: dict, db: Session = Depends(get_db)):
    """Record placement-based match result"""
    try:
        # Validate match exists and is pending
        match = MatchService.get_match(db, match_id)
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        if match.status != MatchStatus.PENDING:
            raise HTTPException(status_code=400, detail="Match is not in pending status")
        
        # Get all players in the match
        players = db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()
        if not players:
            raise HTTPException(status_code=404, detail="No players found for this match")
        
        # Group players by team
        teams = {}
        for player in players:
            if player.team_number not in teams:
                teams[player.team_number] = []
            teams[player.team_number].append(player)
        
        # Validate team_placements
        team_placements_int = {}
        for team_str, placement in team_placements.items():
            try:
                team_num = int(team_str)
                placement_num = int(placement)
                team_placements_int[team_num] = placement_num
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid team number or placement: {team_str} -> {placement}")
        
        # Validate all teams have placements
        if set(team_placements_int.keys()) != set(teams.keys()):
            raise HTTPException(status_code=400, detail="All teams must have placements")
        
        # Validate placements are unique and consecutive
        placements = list(team_placements_int.values())
        if len(set(placements)) != len(placements):
            raise HTTPException(status_code=400, detail="All placements must be unique")
        
        expected_placements = set(range(1, len(teams) + 1))
        if set(placements) != expected_placements:
            raise HTTPException(status_code=400, detail=f"Placements must be 1 through {len(teams)}")
        
        # Calculate rating changes and update players
        for team_num, placement in team_placements_int.items():
            team_players = teams[team_num]
            
            # Calculate rating change based on placement
            rating_change = calculate_placement_rating_change(placement)
            
            # Determine result based on placement
            if placement == 1:
                result = PlayerResult.WIN
            elif placement <= len(teams) // 2:
                result = PlayerResult.DRAW if len(teams) > 2 else PlayerResult.LOSS
            else:
                result = PlayerResult.LOSS
            
            # Update each player in the team
            for player in team_players:
                # Get user for rating calculation
                user = db.query(User).filter(
                    User.guild_id == player.guild_id,
                    User.user_id == player.user_id
                ).first()
                
                if not user:
                    continue
                
                # Calculate new rating using simplified approach
                old_mu = user.rating_mu
                old_sigma = user.rating_sigma
                
                # Apply rating change
                new_mu = max(100, min(3000, old_mu + rating_change))  # Clamp between 100-3000
                new_sigma = max(50, old_sigma * 0.99)  # Slightly reduce uncertainty
                
                # Update player record
                player.team_placement = placement
                player.rating_mu_after = new_mu
                player.rating_sigma_after = new_sigma
                player.result = result
                
                # Update user rating
                user.rating_mu = new_mu
                user.rating_sigma = new_sigma
                
                # Update user statistics
                if result == PlayerResult.WIN:
                    user.wins += 1
                elif result == PlayerResult.LOSS:
                    user.losses += 1
                else:
                    user.draws += 1
                
                user.games_played += 1
        
        # Update match status
        match.status = MatchStatus.COMPLETED
        match.result_type = ResultType.PLACEMENT
        match.end_time = datetime.utcnow()
        
        # Find winning team (placement 1)
        winning_team = None
        for team_num, placement in team_placements_int.items():
            if placement == 1:
                winning_team = team_num
                break
        match.winning_team = winning_team
        
        # Commit all changes
        db.commit()
        
        return {"message": "Placement results recorded successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to record placement result: {str(e)}")

def calculate_placement_rating_change(placement: int, baseline_rank: int = 7, max_rank: int = 30) -> float:
    """Calculate rating change based on placement (Rank 7 baseline system)"""
    if placement <= baseline_rank:
        # Above baseline: scale from 0 to +25
        if placement == baseline_rank:
            return 0.0
        performance_score = (baseline_rank - placement) / (baseline_rank - 1)
        rating_change = performance_score * 25
    else:
        # Below baseline: scale from 0 to -40
        if placement >= max_rank:
            return -40.0
        performance_score = (placement - baseline_rank) / (max_rank - baseline_rank)
        rating_change = -performance_score * 40
    
    return rating_change