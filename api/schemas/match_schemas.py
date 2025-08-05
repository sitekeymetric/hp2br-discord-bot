from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID

class MatchCreate(BaseModel):
    guild_id: int
    created_by: int
    total_teams: int

class MatchPlayerCreate(BaseModel):
    user_id: int
    guild_id: int
    team_number: int

class MatchResultUpdate(BaseModel):
    result_type: str  # "win_loss", "draw", "cancelled"
    winning_team: Optional[int] = None

class MatchPlayerResponse(BaseModel):
    user_id: int
    guild_id: int
    team_number: int
    rating_mu_before: float
    rating_sigma_before: float
    rating_mu_after: Optional[float]
    rating_sigma_after: Optional[float]
    result: str
    
    class Config:
        orm_mode = True

class MatchPlayerWithDateResponse(BaseModel):
    user_id: int
    guild_id: int
    team_number: int
    rating_mu_before: float
    rating_sigma_before: float
    rating_mu_after: Optional[float]
    rating_sigma_after: Optional[float]
    result: str
    match_id: UUID
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    result_type: Optional[str]
    
    class Config:
        orm_mode = True

class MatchResponse(BaseModel):
    match_id: UUID
    guild_id: int
    created_by: int
    start_time: datetime
    end_time: Optional[datetime]
    status: str
    result_type: Optional[str]
    winning_team: Optional[int]
    total_teams: int
    players: List[MatchPlayerResponse] = []
    
    class Config:
        orm_mode = True