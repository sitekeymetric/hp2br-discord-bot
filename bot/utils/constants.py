import os

class Config:
    # Environment Variables
    DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
    
    # Optional Configuration
    DEBUG_MODE = os.environ.get("DEBUG", "False").lower() == "true"
    DEFAULT_TEAMS = int(os.environ.get("DEFAULT_TEAMS", "3"))
    MIN_PLAYERS = int(os.environ.get("MIN_PLAYERS", "1"))
    MAX_PLAYERS = int(os.environ.get("MAX_PLAYERS", "24"))
    # PROPOSAL_TIMEOUT no longer used - team proposal UI has no timeout
    
    # Voice Channel Names
    WAITING_ROOM_NAME = os.environ.get("WAITING_ROOM_NAME", "Waiting Room")
    TEAM_CHANNEL_PREFIX = os.environ.get("TEAM_CHANNEL_PREFIX", "Team")
    
    # Rating System
    DEFAULT_RATING_MU = 1500.0
    DEFAULT_RATING_SIGMA = 350.0
    
    # Team Balancing
    MIN_PLAYERS_FOR_TEAMS = 1  # Changed to allow special cases
    MAX_PLAYERS_PER_MATCH = 24
    DEFAULT_NUM_TEAMS = 3
    
    # Special case thresholds
    SINGLE_TEAM_THRESHOLD = 4  # 1-4 players = single team
    TWO_TEAM_THRESHOLD = 5     # 5 players = 2 teams (2:3 split)
    
    # Region codes for validation
    VALID_REGIONS = ["CA", "TX", "NY", "KR", "NA", "EU"]
    
    # UI Settings
    EMBED_COLOR = 0x2B5CE6  # Discord blue
    ERROR_COLOR = 0xFF0000  # Red
    SUCCESS_COLOR = 0x00FF00  # Green
    WARNING_COLOR = 0xFFFF00  # Yellow
    
    # Timeouts
    # TEAM_PROPOSAL_TIMEOUT removed - team proposal UI has no timeout
    MATCH_CLEANUP_DELAY = 30     # 30 seconds

# Region codes for validation
VALID_REGIONS = ["CA", "TX", "NY", "KR", "NA", "EU"]

# Team emojis for display
TEAM_EMOJIS = ["🔴", "🔵", "🟢", "🟡", "🟠", "🟣"]