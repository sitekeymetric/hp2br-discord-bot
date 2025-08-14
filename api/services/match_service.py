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
        """Get recent matches for a guild (all statuses)"""
        return db.query(Match).filter(
            Match.guild_id == guild_id
        ).order_by(Match.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_guild_completed_matches(db: Session, guild_id: int, limit: int = 50) -> List[Match]:
        """Get only completed matches for a guild"""
        return db.query(Match).filter(
            Match.guild_id == guild_id,
            Match.status == MatchStatus.COMPLETED
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
    def cleanup_pending_matches_for_players(db: Session, player_ids: List[int], guild_id: int) -> int:
        """
        Clean up pending matches for specific players involved in a new result recording
        This prevents players from having multiple pending matches
        """
        if not player_ids:
            return 0
        
        # Find pending matches that involve any of these players
        pending_matches = db.query(Match).join(MatchPlayer).filter(
            Match.status == MatchStatus.PENDING,
            Match.guild_id == guild_id,
            MatchPlayer.user_id.in_(player_ids)
        ).distinct().all()
        
        cleanup_count = 0
        for match in pending_matches:
            # Cancel the pending match
            match.status = MatchStatus.CANCELLED
            match.result_type = ResultType.CANCELLED
            match.end_time = datetime.utcnow()
            
            # Update all players in this match to cancelled state
            match_players = db.query(MatchPlayer).filter(MatchPlayer.match_id == match.match_id).all()
            for player in match_players:
                player.result = PlayerResult.PENDING  # Keep as pending since never completed
            
            cleanup_count += 1
        
        if cleanup_count > 0:
            db.commit()
        
        return cleanup_count
    
    @staticmethod
    def update_match_result(db: Session, match_id: UUID, result_data: MatchResultUpdate) -> Optional[Match]:
        """Update match result and player outcomes"""
        match = MatchService.get_match(db, match_id)
        if not match:
            return None
        
        # Get players involved in this match for cleanup
        players = MatchService.get_match_players(db, match_id)
        player_ids = [p.user_id for p in players]
        
        # Clean up any other pending matches for these players
        cleanup_count = MatchService.cleanup_pending_matches_for_players(db, player_ids, match.guild_id)
        
        # Update match status
        match.status = MatchStatus.COMPLETED
        match.result_type = ResultType(result_data.result_type)
        match.winning_team = result_data.winning_team
        match.end_time = datetime.utcnow()
        
        # Update player results
        for player in players:
            if result_data.result_type == "win_loss":
                if player.team_number == result_data.winning_team:
                    player.result = PlayerResult.WIN
                else:
                    player.result = PlayerResult.LOSS
            elif result_data.result_type == "draw":
                player.result = PlayerResult.DRAW
            elif result_data.result_type == "forfeit":
                # All players lose in a forfeit (no winner)
                player.result = PlayerResult.LOSS
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
        """Get match history for a specific user (all statuses)"""
        return db.query(MatchPlayer).filter(
            MatchPlayer.guild_id == guild_id,
            MatchPlayer.user_id == user_id
        ).join(Match).order_by(Match.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_user_completed_match_history(db: Session, guild_id: int, user_id: int, limit: int = 20):
        """Get only completed match history for a specific user with match date and teammate information"""
        # Query both MatchPlayer and Match data
        results = db.query(MatchPlayer, Match).filter(
            MatchPlayer.guild_id == guild_id,
            MatchPlayer.user_id == user_id
        ).join(Match, MatchPlayer.match_id == Match.match_id).filter(
            Match.status == MatchStatus.COMPLETED
        ).order_by(Match.end_time.desc()).limit(limit).all()
        
        # Convert to list of dictionaries with both player and match data
        history = []
        for match_player, match in results:
            # Get teammates for this match (same team, different user)
            teammates = db.query(MatchPlayer).join(User).filter(
                MatchPlayer.match_id == match.match_id,
                MatchPlayer.team_number == match_player.team_number,
                MatchPlayer.user_id != user_id,
                MatchPlayer.guild_id == guild_id
            ).all()
            
            # Get teammate usernames
            teammate_info = []
            for teammate in teammates:
                teammate_user = db.query(User).filter(
                    User.guild_id == guild_id,
                    User.user_id == teammate.user_id
                ).first()
                if teammate_user:
                    teammate_info.append({
                        'user_id': teammate.user_id,
                        'username': teammate_user.username
                    })
            
            history.append({
                'user_id': match_player.user_id,
                'guild_id': match_player.guild_id,
                'team_number': match_player.team_number if match_player.team_number is not None else 1,
                'team_placement': match_player.team_placement,  # Add team placement for placement-based results
                'rating_mu_before': match_player.rating_mu_before,
                'rating_sigma_before': match_player.rating_sigma_before,
                'rating_mu_after': match_player.rating_mu_after,
                'rating_sigma_after': match_player.rating_sigma_after,
                'result': match_player.result.value if match_player.result else 'unknown',
                'match_id': str(match.match_id),  # Convert UUID to string for JSON serialization
                'start_time': match.start_time.isoformat() if match.start_time else None,
                'end_time': match.end_time.isoformat() if match.end_time else None,
                'status': match.status.value if match.status else 'unknown',
                'result_type': match.result_type.value if match.result_type else None,
                'total_teams': match.total_teams,  # Add total teams in match
                'teammates': teammate_info  # Include teammate information
            })
        
        return history