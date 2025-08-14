import aiohttp
import asyncio
import logging
from typing import Optional, List, Dict, Any
from utils.constants import Config

logger = logging.getLogger(__name__)

class APIClient:
    """HTTP client for communicating with the database API"""
    
    def __init__(self):
        self.base_url = Config.API_BASE_URL.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
        self.timeout = aiohttp.ClientTimeout(total=30)
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _ensure_session(self):
        """Ensure session is created"""
        if not self.session or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict[Any, Any]]:
        """Make HTTP request to API"""
        await self._ensure_session()
        
        url = f"{self.base_url}{endpoint}"
        logger.debug(f"Making {method} request to {url}")
        
        try:
            async with self.session.request(method, url, **kwargs) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 201:
                    return await response.json()
                elif response.status == 404:
                    logger.warning(f"Resource not found: {url}")
                    return None
                else:
                    error_text = await response.text()
                    logger.error(f"API request failed: {response.status} - {error_text}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {url}")
            return None
        except aiohttp.ClientError as e:
            logger.error(f"Client error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {e}")
            return None
    
    # User Operations
    async def create_user(self, guild_id: int, user_id: int, username: str, region: str = None) -> Optional[Dict]:
        """Create a new user in the database"""
        data = {
            "guild_id": guild_id,
            "user_id": user_id,
            "username": username
        }
        if region:
            data["region_code"] = region
            
        return await self._make_request("POST", "/users/", json=data)
    
    async def get_user(self, guild_id: int, user_id: int) -> Optional[Dict]:
        """Get user stats from database"""
        return await self._make_request("GET", f"/users/{guild_id}/{user_id}")
    
    async def update_user(self, guild_id: int, user_id: int, **kwargs) -> Optional[Dict]:
        """Update user information"""
        # Filter out None values
        data = {k: v for k, v in kwargs.items() if v is not None}
        if not data:
            return None
            
        return await self._make_request("PUT", f"/users/{guild_id}/{user_id}", json=data)
    
    async def get_guild_users(self, guild_id: int) -> List[Dict]:
        """Get all users in a guild (legacy method)"""
        result = await self._make_request("GET", f"/users/{guild_id}")
        return result if result is not None else []
    
    async def get_guild_users_completed_stats(self, guild_id: int) -> List[Dict]:
        """Get all users in a guild with statistics based only on COMPLETED matches"""
        result = await self._make_request("GET", f"/users/{guild_id}/completed-stats")
        return result if result is not None else []
    
    async def get_user_completed_stats(self, guild_id: int, user_id: int) -> Optional[Dict]:
        """Get user with statistics based only on COMPLETED matches"""
        return await self._make_request("GET", f"/users/{guild_id}/{user_id}/completed-stats")
    
    async def update_user_rating(self, guild_id: int, user_id: int, new_mu: float, new_sigma: float) -> Optional[Dict]:
        """Update user's rating (internal use)"""
        params = {"new_mu": new_mu, "new_sigma": new_sigma}
        return await self._make_request("PUT", f"/users/{guild_id}/{user_id}/rating", params=params)
    
    async def delete_user(self, guild_id: int, user_id: int) -> bool:
        """Delete a user from the database"""
        result = await self._make_request("DELETE", f"/users/{guild_id}/{user_id}")
        return result is not None
    
    # Match Operations
    async def create_match(self, guild_id: int, created_by: int, total_teams: int) -> Optional[Dict]:
        """Create a new match"""
        data = {
            "guild_id": guild_id,
            "created_by": created_by,
            "total_teams": total_teams
        }
        return await self._make_request("POST", "/matches/", json=data)
    
    async def add_player_to_match(self, match_id: str, user_id: int, guild_id: int, team_number: int) -> Optional[Dict]:
        """Add a player to a match"""
        data = {
            "user_id": user_id,
            "guild_id": guild_id,
            "team_number": team_number
        }
        return await self._make_request("POST", f"/matches/{match_id}/players", json=data)
    
    async def get_match(self, match_id: str) -> Optional[Dict]:
        """Get specific match details"""
        return await self._make_request("GET", f"/matches/match/{match_id}")
    
    async def get_guild_matches(self, guild_id: int, limit: int = 50) -> List[Dict]:
        """Get guild's match history (all statuses)"""
        params = {"limit": limit}
        result = await self._make_request("GET", f"/matches/{guild_id}", params=params)
        return result if result is not None else []
    
    async def get_guild_completed_matches(self, guild_id: int, limit: int = 50) -> List[Dict]:
        """Get only completed matches for a guild (for statistics and ratings)"""
        params = {"limit": limit}
        result = await self._make_request("GET", f"/matches/{guild_id}/completed", params=params)
        return result if result is not None else []
    
    async def record_match_result(self, match_id: str, result_type: str, winning_team: int = None) -> Optional[Dict]:
        """Record match result and update ratings"""
        data = {"result_type": result_type}
        if winning_team is not None:
            data["winning_team"] = winning_team
            
        return await self._make_request("PUT", f"/matches/{match_id}/result", json=data)
    
    async def cancel_match(self, match_id: str) -> Optional[Dict]:
        """Cancel a match"""
        return await self._make_request("DELETE", f"/matches/{match_id}")
    
    async def get_user_match_history(self, guild_id: int, user_id: int, limit: int = 20) -> List[Dict]:
        """Get match history for a specific user (all statuses)"""
        params = {"limit": limit}
        result = await self._make_request("GET", f"/matches/user/{guild_id}/{user_id}/history", params=params)
        return result if result is not None else []
    
    async def get_user_completed_match_history(self, guild_id: int, user_id: int, limit: int = 20) -> List[Dict]:
        """Get only completed match history for a specific user (for statistics and ratings)"""
        params = {"limit": limit}
        result = await self._make_request("GET", f"/matches/user/{guild_id}/{user_id}/completed", params=params)
        return result if result is not None else []
    
    async def get_user_teammate_stats(self, guild_id: int, user_id: int, limit: int = 10) -> List[Dict]:
        """Get teammate statistics for a user - most frequent teammates and win rates"""
        params = {"limit": limit}
        result = await self._make_request("GET", f"/users/{guild_id}/{user_id}/teammates", params=params)
        return result if result is not None else []
    
    # OpenSkill Rating System Methods
    async def get_openskill_rating(self, guild_id: int, user_id: int) -> Optional[Dict]:
        """Get OpenSkill rating for a user"""
        return await self._make_request("GET", f"/openskill/ratings/{guild_id}/{user_id}")
    
    async def get_openskill_leaderboard(self, guild_id: int, limit: int = 25) -> List[Dict]:
        """Get OpenSkill leaderboard for a guild"""
        params = {"limit": limit}
        result = await self._make_request("GET", f"/openskill/ratings/{guild_id}", params=params)
        return result if result is not None else []
    
    async def get_openskill_history(self, guild_id: int, user_id: int, limit: int = 20) -> List[Dict]:
        """Get OpenSkill match history for a user"""
        params = {"limit": limit}
        result = await self._make_request("GET", f"/openskill/history/{guild_id}/{user_id}", params=params)
        return result if result is not None else []
    
    async def get_openskill_stats(self, guild_id: int) -> Optional[Dict]:
        """Get OpenSkill statistics for a guild"""
        return await self._make_request("GET", f"/openskill/stats/{guild_id}")
    
    async def compare_rating_systems(self, guild_id: int) -> Optional[Dict]:
        """Compare OpenSkill and Placement rating systems for a guild"""
        return await self._make_request("GET", f"/openskill/compare/{guild_id}")
    
    # Team Composition Analysis Methods
    async def get_team_composition_stats(self, guild_id: int) -> Optional[Dict]:
        """Get team composition statistics (win-based)"""
        return await self._make_request("GET", f"/team-compositions/stats/{guild_id}")
    
    async def get_enhanced_team_composition_stats(self, guild_id: int) -> Optional[Dict]:
        """Get enhanced team composition statistics (performance-based)"""
        return await self._make_request("GET", f"/team-compositions/performance/stats/{guild_id}")
    
    async def process_openskill_match(self, match_id: str, team_placements: Dict[str, int]) -> Optional[Dict]:
        """Process OpenSkill ratings for a completed match"""
        return await self._make_request("POST", f"/openskill/process-match/{match_id}", json=team_placements)
    
    async def initialize_guild_openskill(self, guild_id: int) -> Optional[Dict]:
        """Initialize OpenSkill ratings for all users in a guild"""
        return await self._make_request("POST", f"/openskill/initialize/{guild_id}")
    
    # Utility Methods
    async def health_check(self) -> bool:
        """Check if API is accessible"""
        result = await self._make_request("GET", "/health")
        return result is not None and result.get("status") == "healthy"
    
    async def auto_register_user(self, guild_id: int, user_id: int, username: str, region: str = None) -> Optional[Dict]:
        """Auto-register user if they don't exist"""
        # First try to get existing user
        user = await self.get_user(guild_id, user_id)
        if user:
            return user
        
        # User doesn't exist, create them
        logger.info(f"Auto-registering user {username} ({user_id}) in guild {guild_id}")
        return await self.create_user(guild_id, user_id, username, region)
    
    async def record_placement_result(self, match_id: str, team_placements: Dict[int, int]) -> Dict:
        """Record placement-based match result (legacy v2.0 system)"""
        # Wrap team_placements in the expected format for PlacementResultUpdate model
        data = {
            "team_placements": team_placements
        }
        result = await self._make_request("PUT", f"/matches/{match_id}/placement-result", json=data)
        return result if result is not None else {}
    
    async def record_advanced_placement_result(self, match_id: str, team_placements: Dict[int, Dict]) -> Dict:
        """Record match result using advanced rating system v3.0"""
        data = {
            "team_placements": team_placements
        }
        result = await self._make_request("PUT", f"/advanced-matches/{match_id}/placement-result", json=data)
        return result if result is not None else {}
    
    async def preview_rating_changes(self, player_rating: float, team_avg_rating: float, opponent_teams: List[Dict]) -> Dict:
        """Preview rating changes for different placements"""
        data = {
            "player_rating": player_rating,
            "team_avg_rating": team_avg_rating,
            "opponent_teams": opponent_teams
        }
        result = await self._make_request("POST", "/advanced-matches/rating-preview", json=data)
        return result if result is not None else {}
    
    async def get_advanced_rating_scale(self) -> Dict:
        """Get advanced rating scale information"""
        result = await self._make_request("GET", "/advanced-matches/rating-scale")
        return result if result is not None else {}
    
    # Team Management Operations
    async def remove_player_from_match(self, match_id: str, user_id: int, guild_id: int) -> bool:
        """Remove a player from a match"""
        params = {"guild_id": guild_id}
        result = await self._make_request("DELETE", f"/matches/{match_id}/players/{user_id}", params=params)
        return result is not None
    
    async def update_player_team_assignment(self, match_id: str, user_id: int, guild_id: int, new_team_number: int) -> bool:
        """Update a player's team assignment in a match"""
        params = {"new_team_number": new_team_number, "guild_id": guild_id}
        result = await self._make_request("PUT", f"/matches/{match_id}/players/{user_id}/team", params=params)
        return result is not None
    
    async def get_match_teams(self, match_id: str) -> Dict:
        """Get all teams in a match organized by team number"""
        result = await self._make_request("GET", f"/matches/{match_id}/teams")
        return result if result is not None else {}
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

# Global API client instance
api_client = APIClient()