# HP2BR Discord Bot - Change Log

This file tracks all changes and version updates for the HP2BR Discord Bot system.

---
## v1.9.1-build.1 - 2025-08-05

### Changes
- Added flexibility for teams < 3 to report all losses (forfeit/incomplete matches) without requiring a winner

### Technical Details
- Build: 1
- Updated: 2025-08-05T16:35:56.037963

---

## v1.9.0-build.1 - 2025-08-05

### Changes
- Added /teammates command to show top teammates and win rates with each teammate

### Technical Details
- Build: 1
- Updated: 2025-08-05T16:31:21.462716

---

## v1.8.0-build.1 - 2025-08-05

### Changes
- Enhanced match history to show full dates (MM/DD/YY), use match completion time, and display rating changes

### Technical Details
- Build: 1
- Updated: 2025-08-05T16:27:01.738931

---

## v1.7.1-build.1 - 2025-08-05

### Changes
- Fixed 'int' object is not iterable error in /create_teams with region parameter for single players

### Technical Details
- Build: 1
- Updated: 2025-08-05T16:24:00.040300

---

## v1.7.0-build.1 - 2025-08-05

### Changes
- Removed End Game from team creation, added to match results; added region-based team balancing to /create_teams

### Technical Details
- Build: 1
- Updated: 2025-08-05T16:18:50.931315

---

## v1.6.0-build.1 - 2025-08-05

### Changes
- Implemented COMPLETED-only statistics and automatic pending match cleanup during result recording

### Technical Details
- Build: 1
- Updated: 2025-08-05T15:43:14.061652

---

## v1.5.0-build.1 - 2025-08-05

### Changes
- Enhanced /record_result with interactive dialogue: dropdown selections for each team (win/loss/draw) with validation

### Technical Details
- Build: 1
- Updated: 2025-08-05T15:18:12.782363

---

## v1.4.0-build.1 - 2025-08-05

### Changes
- Improved UX: replaced Accept/Decline with Create Team/End Game buttons, removed timeout for persistent UI

### Technical Details
- Build: 1
- Updated: 2025-08-05T15:13:50.668027

---

## v1.3.1-build.1 - 2025-08-05

### Changes
- Fixed team acceptance system: removed voting, extended timeout to 15 minutes, improved player movement error handling

### Technical Details
- Build: 1
- Updated: 2025-08-05T15:07:12.664494

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
