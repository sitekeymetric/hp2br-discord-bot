"""
Advanced Match Routes for Rating System v3.0.0
Handles advanced placement results with opponent strength consideration
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel

from database.connection import get_db
from database.models import Match, MatchPlayer, User
from services.advanced_rating_service import AdvancedRatingService, TeamData, RatingChangeBreakdown


class TeamPlacementData(BaseModel):
    """Team placement data for advanced rating calculation"""
    placement: int
    avg_rating: Optional[float] = None
    players: Optional[List[int]] = None


class AdvancedPlacementRequest(BaseModel):
    """Request model for advanced placement results"""
    team_placements: Dict[int, TeamPlacementData]


class PlayerRatingChange(BaseModel):
    """Individual player rating change details"""
    user_id: int
    username: str
    rating_before: float
    rating_after: float
    rating_change: float
    tier_before: str
    tier_after: str
    breakdown: Dict


class AdvancedPlacementResponse(BaseModel):
    """Response model for advanced placement results"""
    match_id: str
    rating_system_version: str
    player_changes: List[PlayerRatingChange]
    team_summary: Dict[int, Dict]


class RatingPreviewRequest(BaseModel):
    """Request model for rating change preview"""
    player_rating: float
    team_avg_rating: float
    opponent_teams: List[Dict[str, float]]  # [{"avg_rating": 1600}, ...]


class RatingPreviewResponse(BaseModel):
    """Response model for rating change preview"""
    player_rating: float
    team_avg_rating: float
    opponent_strength_diff: float
    placement_previews: Dict[int, float]  # {placement: rating_change}
    tier_info: Dict[str, str]


router = APIRouter(prefix="/advanced-matches", tags=["advanced-matches"])


@router.put("/{match_id}/placement-result", response_model=AdvancedPlacementResponse)
async def record_advanced_placement_result(
    match_id: UUID,
    placement_data: AdvancedPlacementRequest,
    db: Session = Depends(get_db)
):
    """Record match result using advanced rating system with opponent strength consideration"""
    
    try:
        # Validate match exists
        match = db.query(Match).filter(Match.match_id == match_id).first()
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
        
        if match.status == "completed":
            raise HTTPException(status_code=400, detail="Match already completed")
        
        # Get all match players
        match_players = db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()
        if not match_players:
            raise HTTPException(status_code=400, detail="No players found in match")
        
        # Validate team placements
        team_numbers = set(mp.team_number for mp in match_players)
        provided_teams = set(placement_data.team_placements.keys())
        
        if team_numbers != provided_teams:
            raise HTTPException(
                status_code=400, 
                detail=f"Team mismatch. Expected teams: {team_numbers}, provided: {provided_teams}"
            )
        
        # Calculate team averages if not provided
        team_placement_dict = {}
        for team_num, team_data in placement_data.team_placements.items():
            team_players = [mp for mp in match_players if mp.team_number == team_num]
            
            if team_data.avg_rating is None:
                # Calculate team average from players
                avg_rating = sum(mp.rating_mu_before for mp in team_players) / len(team_players)
            else:
                avg_rating = team_data.avg_rating
            
            team_placement_dict[team_num] = {
                'placement': team_data.placement,
                'avg_rating': avg_rating,
                'players': [mp.user_id for mp in team_players]
            }
        
        # Apply advanced rating changes
        rating_changes = AdvancedRatingService.apply_advanced_rating_changes(
            db, str(match_id), team_placement_dict
        )
        
        # Update match metadata
        match.team_ratings = str(team_placement_dict)  # Store as JSON string
        match.rating_system_version = "v3.0.0"
        match.result_type = "placement"
        
        # Calculate average opponent strength for match
        all_ratings = [data['avg_rating'] for data in team_placement_dict.values()]
        match.avg_opponent_strength = sum(all_ratings) / len(all_ratings)
        
        db.commit()
        
        # Prepare response
        player_changes = []
        for match_player in match_players:
            user = db.query(User).filter(
                User.guild_id == match_player.guild_id,
                User.user_id == match_player.user_id
            ).first()
            
            breakdown = rating_changes.get(str(match_player.user_id))
            if breakdown and user:
                player_changes.append(PlayerRatingChange(
                    user_id=match_player.user_id,
                    username=user.username,
                    rating_before=match_player.rating_mu_before,
                    rating_after=match_player.rating_mu_after,
                    rating_change=breakdown.final_change,
                    tier_before=AdvancedRatingService.get_rating_tier_name(match_player.rating_mu_before),
                    tier_after=AdvancedRatingService.get_rating_tier_name(match_player.rating_mu_after),
                    breakdown={
                        "base_score": breakdown.base_score,
                        "opponent_multiplier": breakdown.opponent_multiplier,
                        "individual_adjustment": breakdown.individual_adjustment,
                        "curve_multiplier": breakdown.curve_multiplier,
                        "preliminary_change": breakdown.preliminary_change,
                        "final_change": breakdown.final_change,
                        "max_change_limit": breakdown.max_change_limit
                    }
                ))
        
        # Team summary
        team_summary = {}
        for team_num, data in team_placement_dict.items():
            team_summary[team_num] = {
                "placement": data['placement'],
                "avg_rating": data['avg_rating'],
                "player_count": len(data['players'])
            }
        
        return AdvancedPlacementResponse(
            match_id=str(match_id),
            rating_system_version="v3.0.0",
            player_changes=player_changes,
            team_summary=team_summary
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to record placement result: {str(e)}")


@router.post("/rating-preview", response_model=RatingPreviewResponse)
async def preview_rating_changes(preview_request: RatingPreviewRequest):
    """Preview rating changes for different placements"""
    
    try:
        # Convert opponent data to TeamData objects
        opponent_teams = []
        for i, opponent in enumerate(preview_request.opponent_teams):
            opponent_teams.append(TeamData(
                team_number=i + 2,  # Assuming player is team 1
                placement=0,  # Placeholder
                avg_rating=opponent['avg_rating'],
                players=[]
            ))
        
        # Calculate opponent strength difference
        if opponent_teams:
            avg_opponent_rating = sum(team.avg_rating for team in opponent_teams) / len(opponent_teams)
            strength_diff = avg_opponent_rating - preview_request.team_avg_rating
        else:
            strength_diff = 0.0
        
        # Get rating previews for different placements
        placement_previews = AdvancedRatingService.preview_rating_changes(
            preview_request.player_rating,
            preview_request.team_avg_rating,
            opponent_teams
        )
        
        # Get tier information
        current_tier = AdvancedRatingService.get_rating_tier_name(preview_request.player_rating)
        team_tier = AdvancedRatingService.get_rating_tier_name(preview_request.team_avg_rating)
        
        return RatingPreviewResponse(
            player_rating=preview_request.player_rating,
            team_avg_rating=preview_request.team_avg_rating,
            opponent_strength_diff=strength_diff,
            placement_previews=placement_previews,
            tier_info={
                "player_tier": current_tier,
                "team_tier": team_tier,
                "strength_assessment": "stronger" if strength_diff > 0 else "weaker" if strength_diff < 0 else "similar"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to preview rating changes: {str(e)}")


@router.get("/rating-scale")
async def get_rating_scale():
    """Get the complete rating scale and tier information"""
    
    return {
        "version": "v3.0.0",
        "placement_scores": AdvancedRatingService.PLACEMENT_SCORES,
        "rating_tiers": {
            "Legendary": {"min_rating": 2200, "description": "Top 0.1% - Rank 1 teams"},
            "Elite": {"min_rating": 2000, "description": "Top 1% - Rank 1-2 teams"},
            "Expert": {"min_rating": 1800, "description": "Top 5% - Rank 2-4 teams"},
            "Advanced": {"min_rating": 1600, "description": "Top 15% - Rank 3-6 teams"},
            "Intermediate": {"min_rating": 1400, "description": "Middle 40% - Rank 5-10 teams"},
            "Beginner": {"min_rating": 1200, "description": "Bottom 30% - Rank 8-15 teams"},
            "Novice": {"min_rating": 1000, "description": "Bottom 10% - Rank 12-20 teams"},
            "Learning": {"min_rating": 0, "description": "Bottom 4% - Rank 15-30 teams"}
        },
        "climbing_multipliers": {
            "Elite (2000+)": 0.3,
            "Expert (1800+)": 0.5,
            "Advanced (1600+)": 0.7,
            "Intermediate (1400+)": 0.85,
            "Below Average (<1400)": 1.0
        },
        "dropping_multipliers": {
            "Elite (2000+)": 1.5,
            "Expert (1800+)": 1.3,
            "Advanced (1600+)": 1.1,
            "Lower Tiers (<1600)": 1.0
        }
    }


@router.get("/rating-calculator")
async def get_rating_calculator_info():
    """Get information about the rating calculation system"""
    
    return {
        "version": "v3.0.0",
        "system_name": "Advanced Skill-Based Rating System",
        "description": "Considers opponent strength, individual performance, and applies curved scaling",
        "factors": {
            "base_placement_score": "Score based on final placement (1st = +50, 30th = -345)",
            "opponent_strength_multiplier": "Bonus/penalty based on opponent team ratings (0.2x to 2.2x)",
            "individual_adjustment": "Adjustment based on player vs team average (0.8x to 1.2x)",
            "rating_curve_multiplier": "Climbing penalty/dropping bonus based on current rating"
        },
        "max_change_limit": "15% of current rating or 150 points, whichever is smaller",
        "examples": {
            "underdog_victory": "1200 player beats 1600 teams → +90 points (huge bonus)",
            "expected_elite_win": "2100 player beats 1800 teams → +9 points (slow climbing)",
            "elite_disaster": "2000 player gets 25th place → -330 points (massive drop)"
        }
    }
