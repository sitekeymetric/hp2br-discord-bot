from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    guild_id: int
    user_id: int
    username: str
    region_code: Optional[str] = None

class UserUpdate(BaseModel):
    username: Optional[str] = None
    region_code: Optional[str] = None

class UserResponse(BaseModel):
    guild_id: int
    user_id: int
    username: str
    region_code: Optional[str]
    rating_mu: float
    rating_sigma: float
    games_played: int
    wins: int
    losses: int
    draws: int
    created_at: datetime
    last_updated: datetime
    
    class Config:
        orm_mode = True