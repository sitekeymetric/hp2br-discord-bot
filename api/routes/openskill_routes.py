"""
OpenSkill API Routes
REST endpoints for OpenSkill parallel rating system
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from services.openskill_data_service import OpenSkillDataService
from database.openskill_models import OpenSkillRating, OpenSkillMatchHistory
from typing import List, Dict
from pydantic import BaseModel

router = APIRouter(prefix="/openskill", tags=["openskill"])

# Pydantic models for API responses
class OpenSkillRatingResponse(BaseModel):
    guild_id: int
    user_id: int
    mu: float
    sigma: float
    display_rating: float
    ordinal: float
    games_played: int
    last_updated: str
    
    class Config:
        from_attributes = True

class OpenSkillMatchHistoryResponse(BaseModel):
    id: int
    match_id: str
    guild_id: int
    user_id: int
    team_number: int
    team_placement: int
    total_competitors: int
    guild_teams_count: int
    external_teams_count: int
    competition_type: str
    mu_before: float
    sigma_before: float
    mu_after: float
    sigma_after: float
    rating_change: float
    display_rating_before: float
    display_rating_after: float
    created_at: str
    
    class Config:
        from_attributes = True

class OpenSkillStatsResponse(BaseModel):
    total_users: int
    active_users: int
    total_matches: int
    average_rating: float

@router.get("/ratings/{guild_id}", response_model=List[OpenSkillRatingResponse])
def get_guild_openskill_leaderboard(guild_id: int, limit: int = 25, db: Session = Depends(get_db)):
    """Get OpenSkill leaderboard for a guild"""
    try:
        ratings = OpenSkillDataService.get_guild_leaderboard(db, guild_id, limit)
        
        response_data = []
        for rating in ratings:
            response_data.append({
                'guild_id': rating.guild_id,
                'user_id': rating.user_id,
                'mu': rating.mu,
                'sigma': rating.sigma,
                'display_rating': rating.display_rating,
                'ordinal': rating.ordinal,
                'games_played': rating.games_played,
                'last_updated': rating.last_updated.isoformat()
            })
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get OpenSkill leaderboard: {str(e)}")

@router.get("/ratings/{guild_id}/{user_id}", response_model=OpenSkillRatingResponse)
def get_user_openskill_rating(guild_id: int, user_id: int, db: Session = Depends(get_db)):
    """Get OpenSkill rating for a specific user"""
    try:
        rating = OpenSkillDataService.get_user_rating(db, guild_id, user_id)
        
        if not rating:
            raise HTTPException(status_code=404, detail="User not found in OpenSkill system")
        
        return {
            'guild_id': rating.guild_id,
            'user_id': rating.user_id,
            'mu': rating.mu,
            'sigma': rating.sigma,
            'display_rating': rating.display_rating,
            'ordinal': rating.ordinal,
            'games_played': rating.games_played,
            'last_updated': rating.last_updated.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user OpenSkill rating: {str(e)}")

@router.get("/history/{guild_id}/{user_id}", response_model=List[OpenSkillMatchHistoryResponse])
def get_user_openskill_history(guild_id: int, user_id: int, limit: int = 20, db: Session = Depends(get_db)):
    """Get OpenSkill match history for a user"""
    try:
        history = OpenSkillDataService.get_user_match_history(db, guild_id, user_id, limit)
        
        response_data = []
        for match in history:
            response_data.append({
                'id': match.id,
                'match_id': match.match_id,
                'guild_id': match.guild_id,
                'user_id': match.user_id,
                'team_number': match.team_number,
                'team_placement': match.team_placement,
                'total_competitors': match.total_competitors,
                'guild_teams_count': match.guild_teams_count,
                'external_teams_count': match.external_teams_count,
                'competition_type': match.competition_type,
                'mu_before': match.mu_before,
                'sigma_before': match.sigma_before,
                'mu_after': match.mu_after,
                'sigma_after': match.sigma_after,
                'rating_change': match.rating_change,
                'display_rating_before': match.display_rating_before,
                'display_rating_after': match.display_rating_after,
                'created_at': match.created_at.isoformat()
            })
        
        return response_data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user OpenSkill history: {str(e)}")

@router.get("/stats/{guild_id}", response_model=OpenSkillStatsResponse)
def get_guild_openskill_stats(guild_id: int, db: Session = Depends(get_db)):
    """Get OpenSkill statistics for a guild"""
    try:
        stats = OpenSkillDataService.get_guild_statistics(db, guild_id)
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get OpenSkill stats: {str(e)}")

@router.post("/process-match/{match_id}")
def process_match_openskill(match_id: str, team_placements: Dict[str, int], db: Session = Depends(get_db)):
    """Process OpenSkill ratings for a completed match"""
    try:
        # Convert string keys to integers
        team_placements_int = {}
        for team_str, placement in team_placements.items():
            try:
                team_num = int(team_str)
                placement_num = int(placement)
                team_placements_int[team_num] = placement_num
            except (ValueError, TypeError):
                raise HTTPException(status_code=400, detail=f"Invalid team number or placement: {team_str} -> {placement}")
        
        # Process the match
        result = OpenSkillDataService.process_match_openskill_results(db, match_id, team_placements_int)
        
        if result['success']:
            return {
                "message": "OpenSkill ratings processed successfully",
                "players_updated": result['players_updated'],
                "competition_type": result['competition_type'],
                "total_competitors": result['total_competitors']
            }
        else:
            raise HTTPException(status_code=500, detail=f"OpenSkill processing failed: {result['error']}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process OpenSkill match: {str(e)}")

@router.get("/compare/{guild_id}")
def compare_rating_systems(guild_id: int, db: Session = Depends(get_db)):
    """Compare OpenSkill and Placement rating systems for a guild"""
    try:
        from database.models import User
        
        # Get users with both rating systems
        users = db.query(User).filter(User.guild_id == guild_id).all()
        openskill_ratings = OpenSkillDataService.get_guild_leaderboard(db, guild_id, 100)
        
        comparison_data = []
        
        for user in users:
            # Find corresponding OpenSkill rating
            openskill_rating = next((r for r in openskill_ratings if r.user_id == user.user_id), None)
            
            if openskill_rating and user.games_played > 0:
                comparison_data.append({
                    'user_id': user.user_id,
                    'username': user.username,
                    'placement_rating': user.rating_mu,
                    'openskill_display_rating': openskill_rating.display_rating,
                    'placement_games': user.games_played,
                    'openskill_games': openskill_rating.games_played,
                    'placement_uncertainty': user.rating_sigma,
                    'openskill_uncertainty': openskill_rating.sigma
                })
        
        # Sort by placement rating for comparison
        comparison_data.sort(key=lambda x: x['placement_rating'], reverse=True)
        
        return {
            'guild_id': guild_id,
            'total_users': len(comparison_data),
            'users': comparison_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare rating systems: {str(e)}")

@router.post("/initialize/{guild_id}")
def initialize_guild_openskill(guild_id: int, db: Session = Depends(get_db)):
    """Initialize OpenSkill ratings for all users in a guild"""
    try:
        from database.models import User
        
        # Get all users in the guild
        users = db.query(User).filter(User.guild_id == guild_id).all()
        
        initialized_count = 0
        for user in users:
            # Create OpenSkill rating if it doesn't exist
            existing_rating = OpenSkillDataService.get_user_rating(db, guild_id, user.user_id)
            if not existing_rating:
                OpenSkillDataService.get_or_create_user_rating(db, guild_id, user.user_id)
                initialized_count += 1
        
        return {
            'message': f'Initialized OpenSkill ratings for {initialized_count} users',
            'total_users': len(users),
            'initialized_count': initialized_count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initialize OpenSkill ratings: {str(e)}")
