from sqlalchemy.orm import Session
from database.models import Match, MatchPlayer, User, MatchStatus, ResultType, PlayerResult
from schemas.match_schemas import MatchCreate, MatchPlayerCreate, MatchResultUpdate
from typing import List, Optional
from uuid import UUID
from datetime import datetime

class MatchService:
    @staticmethod
    def create_match(db: Session, match_data: MatchCreate) -> Match:
        """Create a new match"""
        db_match = Match(**match_data.dict())
        db.add(db_match)
        db.commit()
        db.refresh(db_match)
        return db_match
    
    @staticmethod
    def get_match(db: Session, match_id: UUID) -> Optional[Match]:
        """Get match by match_id"""
        return db.query(Match).filter(Match.match_id == match_id).first()
    
    @staticmethod
    def get_guild_matches(db: Session, guild_id: int, limit: int = 50) -> List[Match]:
        """Get recent matches for a guild"""
        return db.query(Match).filter(
            Match.guild_id == guild_id
        ).order_by(Match.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def add_player_to_match(db: Session, match_id: UUID, player_data: MatchPlayerCreate) -> Optional[MatchPlayer]:
        """Add a player to a match"""
        # Get user's current rating
        user = db.query(User).filter(
            User.guild_id == player_data.guild_id,
            User.user_id == player_data.user_id
        ).first()
        
        if not user:
            return None
        
        db_match_player = MatchPlayer(
            match_id=match_id,
            user_id=player_data.user_id,
            guild_id=player_data.guild_id,
            team_number=player_data.team_number,
            rating_mu_before=user.rating_mu,
            rating_sigma_before=user.rating_sigma
        )
        
        db.add(db_match_player)
        db.commit()
        db.refresh(db_match_player)
        return db_match_player
    
    @staticmethod
    def get_match_players(db: Session, match_id: UUID) -> List[MatchPlayer]:
        """Get all players in a match"""
        return db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()
    
    @staticmethod
    def update_match_result(db: Session, match_id: UUID, result_data: MatchResultUpdate) -> Optional[Match]:
        """Update match result and player outcomes"""
        match = MatchService.get_match(db, match_id)
        if not match:
            return None
        
        # Update match status
        match.status = MatchStatus.COMPLETED
        match.result_type = ResultType(result_data.result_type)
        match.winning_team = result_data.winning_team
        match.end_time = datetime.utcnow()
        
        # Update player results
        players = MatchService.get_match_players(db, match_id)
        for player in players:
            if result_data.result_type == "win_loss":
                if player.team_number == result_data.winning_team:
                    player.result = PlayerResult.WIN
                else:
                    player.result = PlayerResult.LOSS
            elif result_data.result_type == "draw":
                player.result = PlayerResult.DRAW
            elif result_data.result_type == "cancelled":
                player.result = PlayerResult.PENDING
        
        db.commit()
        db.refresh(match)
        return match
    
    @staticmethod
    def cancel_match(db: Session, match_id: UUID) -> Optional[Match]:
        """Cancel a match"""
        match = MatchService.get_match(db, match_id)
        if not match:
            return None
        
        match.status = MatchStatus.CANCELLED
        match.result_type = ResultType.CANCELLED
        match.end_time = datetime.utcnow()
        
        # Update all players to cancelled state
        players = MatchService.get_match_players(db, match_id)
        for player in players:
            player.result = PlayerResult.PENDING
        
        db.commit()
        db.refresh(match)
        return match
    
    @staticmethod
    def get_user_match_history(db: Session, guild_id: int, user_id: int, limit: int = 20) -> List[MatchPlayer]:
        """Get match history for a specific user"""
        return db.query(MatchPlayer).filter(
            MatchPlayer.guild_id == guild_id,
            MatchPlayer.user_id == user_id
        ).join(Match).order_by(Match.created_at.desc()).limit(limit).all()