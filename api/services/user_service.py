from sqlalchemy.orm import Session
from database.models import User, Match, MatchPlayer, MatchStatus, PlayerResult
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
    def get_guild_users_with_completed_stats(db: Session, guild_id: int) -> List[dict]:
        """Get all users in a guild with statistics based only on COMPLETED matches"""
        users = db.query(User).filter(User.guild_id == guild_id).all()
        
        result = []
        for user in users:
            # Calculate stats from completed matches only
            completed_matches = db.query(MatchPlayer).filter(
                MatchPlayer.guild_id == guild_id,
                MatchPlayer.user_id == user.user_id
            ).join(Match).filter(
                Match.status == MatchStatus.COMPLETED
            ).all()
            
            # Count results from completed matches
            wins = len([m for m in completed_matches if m.result == PlayerResult.WIN])
            losses = len([m for m in completed_matches if m.result == PlayerResult.LOSS])
            draws = len([m for m in completed_matches if m.result == PlayerResult.DRAW])
            games_played = len(completed_matches)
            
            user_dict = {
                'guild_id': user.guild_id,
                'user_id': user.user_id,
                'username': user.username,
                'region_code': user.region_code,
                'rating_mu': user.rating_mu,
                'rating_sigma': user.rating_sigma,
                'games_played': games_played,  # From completed matches only
                'wins': wins,                  # From completed matches only
                'losses': losses,              # From completed matches only
                'draws': draws,                # From completed matches only
                'created_at': user.created_at,
                'last_updated': user.last_updated
            }
            result.append(user_dict)
        
        return result
    
    @staticmethod
    def get_user_with_completed_stats(db: Session, guild_id: int, user_id: int) -> Optional[dict]:
        """Get user with statistics based only on COMPLETED matches"""
        user = UserService.get_user(db, guild_id, user_id)
        if not user:
            return None
        
        # Calculate stats from completed matches only
        completed_matches = db.query(MatchPlayer).filter(
            MatchPlayer.guild_id == guild_id,
            MatchPlayer.user_id == user_id
        ).join(Match).filter(
            Match.status == MatchStatus.COMPLETED
        ).all()
        
        # Count results from completed matches
        wins = len([m for m in completed_matches if m.result == PlayerResult.WIN])
        losses = len([m for m in completed_matches if m.result == PlayerResult.LOSS])
        draws = len([m for m in completed_matches if m.result == PlayerResult.DRAW])
        games_played = len(completed_matches)
        
        return {
            'guild_id': user.guild_id,
            'user_id': user.user_id,
            'username': user.username,
            'region_code': user.region_code,
            'rating_mu': user.rating_mu,
            'rating_sigma': user.rating_sigma,
            'games_played': games_played,  # From completed matches only
            'wins': wins,                  # From completed matches only
            'losses': losses,              # From completed matches only
            'draws': draws,                # From completed matches only
            'created_at': user.created_at,
            'last_updated': user.last_updated
        }
    
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
        """Update user's game statistics (legacy method - kept for compatibility)"""
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