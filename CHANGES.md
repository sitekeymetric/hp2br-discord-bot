# HP2BR Discord Bot - Change Log

This file tracks all changes and version updates for the HP2BR Discord Bot system.

---
## v2.14.2-build.1 - 2025-08-09

### Changes
- **Replaced snake draft with fully random assignment**: Snake draft was too structured and predictable
- **New random balanced assignment algorithm**: Players are completely shuffled and randomly assigned to teams while maintaining size balance
- **Enhanced NP mode randomization**: Increased attempts from 10 to 15 random assignments + 3 greedy attempts
- **Removed rating-based sorting in greedy algorithm**: Now uses full randomization for maximum variety
- **Added comprehensive logging**: Shows shuffled player order and team slot assignments for transparency

### Algorithm Changes
- `_random_balanced_assignment()`: New method that shuffles both players and team slots for true randomness
- `_distribute_players_randomly()`: Replaces snake draft distribution with random team selection
- `_greedy_partner_avoidance()`: Now fully randomizes player order instead of rating-based sorting
- Regional distribution: Maintains one regional player per team but randomizes their assignment order

### Technical Details
- Build: 1  
- Updated: 2025-08-09T00:10:00.000000
- Breaking Change: Snake draft algorithm completely replaced
- New Feature: True random team generation while maintaining balance

---
## v2.14.1-build.1 - 2025-08-09

### Changes
- Enhanced randomization in team generation to fix identical team issue
- Improved random seed generation using time + process ID + object ID
- Increased NP mode attempts from 5 to 10 snake draft tries + 3 greedy attempts
- Added tie-breaking randomization when multiple teams have equal penalty scores
- Added pre-shuffle randomization to NP mode algorithms
- Enhanced logging to show random seed values for debugging

### Technical Details
- Build: 1
- Updated: 2025-08-09T00:05:00.000000

---
## v2.14.0-build.1 - 2025-08-09

### Major Feature: New Partners (NP) Mode

#### Core Changes
- **Replaced `num_teams` parameter with `np` mode**: `/create_teams` now uses `np: Optional[bool] = False` instead of manual team count selection
- **Automatic team count determination**: Bot now intelligently calculates optimal team count based on player count (6-8 players = 2 teams, 9-12 = 3 teams, etc.)
- **New Partners algorithm**: When `np=true`, creates teams by minimizing repeated partnerships using partnership history from completed matches

#### NP Mode Algorithm Features
- **Partnership matrix building**: Analyzes historical teammate data to identify frequent partnerships
- **Dual strategy approach**: Uses both snake draft randomization and greedy partner avoidance algorithms
- **Regional exemptions**: When region is specified, players from that region are exempt from partnership penalties against each other
- **Penalty scoring**: Applies exponential penalty scaling (games_together^1.5) to discourage repeated partnerships
- **Comprehensive logging**: Detailed partnership analysis and penalty scoring for transparency

#### Technical Implementation
- Enhanced `TeamBalancer.create_balanced_teams()` with `np_mode` parameter
- Added `_create_teams_with_new_partners()` - main NP mode orchestrator  
- Added `_build_partnership_matrix()` - builds partnership history from API data
- Added `_calculate_partnership_penalty()` - calculates penalty scores with regional exemptions
- Added `_greedy_partner_avoidance()` - greedy algorithm for optimal team assignment
- Added `_ensure_regional_distribution()` - ensures regional requirements are met
- Added `_log_partnership_analysis()` - detailed logging of partnership decisions

#### User Experience
- **Seamless integration**: NP mode works with existing region requirements and custom formats
- **Smart messaging**: Shows "New Partners Mode: Minimizing repeated partnerships" when enabled
- **Backward compatibility**: All existing functionality (region requirements, custom formats) works identically

### Technical Details
- Build: 1
- Updated: 2025-08-09T00:00:00.000000
- Breaking Change: `num_teams` parameter removed from `/create_teams`
- New Feature: `np` parameter enables partnership optimization
- Regional Integration: NP mode respects regional distribution requirements

---
## v2.13.6-build.1 - 2025-08-08

### Changes
- Fixed ImportError in advanced_rating_commands by correcting embed imports and disabling conflicting extension

### Technical Details
- Build: 1
- Updated: 2025-08-08T23:05:36.636730

---

## v2.13.5-build.1 - 2025-08-08

### Changes
- Fixed JSON parsing error in VERSION.json caused by Git merge conflict markers

### Technical Details
- Build: 1
- Updated: 2025-08-08T23:02:53.809922

---

## v2.13.4-build.1 - 2025-08-08

### Changes
- Fixed team randomization by creating fresh TeamBalancer instances and adding comprehensive debug logging to identify randomization issues

### Technical Details
- Build: 1
- Updated: 2025-08-08T22:44:29.544673

