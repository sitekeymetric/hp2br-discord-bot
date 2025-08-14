"""
Team Composition Analysis Service
Analyzes winning team compositions and partnerships
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from database.models import Match, MatchPlayer, User
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class TeamCompositionService:
    """Service for analyzing team composition statistics"""
    
    @staticmethod
    def get_top_partnerships(db: Session, guild_id: int, limit: int = 5) -> List[Dict]:
        """Get most successful 2-player partnerships"""
        try:
            # Query for partnerships in winning teams
            query = text("""
            WITH winning_teams AS (
                SELECT 
                    m.match_id,
                    mp.team_number,
                    u.username,
                    u.user_id
                FROM matches m
                JOIN match_players mp ON m.match_id = mp.match_id
                JOIN users u ON mp.guild_id = u.guild_id AND mp.user_id = u.user_id
                WHERE m.guild_id = :guild_id 
                    AND m.status = 'COMPLETED' 
                    AND mp.team_number = m.winning_team
            ),
            partnerships AS (
                SELECT 
                    wt1.match_id,
                    CASE 
                        WHEN wt1.username < wt2.username THEN wt1.username || ' + ' || wt2.username
                        ELSE wt2.username || ' + ' || wt1.username
                    END as partnership,
                    CASE 
                        WHEN wt1.username < wt2.username THEN wt1.user_id || ',' || wt2.user_id
                        ELSE wt2.user_id || ',' || wt1.user_id
                    END as user_ids
                FROM winning_teams wt1
                JOIN winning_teams wt2 ON wt1.match_id = wt2.match_id 
                    AND wt1.team_number = wt2.team_number
                    AND wt1.username < wt2.username
            )
            SELECT 
                partnership,
                user_ids,
                COUNT(*) as wins_together
            FROM partnerships
            GROUP BY partnership, user_ids
            ORDER BY wins_together DESC
            LIMIT :limit
            """)
            
            result = db.execute(query, {"guild_id": guild_id, "limit": limit}).fetchall()
            
            partnerships = []
            for row in result:
                partnerships.append({
                    'partnership': row[0],
                    'user_ids': row[1],
                    'wins': row[2]
                })
            
            return partnerships
            
        except Exception as e:
            logger.error(f"Error getting top partnerships: {e}")
            return []
    
    @staticmethod
    def get_top_trio_compositions(db: Session, guild_id: int, limit: int = 5) -> List[Dict]:
        """Get most successful 3-player team compositions"""
        try:
            # Query for 3-player winning teams
            query = text("""
            WITH winning_teams AS (
                SELECT 
                    m.match_id,
                    mp.team_number,
                    COUNT(mp.user_id) as team_size,
                    GROUP_CONCAT(u.username, ', ') as team_members,
                    GROUP_CONCAT(u.user_id, ',') as user_ids
                FROM matches m
                JOIN match_players mp ON m.match_id = mp.match_id
                JOIN users u ON mp.guild_id = u.guild_id AND mp.user_id = u.user_id
                WHERE m.guild_id = :guild_id 
                    AND m.status = 'COMPLETED' 
                    AND mp.team_number = m.winning_team
                GROUP BY m.match_id, mp.team_number
                HAVING team_size = 3
            )
            SELECT 
                team_members,
                user_ids,
                COUNT(*) as wins
            FROM winning_teams 
            GROUP BY team_members, user_ids
            ORDER BY wins DESC
            LIMIT :limit
            """)
            
            result = db.execute(query, {"guild_id": guild_id, "limit": limit}).fetchall()
            
            trios = []
            for row in result:
                trios.append({
                    'composition': row[0],
                    'user_ids': row[1],
                    'wins': row[2]
                })
            
            return trios
            
        except Exception as e:
            logger.error(f"Error getting top trio compositions: {e}")
            return []
    
    @staticmethod
    def get_top_squad_compositions(db: Session, guild_id: int, limit: int = 5) -> List[Dict]:
        """Get most successful 4-player team compositions"""
        try:
            # Query for 4-player winning teams
            query = text("""
            WITH winning_teams AS (
                SELECT 
                    m.match_id,
                    mp.team_number,
                    COUNT(mp.user_id) as team_size,
                    GROUP_CONCAT(u.username, ', ') as team_members,
                    GROUP_CONCAT(u.user_id, ',') as user_ids
                FROM matches m
                JOIN match_players mp ON m.match_id = mp.match_id
                JOIN users u ON mp.guild_id = u.guild_id AND mp.user_id = u.user_id
                WHERE m.guild_id = :guild_id 
                    AND m.status = 'COMPLETED' 
                    AND mp.team_number = m.winning_team
                GROUP BY m.match_id, mp.team_number
                HAVING team_size = 4
            )
            SELECT 
                team_members,
                user_ids,
                COUNT(*) as wins
            FROM winning_teams 
            GROUP BY team_members, user_ids
            ORDER BY wins DESC
            LIMIT :limit
            """)
            
            result = db.execute(query, {"guild_id": guild_id, "limit": limit}).fetchall()
            
            squads = []
            for row in result:
                squads.append({
                    'composition': row[0],
                    'user_ids': row[1],
                    'wins': row[2]
                })
            
            return squads
            
        except Exception as e:
            logger.error(f"Error getting top squad compositions: {e}")
            return []
    
    @staticmethod
    def get_team_composition_stats(db: Session, guild_id: int) -> Dict:
        """Get comprehensive team composition statistics"""
        try:
            partnerships = TeamCompositionService.get_top_partnerships(db, guild_id, 5)
            trios = TeamCompositionService.get_top_trio_compositions(db, guild_id, 5)
            squads = TeamCompositionService.get_top_squad_compositions(db, guild_id, 5)
            
            # Get total completed matches for context
            total_matches = db.query(Match).filter(
                Match.guild_id == guild_id,
                Match.status == 'COMPLETED'
            ).count()
            
            return {
                'total_matches': total_matches,
                'top_partnerships': partnerships,
                'top_trios': trios,
                'top_squads': squads
            }
            
        except Exception as e:
            logger.error(f"Error getting team composition stats: {e}")
            return {
                'total_matches': 0,
                'top_partnerships': [],
                'top_trios': [],
                'top_squads': []
            }
