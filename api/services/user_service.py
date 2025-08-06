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
        """Get user by guild_id and user_id (excludes soft-deleted users)"""
        return db.query(User).filter(
            User.guild_id == guild_id,
            User.user_id == user_id,
            User.deleted_at.is_(None)  # Exclude soft-deleted users
        ).first()
    
    @staticmethod
    def get_guild_users(db: Session, guild_id: int) -> List[User]:
        """Get all users in a guild (excludes soft-deleted users)"""
        return db.query(User).filter(
            User.guild_id == guild_id,
            User.deleted_at.is_(None)  # Exclude soft-deleted users
        ).all()
    
    @staticmethod
    def get_guild_users_with_completed_stats(db: Session, guild_id: int) -> List[dict]:
        """Get all users in a guild with statistics based only on COMPLETED matches (excludes soft-deleted users)"""
        users = db.query(User).filter(
            User.guild_id == guild_id,
            User.deleted_at.is_(None)  # Exclude soft-deleted users
        ).all()
        
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
        """Soft delete a user from the database (preserves match history)"""
        user = UserService.get_user(db, guild_id, user_id)
        if not user:
            return False
        
        try:
            # Soft delete: set deleted_at timestamp instead of actually deleting
            from datetime import datetime
            user.deleted_at = datetime.utcnow()
            user.username = f"[DELETED] {user.username}"  # Mark as deleted in username
            
            db.commit()
            return True
            
        except Exception as e:
            db.rollback()
            raise e
    
    @staticmethod
    def get_user_teammate_stats(db: Session, guild_id: int, user_id: int, limit: int = 10):
        """Get two categories of teammate statistics for a user"""
        from sqlalchemy import func, and_, case
        
        # Get all matches where the user participated and completed
        user_matches = db.query(
            MatchPlayer.match_id, 
            MatchPlayer.team_number, 
            MatchPlayer.result,
            MatchPlayer.team_placement,
            MatchPlayer.rating_mu_before,
            MatchPlayer.rating_mu_after
        ).filter(
            MatchPlayer.guild_id == guild_id,
            MatchPlayer.user_id == user_id
        ).join(Match).filter(
            Match.status == MatchStatus.COMPLETED
        ).all()
        
        # Create dictionaries to track teammate statistics
        teammate_stats = {}
        
        for user_match_id, user_team_number, user_result, user_placement, rating_before, rating_after in user_matches:
            # Find all other players who were on the same team in this match
            teammates_in_match = db.query(MatchPlayer).filter(
                MatchPlayer.match_id == user_match_id,
                MatchPlayer.team_number == user_team_number,
                MatchPlayer.user_id != user_id,  # Exclude the user themselves
                MatchPlayer.guild_id == guild_id
            ).all()
            
            # Calculate skill change for this match
            skill_change = 0
            if rating_after and rating_before:
                skill_change = rating_after - rating_before
            
            # Track if this was a 1st place finish
            is_first_place = user_placement == 1 if user_placement else False
            
            # Update statistics for each teammate
            for teammate in teammates_in_match:
                teammate_id = teammate.user_id
                
                if teammate_id not in teammate_stats:
                    teammate_stats[teammate_id] = {
                        'games_together': 0,
                        'wins_together': 0,
                        'first_place_wins': 0,
                        'total_skill_change': 0
                    }
                
                teammate_stats[teammate_id]['games_together'] += 1
                teammate_stats[teammate_id]['total_skill_change'] += skill_change
                
                if user_result == PlayerResult.WIN:
                    teammate_stats[teammate_id]['wins_together'] += 1
                
                if is_first_place:
                    teammate_stats[teammate_id]['first_place_wins'] += 1
        
        # Create two separate result lists
        frequent_partners = []
        championship_partners = []
        
        for teammate_id, stats in teammate_stats.items():
            # Get teammate user info (exclude soft-deleted users)
            teammate_user = db.query(User).filter(
                User.guild_id == guild_id,
                User.user_id == teammate_id,
                User.deleted_at.is_(None)
            ).first()
            
            if teammate_user and stats['games_together'] > 0:
                avg_skill_change = stats['total_skill_change'] / stats['games_together']
                win_rate = (stats['wins_together'] / stats['games_together'] * 100)
                
                # Most Frequent Partners (by games together)
                frequent_partners.append({
                    'teammate_username': teammate_user.username,
                    'games_together': stats['games_together'],
                    'avg_skill_change': avg_skill_change
                })
                
                # Championship Partners (by 1st place wins)
                if stats['first_place_wins'] > 0:
                    championship_partners.append({
                        'teammate_username': teammate_user.username,
                        'first_place_wins': stats['first_place_wins'],
                        'win_rate': win_rate
                    })
        
        # Sort both categories
        frequent_partners.sort(key=lambda x: x['games_together'], reverse=True)
        championship_partners.sort(key=lambda x: x['first_place_wins'], reverse=True)
        
        return {
            'frequent_partners': frequent_partners[:5],
            'championship_partners': championship_partners[:5]
        }