---

## v2.13.3-build.1 - 2025-08-08

### Changes
- Enhanced Discord rate limit debugging with complete header inspection and configurable verbose logging

### Technical Details
- Build: 1
- Updated: 2025-08-08T16:52:34.918472

---

## v2.13.2-build.1 - 2025-08-08

### Changes
- Added proper Discord API rate limit handling for command syncing with Retry-After header support and configurable sync options

### Technical Details
- Build: 1
- Updated: 2025-08-08T14:09:40.440692

---

## v2.13.1-build.1 - 2025-08-07

### Changes
- Removed leaderboard note and descriptive text for cleaner leaderboard display

### Technical Details
- Build: 1
- Updated: 2025-08-07T00:00:00.000000

---

## v2.13.0-build.1 - 2025-08-06

### Changes
- Replaced redundant timestamps with Paizen bot version number in all Discord embeds for better branding and less clutter

### Technical Details
- Build: 1
- Updated: 2025-08-06T17:36:40.842697

---

## v2.12.2-build.1 - 2025-08-06

### Changes
- Changed Submit Results button to Finalize Results for better clarity

### Technical Details
- Build: 1
- Updated: 2025-08-06T10:49:51.787924

---

## v2.12.1-build.1 - 2025-08-06

### Changes
- Fixed /record_result UI to show disabled buttons after Submit Results is clicked

### Technical Details
- Build: 1
- Updated: 2025-08-06T10:43:56.945787

---

## v2.12.0-build.1 - 2025-08-06

### Changes
- Added controlled randomization to team balancing: rating band shuffling, similar rating randomization, and random starting teams for variety while maintaining balance

### Technical Details
- Build: 1
- Updated: 2025-08-06T10:19:25.387356

---

## v2.11.1-build.1 - 2025-08-06

### Changes
- Changed 'Most Frequent Partners' to 'Most Frequent Teammates' in stats display

### Technical Details
- Build: 1
- Updated: 2025-08-06T10:06:47.400481

---

## v2.11.0-build.1 - 2025-08-06

### Changes
- Enhanced teammate stats: two categories - Most Frequent Partners (top 5 with avg skill gain) and Championship Partners (top 5 with 1st place wins and win rate)

### Technical Details
- Build: 1
- Updated: 2025-08-06T10:03:23.274618

---

## v2.10.3-build.1 - 2025-08-06

### Changes
- Fixed Member Since calculation in /stats to handle datetime objects correctly, now shows proper account age

### Technical Details
- Build: 1
- Updated: 2025-08-06T09:46:08.050115

---

## v2.10.2-build.1 - 2025-08-06

### Changes
- Made /match_history command ephemeral (only visible to user) like /stats and /set_region

### Technical Details
- Build: 1
- Updated: 2025-08-06T09:44:24.652460

---

## v2.10.1-build.1 - 2025-08-06

### Changes
- Made /stats command ephemeral (only visible to user) like /set_region

### Technical Details
- Build: 1
- Updated: 2025-08-06T09:37:22.261707

---

## v2.10.0-build.1 - 2025-08-06

### Changes
- Enhanced match history to show up to 4 teammates by name (was 3), better team visibility

### Technical Details
- Build: 1
- Updated: 2025-08-06T09:34:03.396093

---

## v2.9.0-build.1 - 2025-08-06

### Changes
- Optimized match history display: removed 'with' and 'skill' words, show up to 3 full teammate names

### Technical Details
- Build: 1
- Updated: 2025-08-06T09:32:25.196369

---

## v2.8.0-build.1 - 2025-08-05

### Changes
- Enhanced /match_history to show last 10 games by default, current rank, and detailed skill changes with improved visual indicators

### Technical Details
- Build: 1
- Updated: 2025-08-05T23:55:26.248883

---

## v2.7.0-build.1 - 2025-08-05

### Changes
- Added custom team format parameter to /create_teams (e.g., format='3:3:4' creates teams of 3, 3, and 4 players)

### Technical Details
- Build: 1
- Updated: 2025-08-05T22:42:07.848523

---

## v2.6.0-build.1 - 2025-08-05

### Changes
- Enhanced team distribution algorithm to ensure optimal team sizes (9 players = 3:3:3, 10 players = 4:3:3, etc.)

### Technical Details
- Build: 1
- Updated: 2025-08-05T22:36:09.725319

---

## v2.5.3-build.1 - 2025-08-05

### Changes
- Created comprehensive database migration system with deployment scripts to fix production database issues

### Technical Details
- Build: 1
- Updated: 2025-08-05T21:45:02.792660

---

## v2.5.2-build.1 - 2025-08-05

### Changes
- Fixed /leaderboard and /stats errors by applying soft-delete migration to correct database file (team_balance.db)

