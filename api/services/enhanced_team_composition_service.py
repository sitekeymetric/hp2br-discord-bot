"""
Enhanced Team Composition Analysis Service
Analyzes team compositions based on performance metrics, not just wins
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from database.models import Match, MatchPlayer, User
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class EnhancedTeamCompositionService:
    """Service for analyzing team composition performance beyond just wins"""
    
    @staticmethod
    def get_performance_based_partnerships(db: Session, guild_id: int, limit: int = 10) -> List[Dict]:
        """Get best performing 2-player partnerships based on multiple metrics"""
        try:
            query = text("""
            WITH team_performance AS (
                SELECT 
                    m.match_id,
                    mp.team_number,
                    COUNT(mp.user_id) as team_size,
                    AVG(mp.team_placement) as avg_placement,
                    AVG(mp.rating_mu_after - mp.rating_mu_before) as avg_rating_change,
                    SUM(mp.rating_mu_after - mp.rating_mu_before) as total_rating_change,
                    GROUP_CONCAT(u.username, ' + ') as team_members,
                    GROUP_CONCAT(u.user_id, ',') as user_ids,
                    -- Performance score: better placement (lower number) + positive rating change
                    (8 - AVG(mp.team_placement)) + (AVG(mp.rating_mu_after - mp.rating_mu_before) * 0.2) as performance_score
                FROM matches m
                JOIN match_players mp ON m.match_id = mp.match_id
                JOIN users u ON mp.guild_id = u.guild_id AND mp.user_id = u.user_id
                WHERE m.guild_id = :guild_id 
                    AND m.status = 'COMPLETED'
                    AND mp.rating_mu_after IS NOT NULL
                GROUP BY m.match_id, mp.team_number
                HAVING team_size = 2
            ),
            partnership_stats AS (
                SELECT 
                    team_members,
                    user_ids,
                    COUNT(*) as matches_played,
                    AVG(avg_placement) as avg_placement,
                    AVG(avg_rating_change) as avg_rating_change,
                    AVG(performance_score) as avg_performance_score,
                    SUM(CASE WHEN avg_placement <= 3 THEN 1 ELSE 0 END) as top3_finishes,
                    SUM(CASE WHEN avg_rating_change > 0 THEN 1 ELSE 0 END) as positive_rating_matches
                FROM team_performance
                GROUP BY team_members, user_ids
            )
            SELECT 
                team_members as partnership,
                user_ids,
                matches_played,
                ROUND(avg_placement, 1) as avg_placement,
                ROUND(avg_rating_change, 1) as avg_rating_change,
                ROUND(avg_performance_score, 2) as performance_score,
                top3_finishes,
                positive_rating_matches
            FROM partnership_stats
            ORDER BY avg_performance_score DESC, matches_played DESC
            LIMIT :limit
            """)
            
            result = db.execute(query, {"guild_id": guild_id, "limit": limit}).fetchall()
            
            partnerships = []
            for row in result:
                partnerships.append({
                    'partnership': row[0],
                    'user_ids': row[1],
                    'matches_played': row[2],
                    'avg_placement': row[3],
                    'avg_rating_change': row[4],
                    'performance_score': row[5],
                    'top3_finishes': row[6],
                    'positive_rating_matches': row[7]
                })
            
            return partnerships
            
        except Exception as e:
            logger.error(f"Error getting performance-based partnerships: {e}")
            return []
    
    @staticmethod
    def get_performance_based_trios(db: Session, guild_id: int, limit: int = 10) -> List[Dict]:
        """Get best performing 3-player team compositions"""
        try:
            query = text("""
            WITH team_performance AS (
                SELECT 
                    m.match_id,
                    mp.team_number,
                    COUNT(mp.user_id) as team_size,
                    AVG(mp.team_placement) as avg_placement,
                    AVG(mp.rating_mu_after - mp.rating_mu_before) as avg_rating_change,
                    GROUP_CONCAT(u.username, ', ') as team_members,
                    GROUP_CONCAT(u.user_id, ',') as user_ids,
                    (8 - AVG(mp.team_placement)) + (AVG(mp.rating_mu_after - mp.rating_mu_before) * 0.2) as performance_score
                FROM matches m
                JOIN match_players mp ON m.match_id = mp.match_id
                JOIN users u ON mp.guild_id = u.guild_id AND mp.user_id = u.user_id
                WHERE m.guild_id = :guild_id 
                    AND m.status = 'COMPLETED'
                    AND mp.rating_mu_after IS NOT NULL
                GROUP BY m.match_id, mp.team_number
                HAVING team_size = 3
            ),
            trio_stats AS (
                SELECT 
                    team_members,
                    user_ids,
                    COUNT(*) as matches_played,
                    AVG(avg_placement) as avg_placement,
                    AVG(avg_rating_change) as avg_rating_change,
                    AVG(performance_score) as avg_performance_score,
                    SUM(CASE WHEN avg_placement <= 3 THEN 1 ELSE 0 END) as top3_finishes
                FROM team_performance
                GROUP BY team_members, user_ids
            )
            SELECT 
                team_members as composition,
                user_ids,
                matches_played,
                ROUND(avg_placement, 1) as avg_placement,
                ROUND(avg_rating_change, 1) as avg_rating_change,
                ROUND(avg_performance_score, 2) as performance_score,
                top3_finishes
            FROM trio_stats
            ORDER BY avg_performance_score DESC, matches_played DESC
            LIMIT :limit
            """)
            
            result = db.execute(query, {"guild_id": guild_id, "limit": limit}).fetchall()
            
            trios = []
            for row in result:
                trios.append({
                    'composition': row[0],
                    'user_ids': row[1],
                    'matches_played': row[2],
                    'avg_placement': row[3],
                    'avg_rating_change': row[4],
                    'performance_score': row[5],
                    'top3_finishes': row[6]
                })
            
            return trios
            
        except Exception as e:
            logger.error(f"Error getting performance-based trios: {e}")
            return []
    
    @staticmethod
    def get_performance_based_squads(db: Session, guild_id: int, limit: int = 10) -> List[Dict]:
        """Get best performing 4-player team compositions"""
        try:
            query = text("""
            WITH team_performance AS (
                SELECT 
                    m.match_id,
                    mp.team_number,
                    COUNT(mp.user_id) as team_size,
                    AVG(mp.team_placement) as avg_placement,
                    AVG(mp.rating_mu_after - mp.rating_mu_before) as avg_rating_change,
                    GROUP_CONCAT(u.username, ', ') as team_members,
                    GROUP_CONCAT(u.user_id, ',') as user_ids,
                    (8 - AVG(mp.team_placement)) + (AVG(mp.rating_mu_after - mp.rating_mu_before) * 0.2) as performance_score
                FROM matches m
                JOIN match_players mp ON m.match_id = mp.match_id
                JOIN users u ON mp.guild_id = u.guild_id AND mp.user_id = u.user_id
                WHERE m.guild_id = :guild_id 
                    AND m.status = 'COMPLETED'
                    AND mp.rating_mu_after IS NOT NULL
                GROUP BY m.match_id, mp.team_number
                HAVING team_size = 4
            ),
            squad_stats AS (
                SELECT 
                    team_members,
                    user_ids,
                    COUNT(*) as matches_played,
                    AVG(avg_placement) as avg_placement,
                    AVG(avg_rating_change) as avg_rating_change,
                    AVG(performance_score) as avg_performance_score,
                    SUM(CASE WHEN avg_placement <= 3 THEN 1 ELSE 0 END) as top3_finishes
                FROM team_performance
                GROUP BY team_members, user_ids
            )
            SELECT 
                team_members as composition,
                user_ids,
                matches_played,
                ROUND(avg_placement, 1) as avg_placement,
                ROUND(avg_rating_change, 1) as avg_rating_change,
                ROUND(avg_performance_score, 2) as performance_score,
                top3_finishes
            FROM squad_stats
            ORDER BY avg_performance_score DESC, matches_played DESC
            LIMIT :limit
            """)
            
            result = db.execute(query, {"guild_id": guild_id, "limit": limit}).fetchall()
            
            squads = []
            for row in result:
                squads.append({
                    'composition': row[0],
                    'user_ids': row[1],
                    'matches_played': row[2],
                    'avg_placement': row[3],
                    'avg_rating_change': row[4],
                    'performance_score': row[5],
                    'top3_finishes': row[6]
                })
            
            return squads
            
        except Exception as e:
            logger.error(f"Error getting performance-based squads: {e}")
            return []
    
    @staticmethod
    def get_enhanced_team_composition_stats(db: Session, guild_id: int) -> Dict:
        """Get comprehensive performance-based team composition statistics"""
        try:
            partnerships = EnhancedTeamCompositionService.get_performance_based_partnerships(db, guild_id, 10)
            trios = EnhancedTeamCompositionService.get_performance_based_trios(db, guild_id, 10)
            squads = EnhancedTeamCompositionService.get_performance_based_squads(db, guild_id, 10)
            
            # Get total completed matches for context
            total_matches = db.query(Match).filter(
                Match.guild_id == guild_id,
                Match.status == 'COMPLETED'
            ).count()
            
            return {
                'total_matches': total_matches,
                'analysis_type': 'performance_based',
                'top_partnerships': partnerships,
                'top_trios': trios,
                'top_squads': squads
            }
            
        except Exception as e:
            logger.error(f"Error getting enhanced team composition stats: {e}")
            return {
                'total_matches': 0,
                'analysis_type': 'performance_based',
                'top_partnerships': [],
                'top_trios': [],
                'top_squads': []
            }
