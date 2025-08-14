"""
Team Composition API Routes
REST endpoints for team composition analysis
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from services.team_composition_service import TeamCompositionService
from services.enhanced_team_composition_service import EnhancedTeamCompositionService
from typing import List, Dict
from pydantic import BaseModel

router = APIRouter(prefix="/team-compositions", tags=["team-compositions"])

# Pydantic models for API responses
class PartnershipResponse(BaseModel):
    partnership: str
    user_ids: str
    wins: int

class EnhancedPartnershipResponse(BaseModel):
    partnership: str
    user_ids: str
    matches_played: int
    avg_placement: float
    avg_rating_change: float
    performance_score: float
    top3_finishes: int
    positive_rating_matches: int

class TeamCompositionResponse(BaseModel):
    composition: str
    user_ids: str
    wins: int

class EnhancedTeamCompositionResponse(BaseModel):
    composition: str
    user_ids: str
    matches_played: int
    avg_placement: float
    avg_rating_change: float
    performance_score: float
    top3_finishes: int

class TeamCompositionStatsResponse(BaseModel):
    total_matches: int
    top_partnerships: List[PartnershipResponse]
    top_trios: List[TeamCompositionResponse]
    top_squads: List[TeamCompositionResponse]

class EnhancedTeamCompositionStatsResponse(BaseModel):
    total_matches: int
    analysis_type: str
    top_partnerships: List[EnhancedPartnershipResponse]
    top_trios: List[EnhancedTeamCompositionResponse]
    top_squads: List[EnhancedTeamCompositionResponse]

# Original win-based endpoints
@router.get("/partnerships/{guild_id}", response_model=List[PartnershipResponse])
def get_top_partnerships(guild_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """Get most successful 2-player partnerships (win-based)"""
    try:
        partnerships = TeamCompositionService.get_top_partnerships(db, guild_id, limit)
        return partnerships
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get partnerships: {str(e)}")

@router.get("/trios/{guild_id}", response_model=List[TeamCompositionResponse])
def get_top_trios(guild_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """Get most successful 3-player team compositions (win-based)"""
    try:
        trios = TeamCompositionService.get_top_trio_compositions(db, guild_id, limit)
        return trios
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trio compositions: {str(e)}")

@router.get("/squads/{guild_id}", response_model=List[TeamCompositionResponse])
def get_top_squads(guild_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """Get most successful 4-player team compositions (win-based)"""
    try:
        squads = TeamCompositionService.get_top_squad_compositions(db, guild_id, limit)
        return squads
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get squad compositions: {str(e)}")

@router.get("/stats/{guild_id}", response_model=TeamCompositionStatsResponse)
def get_team_composition_stats(guild_id: int, db: Session = Depends(get_db)):
    """Get comprehensive team composition statistics (win-based)"""
    try:
        stats = TeamCompositionService.get_team_composition_stats(db, guild_id)
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team composition stats: {str(e)}")

# Enhanced performance-based endpoints
@router.get("/performance/partnerships/{guild_id}", response_model=List[EnhancedPartnershipResponse])
def get_performance_partnerships(guild_id: int, limit: int = 15, db: Session = Depends(get_db)):
    """Get best performing 2-player partnerships (performance-based)"""
    try:
        partnerships = EnhancedTeamCompositionService.get_performance_based_partnerships(db, guild_id, limit)
        return partnerships
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance partnerships: {str(e)}")

@router.get("/performance/trios/{guild_id}", response_model=List[EnhancedTeamCompositionResponse])
def get_performance_trios(guild_id: int, limit: int = 15, db: Session = Depends(get_db)):
    """Get best performing 3-player team compositions (performance-based)"""
    try:
        trios = EnhancedTeamCompositionService.get_performance_based_trios(db, guild_id, limit)
        return trios
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance trio compositions: {str(e)}")

@router.get("/performance/squads/{guild_id}", response_model=List[EnhancedTeamCompositionResponse])
def get_performance_squads(guild_id: int, limit: int = 15, db: Session = Depends(get_db)):
    """Get best performing 4-player team compositions (performance-based)"""
    try:
        squads = EnhancedTeamCompositionService.get_performance_based_squads(db, guild_id, limit)
        return squads
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get performance squad compositions: {str(e)}")

@router.get("/performance/stats/{guild_id}", response_model=EnhancedTeamCompositionStatsResponse)
def get_enhanced_team_composition_stats(guild_id: int, db: Session = Depends(get_db)):
    """Get comprehensive performance-based team composition statistics"""
    try:
        stats = EnhancedTeamCompositionService.get_enhanced_team_composition_stats(db, guild_id)
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get enhanced team composition stats: {str(e)}")