### Technical Details
- Build: 1
- Updated: 2025-08-05T21:41:54.726871

---

## v2.5.1-build.1 - 2025-08-05

### Changes
- Fixed leaderboard API error by adding soft-delete filtering to guild user queries

### Technical Details
- Build: 1
- Updated: 2025-08-05T21:38:41.757406

---

## v2.5.0-build.1 - 2025-08-05

### Changes
- Made team voice channels open - players can freely join/leave without permission restrictions

### Technical Details
- Build: 1
- Updated: 2025-08-05T21:17:56.184136

---

## v2.4.0-build.1 - 2025-08-05

### Changes
- Enhanced team generation to prioritize minimum 3 players per team with smarter default team counts

### Technical Details
- Build: 1
- Updated: 2025-08-05T21:00:43.706265

---

## v2.3.3-build.1 - 2025-08-05

### Changes
- Fixed /delete_account foreign key constraint error by implementing soft delete system

### Technical Details
- Build: 1
- Updated: 2025-08-05T20:54:55.940341

---

## v2.3.2-build.1 - 2025-08-05

### Changes
- Fixed Discord modal field length limits causing Team 2+ placement input errors

### Technical Details
- Build: 1
- Updated: 2025-08-05T20:39:33.669651

---

## v2.3.1-build.1 - 2025-08-05

### Changes
- Fixed VoiceManager initialization error in auto-registration for /stats and /leaderboard commands

### Technical Details
- Build: 1
- Updated: 2025-08-05T18:48:56.843996

---

## v2.3.0-build.1 - 2025-08-05

### Changes
- Enhanced auto-registration: /stats and /leaderboard now auto-register players found in waiting room

### Technical Details
- Build: 1
- Updated: 2025-08-05T18:37:34.461330

---

## v2.2.0-build.1 - 2025-08-05

### Changes
- Enhanced /match_history with color-coded icons based on rating changes: green (+10+), yellow (-9 to +9), red (-10+)

### Technical Details
- Build: 1
- Updated: 2025-08-05T18:17:59.203377

---

## v2.1.3-build.1 - 2025-08-05

### Changes
- Fixed End Game button voice channel cleanup to work like /cleanup command

### Technical Details
- Build: 1
- Updated: 2025-08-05T18:12:31.628663

---

## v2.1.2-build.1 - 2025-08-05

### Changes
- Fixed API data format issue causing 422 error when submitting placement results

### Technical Details
- Build: 1
- Updated: 2025-08-05T18:05:24.811060

---

## v2.1.1-build.1 - 2025-08-05

### Changes
- Fixed missing end_game method in PlacementResultView causing End Game button error

### Technical Details
- Build: 1
- Updated: 2025-08-05T18:00:28.329072

---

## v2.1.0-build.1 - 2025-08-05

### Changes
- Added support for external competitions: allow placements 1-30, detect guild vs external matches automatically

### Technical Details
- Build: 1
- Updated: 2025-08-05T17:58:52.513674

---

## v2.0.2-build.1 - 2025-08-05

### Changes
- Fixed missing datetime import causing error in /record_result command

### Technical Details
- Build: 1
- Updated: 2025-08-05T17:52:47.411508

---

## v2.0.1-build.1 - 2025-08-05

### Changes
- Added placement-based result recording API endpoint and database migration support

### Technical Details
- Build: 1
- Updated: 2025-08-05T17:50:19.458848

---

## v2.0.0-build.1 - 2025-08-05

### Changes
- Implemented placement-based rating system (Rank 7 baseline) replacing win/loss system for all matches

### Technical Details
- Build: 1
- Updated: 2025-08-05T17:37:13.905550

---

## v1.9.6-build.1 - 2025-08-05

### Changes
- Added teammate display to match history - shows who you played with in each match

### Technical Details
- Build: 1
- Updated: 2025-08-05T16:56:06.905705

---

## v1.9.5-build.1 - 2025-08-05

### Changes
- Fixed ConfirmationView attribute error in admin commands (changed 'result' to 'value')

### Technical Details
- Build: 1
- Updated: 2025-08-05T16:51:38.019270

---

## v1.9.4-build.1 - 2025-08-05

### Changes
- Fixed API route ordering conflict that was causing 422 errors in leaderboard command

### Technical Details
- Build: 1
- Updated: 2025-08-05T16:46:09.220865

---

## v1.9.3-build.1 - 2025-08-05

### Changes
- Fixed /leaderboard to show all registered players, not just those with completed matches

### Technical Details
- Build: 1
- Updated: 2025-08-05T16:44:32.340775

---

## v1.9.2-build.1 - 2025-08-05

### Changes
- Integrated top 3 teammates and win rates into main /stats command display

### Technical Details
- Build: 1
- Updated: 2025-08-05T16:38:29.828545

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
