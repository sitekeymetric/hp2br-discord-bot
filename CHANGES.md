# HP2BR Discord Bot - Change Log

This file tracks all changes and version updates for the HP2BR Discord Bot system.

---
## v1.3.0-build.1 - 2025-08-05

### Changes
- Added special cases for small player counts (1-5 players) with intelligent team configuration

### Technical Details
- Build: 1
- Updated: 2025-08-05T15:02:32.503773

---

## v1.2.0-build.1 - 2025-08-05

### Major Feature: Special Cases for Small Player Counts

#### New Features
- **Flexible Player Requirements**: Minimum players reduced from 6 to 1
- **Single Team Mode (1-4 players)**: Creates single team for practice/warmup sessions
- **2:3 Split Mode (5 players)**: Intelligently splits into 2 teams (top 2 vs bottom 3 by rating)
- **Auto-Detection**: Bot automatically determines optimal team configuration based on player count

#### Enhanced Team Creation
- **Smart Team Count**: `/create_teams` now auto-determines team count for special cases
- **Contextual UI**: Adaptive embeds and messaging based on team configuration
- **Special Case Notifications**: Clear messaging explaining the configuration being used

#### Technical Improvements
- Added `SINGLE_TEAM_THRESHOLD = 4` and `TWO_TEAM_THRESHOLD = 5` constants
- Enhanced `TeamBalancer` with `_split_five_players()` method
- Updated team proposal embeds for single team scenarios
- Improved validation logic for flexible player counts

#### Configuration Updates
- `MIN_PLAYERS_FOR_TEAMS`: 6 → 1
- `.env.example` updated to reflect new minimum
- Added special case thresholds to constants

### Technical Details
- Build: 1
- Updated: 2025-08-05T22:00:00
- Backward Compatible: All existing 6+ player functionality unchanged
- New Logic: 1-4 players → 1 team, 5 players → 2 teams (2:3), 6+ players → normal balancing

---
## v1.1.0-build.1 - 2025-08-05

### Changes
- Added versioning system with automatic changelog updates

### Technical Details
- Build: 1
- Updated: 2025-08-05T14:51:29.667889

---


## v1.0.0-build.1 - 2025-01-05

### Changes
- Initial release with Waiting Room voice channel support
- Implemented team balancing system with flexible player counts
- Added user registration and rating system
- Created voice channel management with exact name matching
- Added admin commands for setup and management
- Implemented match tracking and statistics
- Added comprehensive error handling and validation

### Technical Details
- Build: 1
- Updated: 2025-01-05T21:00:00
- Voice Channel: "Waiting Room" (exact match required)
- Database: FastAPI backend integration
- Discord.py: Modern slash commands implementation

### Features
- `/register` - User registration system
- `/create_teams` - Balanced team creation from waiting room
- `/record_result` - Match result tracking
- `/setup` - Initial bot configuration
- `/status` - System status and statistics
- Automatic voice channel creation and cleanup
- Team proposal voting system
- Comprehensive logging and error handling

---
