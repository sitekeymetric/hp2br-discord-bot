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
        """Get all users in a guild"""
        result = await self._make_request("GET", f"/users/{guild_id}")
        return result if result is not None else []
    
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
        """Get guild's match history"""
        params = {"limit": limit}
        result = await self._make_request("GET", f"/matches/{guild_id}", params=params)
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
        """Get match history for a specific user"""
        params = {"limit": limit}
        result = await self._make_request("GET", f"/matches/user/{guild_id}/{user_id}/history", params=params)
        return result if result is not None else []
    
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
    
    async def close(self):
        """Close the HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()

# Global API client instance
api_client = APIClient()