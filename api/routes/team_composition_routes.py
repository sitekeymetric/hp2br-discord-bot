"""
Team Composition API Routes
REST endpoints for team composition analysis
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from services.team_composition_service import TeamCompositionService
from typing import List, Dict
from pydantic import BaseModel

router = APIRouter(prefix="/team-compositions", tags=["team-compositions"])

# Pydantic models for API responses
class PartnershipResponse(BaseModel):
    partnership: str
    user_ids: str
    wins: int

class TeamCompositionResponse(BaseModel):
    composition: str
    user_ids: str
    wins: int

class TeamCompositionStatsResponse(BaseModel):
    total_matches: int
    top_partnerships: List[PartnershipResponse]
    top_trios: List[TeamCompositionResponse]
    top_squads: List[TeamCompositionResponse]

@router.get("/partnerships/{guild_id}", response_model=List[PartnershipResponse])
def get_top_partnerships(guild_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """Get most successful 2-player partnerships"""
    try:
        partnerships = TeamCompositionService.get_top_partnerships(db, guild_id, limit)
        return partnerships
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get partnerships: {str(e)}")

@router.get("/trios/{guild_id}", response_model=List[TeamCompositionResponse])
def get_top_trios(guild_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """Get most successful 3-player team compositions"""
    try:
        trios = TeamCompositionService.get_top_trio_compositions(db, guild_id, limit)
        return trios
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trio compositions: {str(e)}")

@router.get("/squads/{guild_id}", response_model=List[TeamCompositionResponse])
def get_top_squads(guild_id: int, limit: int = 5, db: Session = Depends(get_db)):
    """Get most successful 4-player team compositions"""
    try:
        squads = TeamCompositionService.get_top_squad_compositions(db, guild_id, limit)
        return squads
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get squad compositions: {str(e)}")

@router.get("/stats/{guild_id}", response_model=TeamCompositionStatsResponse)
def get_team_composition_stats(guild_id: int, db: Session = Depends(get_db)):
    """Get comprehensive team composition statistics"""
    try:
        stats = TeamCompositionService.get_team_composition_stats(db, guild_id)
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get team composition stats: {str(e)}")
