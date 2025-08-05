# Discord Team Balance Bot

A Discord bot that creates balanced teams for competitive gameplay using skill ratings and database persistence.

## Features

### 🎮 Core Functionality
- **Automatic Team Balancing**: Creates fair teams using Glicko-2 rating system
- **Voice Channel Management**: Automatically moves players to team channels
- **Rating Tracking**: Persistent skill ratings that improve over time
- **Multi-Guild Support**: Works across multiple Discord servers

### 👤 User Commands
- `/register [region]` - Register in the team balance system
- `/stats [@user]` - View player statistics and ratings
- `/set_region <region>` - Update your region (NA, EU, AS, OCE, etc.)
- `/leaderboard [limit]` - Show top players in the guild
- `/match_history [@user] [limit]` - View recent match history

### 🎯 Team Commands
- `/create_teams [num_teams]` - Create balanced teams from waiting room
- `/record_result <winning_team>` - Record match result and update ratings
- `/cancel_match` - Cancel current match

### ⚙️ Admin Commands (Administrator Permission Required)
- `/setup` - Initial bot setup for the guild
- `/reset_user <@user>` - Reset user's rating and stats
- `/guild_stats` - Show guild-wide statistics
- `/cleanup` - Clean up abandoned team channels

## Setup Instructions

### Prerequisites
1. **Database API**: Ensure the FastAPI database server is running
2. **Discord Bot Token**: Create a bot application on Discord Developer Portal
3. **Python 3.8+**: Required for Discord.py

### Installation

1. **Clone and Navigate**:
   ```bash
   cd bot/
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your bot token and API URL
   ```

4. **Set Required Environment Variables**:
   ```bash
   export DISCORD_TOKEN="your_bot_token_here"
   export API_BASE_URL="http://localhost:8000"  # Your database API URL
   ```

5. **Run the Bot**:
   ```bash
   python main.py
   ```

### Discord Bot Permissions

The bot requires the following permissions:
- **Send Messages**: To respond to commands
- **Use Slash Commands**: To register and handle slash commands
- **Manage Channels**: To create and delete team voice channels
- **Move Members**: To move players between voice channels
- **Embed Links**: To display rich embeds
- **Read Message History**: For command functionality

### Initial Guild Setup

1. **Invite Bot**: Use Discord's OAuth2 URL generator with required permissions
2. **Run Setup**: Use `/setup` command to create necessary voice channels
3. **Test**: Have players use `/register` and try `/create_teams`

## Usage Flow

### For Players
1. **Join**: Use `/register` to join the team balance system
2. **Wait**: Join the "🎯 Waiting Room" voice channel
3. **Play**: Admin uses `/create_teams` to create balanced teams
4. **Accept**: Vote to accept or decline the team proposal
5. **Compete**: Players are moved to team voice channels automatically
6. **Record**: Admin uses `/record_result` to update ratings

### For Administrators
1. **Setup**: Run `/setup` to configure the bot for your guild
2. **Monitor**: Use `/guild_stats` to view server statistics
3. **Manage**: Use admin commands to reset users or clean up channels
4. **Moderate**: Record match results and manage team balance sessions

## Configuration Options

### Environment Variables
```bash
# Required
DISCORD_TOKEN=your_bot_token_here
API_BASE_URL=http://localhost:8000

# Optional
DEBUG=false                    # Enable debug logging
DEFAULT_TEAMS=3               # Default number of teams
MIN_PLAYERS=6                 # Minimum players for team creation
MAX_PLAYERS=15                # Maximum players per match
PROPOSAL_TIMEOUT=300          # Team proposal timeout (seconds)
WAITING_ROOM_NAME=🎯 Waiting Room  # Waiting room channel name
TEAM_CHANNEL_PREFIX=Team      # Prefix for team channels
```

### Supported Regions
- **NA**: North America
- **EU**: Europe
- **AS**: Asia
- **OCE**: Oceania
- **SA**: South America
- **AF**: Africa
- **ME**: Middle East

## Architecture

### Components
- **Main Bot** (`main.py`): Discord connection and command registration
- **Commands**: User, team, and admin command handlers
- **Services**: API client, voice manager, team balancer
- **Utils**: Embed templates, UI components, constants

### Database Integration
- **API Client**: HTTP client for database communication
- **Auto-Registration**: Automatically registers new players
- **Rating System**: Simplified Glicko-2 implementation
- **Match Tracking**: Complete match history and statistics

## Team Balancing Algorithm

### Snake Draft Method
1. **Sort Players**: By rating (skill estimate μ - uncertainty σ/2)
2. **Distribute**: Using snake pattern (1→2→3→3→2→1)
3. **Validate**: Ensure fair distribution and team balance
4. **Score**: Calculate balance score (lower = better balance)

### Rating System
- **Initial Rating**: 1500μ ± 350σ
- **Updates**: Based on match results (win/loss/draw)
- **Uncertainty**: Decreases with more games played
- **Team Rating**: Average of individual player ratings

## Troubleshooting

### Common Issues

1. **Bot Not Responding**:
   - Check bot token is correct
   - Verify bot has required permissions
   - Ensure API server is running

2. **Voice Channel Issues**:
   - Run `/setup` to create waiting room
   - Check bot has "Move Members" permission
   - Verify channel names match configuration

3. **Team Creation Fails**:
   - Ensure minimum players in waiting room
   - Check API connectivity
   - Verify database is accessible

4. **Rating Not Updating**:
   - Confirm match result was recorded
   - Check API logs for errors
   - Verify database connection

### Logs and Debugging
- Set `DEBUG=true` in environment for detailed logging
- Check console output for error messages
- Monitor API server logs for database issues

## Testing

Run the test suite:
```bash
pytest tests/test_commands.py -v
```

## Support

For issues and feature requests, check the project documentation or create an issue in the repository.

## License

This project is part of the Discord Team Balance Bot system.