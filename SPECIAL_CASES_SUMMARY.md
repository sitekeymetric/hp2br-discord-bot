# Special Cases for Small Player Counts

## Overview
The Discord bot has been updated to handle special cases for small player counts (1-5 players) as requested. This allows for more flexible team creation when there aren't enough players for traditional balanced teams.

## Changes Made

### 1. Updated Configuration (`bot/utils/constants.py`)
- **MIN_PLAYERS_FOR_TEAMS**: Changed from `6` to `1` (now accepts any number of players)
- **Added new thresholds**:
  - `SINGLE_TEAM_THRESHOLD = 4` (1-4 players create single team)
  - `TWO_TEAM_THRESHOLD = 5` (5 players create 2 teams with 2:3 split)

### 2. Enhanced Team Balancer (`bot/services/team_balancer.py`)
- **Special case handling** in `create_balanced_teams()`:
  - 1-4 players: Creates single team (no balancing needed)
  - 5 players: Creates 2 teams with 2:3 split (top 2 vs bottom 3 by rating)
  - 6+ players: Uses normal snake draft balancing
- **Added `_split_five_players()` method**: Intelligently splits 5 players into balanced 2:3 teams

### 3. Updated Team Commands (`bot/commands/team_commands.py`)
- **Flexible team count determination**: Auto-detects special cases and adjusts team count accordingly
- **Enhanced validation**: Removes minimum team count restriction for special cases
- **Special case messaging**: Displays informative messages about the configuration being used
- **Improved parameter handling**: `num_teams` parameter is now optional and auto-determined for special cases

### 4. Enhanced UI (`bot/utils/embeds.py`)
- **Adaptive embed titles**: "Single Team Setup" for 1 team, "Team Proposal" for multiple teams
- **Context-aware descriptions**: Different messaging for single team vs multiple teams
- **Conditional balance display**: Skips balance score for single team scenarios
- **Updated footers**: Appropriate messaging for different scenarios

### 5. Updated Configuration Files
- **`.env.example`**: Updated `MIN_PLAYERS=1` to reflect new minimum
- **Documentation**: Added special case thresholds and explanations

## Special Case Behavior

### 1-4 Players: Single Team
- **Purpose**: Practice, warmup, or casual play
- **Behavior**: All players placed in one team
- **Channel**: Creates single team voice channel
- **UI**: Shows "Practice Team" instead of "Team 1"
- **Balance**: No balance calculation (not applicable)

### 5 Players: 2:3 Split
- **Purpose**: Small competitive matches
- **Behavior**: Top 2 rated players vs bottom 3 rated players
- **Logic**: Balances skill by giving the weaker team an extra player
- **Channels**: Creates 2 team voice channels
- **UI**: Shows both teams with ratings and composition

### 6+ Players: Normal Balancing
- **Purpose**: Standard competitive matches
- **Behavior**: Uses existing snake draft algorithm
- **Teams**: Default 3 teams (or user-specified)
- **Balance**: Full balance scoring and optimization

## Testing Results

The test script confirms correct behavior:
- ✅ 1-4 players → Single team
- ✅ 5 players → 2 teams (2:3 split)
- ✅ 6+ players → Normal balancing (3+ teams)
- ✅ Rating-based splitting for 5-player case works correctly

## Usage Examples

### Single Player (Practice)
```
/create_teams
→ Creates single "Practice Team" with 1 player
→ Message: "Special Case: 1 players - creating single team for practice/warmup"
```

### 5 Players (2:3 Split)
```
/create_teams
→ Creates 2 teams: Team 1 (2 players) vs Team 2 (3 players)
→ Message: "Special Case: 5 players - splitting into 2 teams (2:3)"
→ Top 2 rated players vs bottom 3 rated players
```

### 6+ Players (Normal)
```
/create_teams [num_teams]
→ Uses standard balancing algorithm
→ Creates specified number of teams (default: 3)
```

## Benefits

1. **Flexibility**: Accommodates any number of players (1-24)
2. **Intelligent Handling**: Automatically determines optimal configuration
3. **Clear Communication**: Users understand what's happening and why
4. **Maintains Quality**: Still provides balanced gameplay where possible
5. **Backward Compatibility**: Existing functionality unchanged for 6+ players

## Implementation Notes

- All existing functionality for 6+ players remains unchanged
- Voice channel creation and management works for all scenarios
- Database integration handles single teams and special cases properly
- UI adapts automatically based on team configuration
- Error handling and validation updated for new minimum requirements
