from sqlalchemy.orm import Session
from database.models import User
from schemas.user_schemas import UserCreate, UserUpdate
from typing import List, Optional

class UserService:
    @staticmethod
    def create_user(db: Session, user_data: UserCreate) -> User:
        """Create a new user"""
        db_user = User(**user_data.dict())
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    
    @staticmethod
    def get_user(db: Session, guild_id: int, user_id: int) -> Optional[User]:
        """Get user by guild_id and user_id"""
        return db.query(User).filter(
            User.guild_id == guild_id,
            User.user_id == user_id
        ).first()
    
    @staticmethod
    def get_guild_users(db: Session, guild_id: int) -> List[User]:
        """Get all users in a guild"""
        return db.query(User).filter(User.guild_id == guild_id).all()
    
    @staticmethod
    def update_user(db: Session, guild_id: int, user_id: int, update_data: UserUpdate) -> Optional[User]:
        """Update user information"""
        user = UserService.get_user(db, guild_id, user_id)
        if not user:
            return None
        
        for field, value in update_data.dict(exclude_unset=True).items():
            setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_user_rating(db: Session, guild_id: int, user_id: int, new_mu: float, new_sigma: float) -> Optional[User]:
        """Update user's rating after a match"""
        user = UserService.get_user(db, guild_id, user_id)
        if not user:
            return None
        
        user.rating_mu = new_mu
        user.rating_sigma = new_sigma
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def update_user_stats(db: Session, guild_id: int, user_id: int, result: str) -> Optional[User]:
        """Update user's game statistics"""
        user = UserService.get_user(db, guild_id, user_id)
        if not user:
            return None
        
        user.games_played += 1
        
        if result == "win":
            user.wins += 1
        elif result == "loss":
            user.losses += 1
        elif result == "draw":
            user.draws += 1
        
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def delete_user(db: Session, guild_id: int, user_id: int) -> bool:
        """Delete a user from the database"""
        user = UserService.get_user(db, guild_id, user_id)
        if not user:
            return False
        
        db.delete(user)
        db.commit()
        return True