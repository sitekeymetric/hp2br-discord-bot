from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database.connection import get_db
from services.user_service import UserService
from schemas.user_schemas import UserCreate, UserUpdate, UserResponse
from typing import List

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    existing_user = UserService.get_user(db, user_data.guild_id, user_data.user_id)
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    return UserService.create_user(db, user_data)

@router.get("/{guild_id}", response_model=List[UserResponse])
def get_guild_users(guild_id: int, db: Session = Depends(get_db)):
    """Get all users in a guild"""
    return UserService.get_guild_users(db, guild_id)

# Put specific routes with literal strings BEFORE parameterized routes
@router.get("/{guild_id}/completed-stats")
def get_guild_users_completed_stats(guild_id: int, db: Session = Depends(get_db)):
    """Get all users in a guild with statistics based only on COMPLETED matches"""
    return UserService.get_guild_users_with_completed_stats(db, guild_id)

@router.get("/{guild_id}/{user_id}/completed-stats")
def get_user_completed_stats(guild_id: int, user_id: int, db: Session = Depends(get_db)):
    """Get specific user with statistics based only on COMPLETED matches"""
    user_stats = UserService.get_user_with_completed_stats(db, guild_id, user_id)
    if not user_stats:
        raise HTTPException(status_code=404, detail="User not found")
    return user_stats

@router.get("/{guild_id}/{user_id}/teammates")
def get_user_teammate_stats(guild_id: int, user_id: int, limit: int = 10, db: Session = Depends(get_db)):
    """Get teammate statistics for a user - most frequent teammates and win rates"""
    teammate_stats = UserService.get_user_teammate_stats(db, guild_id, user_id, limit)
    return teammate_stats

@router.get("/{guild_id}/{user_id}/rating")
def get_user_rating(guild_id: int, user_id: int, db: Session = Depends(get_db)):
    """Get user's current rating"""
    user = UserService.get_user(db, guild_id, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"rating_mu": user.rating_mu, "rating_sigma": user.rating_sigma}

# Generic parameterized routes come AFTER specific routes
@router.get("/{guild_id}/{user_id}", response_model=UserResponse)
def get_user(guild_id: int, user_id: int, db: Session = Depends(get_db)):
    """Get specific user"""
    user = UserService.get_user(db, guild_id, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{guild_id}/{user_id}", response_model=UserResponse)
def update_user(guild_id: int, user_id: int, update_data: UserUpdate, db: Session = Depends(get_db)):
    """Update user information"""
    user = UserService.update_user(db, guild_id, user_id, update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{guild_id}/{user_id}/rating", response_model=UserResponse)
def update_user_rating_put(guild_id: int, user_id: int, new_mu: float, new_sigma: float, db: Session = Depends(get_db)):
    """Update user's rating (internal use)"""
    user = UserService.update_user_rating(db, guild_id, user_id, new_mu, new_sigma)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.delete("/{guild_id}/{user_id}")
def delete_user(guild_id: int, user_id: int, db: Session = Depends(get_db)):
    """Delete a user from the system"""
    success = UserService.delete_user(db, guild_id, user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}