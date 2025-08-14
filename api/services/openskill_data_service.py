"""
OpenSkill Data Service
Data access layer for OpenSkill parallel rating system
"""

from sqlalchemy.orm import Session
from database.openskill_models import OpenSkillRating, OpenSkillMatchHistory
from services.openskill_service import OpenSkillService
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class OpenSkillDataService:
    """Data access service for OpenSkill ratings"""
    
    @staticmethod
    def get_user_rating(db: Session, guild_id: int, user_id: int) -> Optional[OpenSkillRating]:
        """Get OpenSkill rating for a user"""
        return db.query(OpenSkillRating).filter(
            OpenSkillRating.guild_id == guild_id,
            OpenSkillRating.user_id == user_id
        ).first()
    
    @staticmethod
    def get_or_create_user_rating(db: Session, guild_id: int, user_id: int) -> OpenSkillRating:
        """Get existing rating or create new one with defaults"""
        rating = OpenSkillDataService.get_user_rating(db, guild_id, user_id)
        
        if not rating:
            rating = OpenSkillRating(
                guild_id=guild_id,
                user_id=user_id,
                mu=OpenSkillService.DEFAULT_MU,
                sigma=OpenSkillService.DEFAULT_SIGMA,
                games_played=0
            )
            db.add(rating)
            db.commit()
            db.refresh(rating)
        
        return rating
    
    @staticmethod
    def update_user_rating(db: Session, guild_id: int, user_id: int, 
                          new_mu: float, new_sigma: float) -> OpenSkillRating:
        """Update user's OpenSkill rating"""
        rating = OpenSkillDataService.get_or_create_user_rating(db, guild_id, user_id)
        
        rating.mu = new_mu
        rating.sigma = new_sigma
        rating.games_played += 1
        rating.last_updated = datetime.utcnow()
        
        db.commit()
        db.refresh(rating)
        return rating
    
    @staticmethod
    def get_guild_leaderboard(db: Session, guild_id: int, limit: int = 25) -> List[OpenSkillRating]:
        """Get OpenSkill leaderboard for a guild"""
        return db.query(OpenSkillRating).filter(
            OpenSkillRating.guild_id == guild_id
        ).order_by(
            OpenSkillRating.mu.desc()  # Order by skill estimate
        ).limit(limit).all()
    
    @staticmethod
    def get_user_match_history(db: Session, guild_id: int, user_id: int, 
                              limit: int = 20) -> List[OpenSkillMatchHistory]:
        """Get OpenSkill match history for a user"""
        return db.query(OpenSkillMatchHistory).filter(
            OpenSkillMatchHistory.guild_id == guild_id,
            OpenSkillMatchHistory.user_id == user_id
        ).order_by(
            OpenSkillMatchHistory.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def record_match_history(db: Session, match_id: str, player_data: Dict) -> OpenSkillMatchHistory:
        """Record OpenSkill match history entry"""
        history = OpenSkillMatchHistory(
            match_id=match_id,
            guild_id=player_data['guild_id'],
            user_id=player_data['user_id'],
            team_number=player_data['team_number'],
            team_placement=player_data['team_placement'],
            total_competitors=player_data['total_competitors'],
            guild_teams_count=player_data['guild_teams_count'],
            external_teams_count=player_data['external_teams_count'],
            competition_type=player_data['competition_type'],
            mu_before=player_data['openskill_mu_before'],
            sigma_before=player_data['openskill_sigma_before'],
            mu_after=player_data['openskill_mu_after'],
            sigma_after=player_data['openskill_sigma_after'],
            rating_change=player_data['rating_change'],
            display_rating_before=player_data['display_rating_before'],
            display_rating_after=player_data['display_rating_after']
        )
        
        db.add(history)
        db.commit()
        db.refresh(history)
        return history
    
    @staticmethod
    def get_guild_statistics(db: Session, guild_id: int) -> Dict:
        """Get OpenSkill statistics for a guild"""
        # Total users with OpenSkill ratings
        total_users = db.query(OpenSkillRating).filter(
            OpenSkillRating.guild_id == guild_id
        ).count()
        
        # Active users (played at least one game)
        active_users = db.query(OpenSkillRating).filter(
            OpenSkillRating.guild_id == guild_id,
            OpenSkillRating.games_played > 0
        ).count()
        
        # Total OpenSkill matches
        total_matches = db.query(OpenSkillMatchHistory).filter(
            OpenSkillMatchHistory.guild_id == guild_id
        ).count()
        
        # Average rating
        ratings = db.query(OpenSkillRating.mu).filter(
            OpenSkillRating.guild_id == guild_id,
            OpenSkillRating.games_played > 0
        ).all()
        
        if ratings:
            avg_mu = sum(r[0] for r in ratings) / len(ratings)
            avg_display_rating = avg_mu * 60
        else:
            avg_display_rating = 1500  # Default
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_matches': total_matches,
            'average_rating': avg_display_rating
        }
    
    @staticmethod
    def get_match_players_with_openskill(db: Session, match_id: str) -> Dict[int, List[Dict]]:
        """Get match players with their current OpenSkill ratings"""
        from database.models import MatchPlayer
        
        # Get match players
        players = db.query(MatchPlayer).filter(
            MatchPlayer.match_id == match_id
        ).all()
        
        players_by_team = {}
        
        for player in players:
            if player.team_number not in players_by_team:
                players_by_team[player.team_number] = []
            
            # Get current OpenSkill rating
            openskill_rating = OpenSkillDataService.get_or_create_user_rating(
                db, player.guild_id, player.user_id
            )
            
            player_data = {
                'guild_id': player.guild_id,
                'user_id': player.user_id,
                'team_number': player.team_number,
                'openskill_mu_before': openskill_rating.mu,
                'openskill_sigma_before': openskill_rating.sigma
            }
            
            players_by_team[player.team_number].append(player_data)
        
        return players_by_team
    
    @staticmethod
    def process_match_openskill_results(db: Session, match_id: str, 
                                      team_placements: Dict[int, int]) -> Dict:
        """Process OpenSkill results for a match"""
        try:
            # Get players with current ratings
            players_by_team = OpenSkillDataService.get_match_players_with_openskill(db, match_id)
            
            # Add team placements to player data
            for team_num, players in players_by_team.items():
                for player in players:
                    player['team_placement'] = team_placements[team_num]
            
            # Calculate new OpenSkill ratings
            from services.openskill_service import openskill_service
            updated_players = openskill_service.calculate_match_ratings(
                players_by_team, team_placements
            )
            
            # Update database
            total_updated = 0
            for team_num, players in updated_players.items():
                for player in players:
                    # Update user's current rating
                    OpenSkillDataService.update_user_rating(
                        db, player['guild_id'], player['user_id'],
                        player['openskill_mu_after'], player['openskill_sigma_after']
                    )
                    
                    # Record match history
                    OpenSkillDataService.record_match_history(db, match_id, player)
                    total_updated += 1
            
            return {
                'success': True,
                'players_updated': total_updated,
                'competition_type': updated_players[list(updated_players.keys())[0]][0]['competition_type'],
                'total_competitors': updated_players[list(updated_players.keys())[0]][0]['total_competitors']
            }
            
        except Exception as e:
            logger.error(f"Error processing OpenSkill match results: {e}")
            return {
                'success': False,
                'error': str(e),
                'players_updated': 0
            }

# Global service instance
openskill_data_service = OpenSkillDataService()
