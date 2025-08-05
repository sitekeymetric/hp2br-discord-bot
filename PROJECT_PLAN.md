# Discord Team Balance Bot - Project Plan

## Project Overview
A Discord.py bot system that creates balanced teams for competitive gameplay using skill ratings, with database persistence and API layer for multi-guild support.

## Architecture
- **Component 1**: Discord Bot (Python with discord.py)
- **Component 2**: Database API (FastAPI/Flask REST service)

---

# 🎯 MVP (Minimum Viable Product)

## MVP Goal
Create balanced teams from "Waiting Room" voice channel participants, display team proposals, and track basic results.

## MVP User Flow
1. Players join "Waiting Room" voice channel
2. Admin runs `/create_teams` command
3. Bot analyzes players and creates balanced teams
4. Bot presents team proposal with Accept/Decline buttons
5. On acceptance, players are moved to team voice channels
6. Admin records match results
7. Player ratings are updated

---

## MVP Phase 1: Database Foundation
**Duration**: 2 days | **Priority**: Critical | **Component**: Database API

### Core Tables (MVP)
```sql
-- Complete schema for MVP with full historical tracking
Users: 
  - guild_id (bigint) - Discord server ID
  - user_id (bigint) - Discord user ID  
  - username (varchar) - Current Discord username
  - region_code (varchar) - User's region (NA, EU, AS, OCE, etc.)
  - rating_mu (float) - Glicko-2 skill rating
  - rating_sigma (float) - Glicko-2 uncertainty
  - games_played (int) - Total matches participated
  - wins (int) - Total wins
  - losses (int) - Total losses
  - draws (int) - Total draws
  - created_at (datetime) - Account creation
  - last_updated (datetime) - Last modification
  - PRIMARY KEY: (guild_id, user_id)

Matches:
  - match_id (uuid) - Unique match identifier
  - guild_id (bigint) - Discord server ID
  - created_by (bigint) - User who initiated match
  - start_time (datetime) - When match was created
  - end_time (datetime) - When result was recorded
  - status (enum) - 'pending', 'completed', 'cancelled'
  - result_type (enum) - 'win_loss', 'draw', 'cancelled'
  - winning_team (int) - Team number that won (null for draw)
  - total_teams (int) - Number of teams in match
  - created_at (datetime) - Record creation
  - PRIMARY KEY: match_id

Match_Players:
  - match_id (uuid) - Foreign key to Matches
  - user_id (bigint) - Discord user ID
  - guild_id (bigint) - Discord server ID
  - team_number (int) - Which team (1, 2, 3, etc.)
  - rating_mu_before (float) - Rating before match
  - rating_sigma_before (float) - Uncertainty before match
  - rating_mu_after (float) - Rating after match (null if pending)
  - rating_sigma_after (float) - Uncertainty after match (null if pending)
  - result (enum) - 'win', 'loss', 'draw', 'pending'
  - PRIMARY KEY: (match_id, user_id)
  - FOREIGN KEY: (guild_id, user_id) -> Users(guild_id, user_id)
```

### MVP API Endpoints

#### User Management (Full CRUD)
- `POST /users` - Create new user
- `GET /users/{guild_id}` - Get all users in guild
- `GET /users/{guild_id}/{user_id}` - Get specific user stats
- `PUT /users/{guild_id}/{user_id}` - Update user information (region, username)
- `DELETE /users/{guild_id}/{user_id}` - Delete user (admin only)
- `PUT /users/{guild_id}/{user_id}/rating` - Update rating (internal use)

#### Match Management (Full CRUD)
- `POST /matches` - Create new match
- `GET /matches/{guild_id}` - Get guild's match history
- `GET /matches/{match_id}` - Get specific match details
- `PUT /matches/{match_id}` - Update match (status, end_time)
- `DELETE /matches/{match_id}` - Delete match (admin only)
- `PUT /matches/{match_id}/result` - Record match result (win/loss/draw)

#### Match Players (Full CRUD)
- `POST /matches/{match_id}/players` - Add players to match
- `GET /matches/{match_id}/players` - Get all players in match
- `PUT /matches/{match_id}/players/{user_id}` - Update player's match data
- `DELETE /matches/{match_id}/players/{user_id}` - Remove player from match

#### Analytics & History
- `GET /users/{guild_id}/{user_id}/history` - User's match history
- `GET /users/{guild_id}/{user_id}/stats` - Detailed user statistics
- `GET /guilds/{guild_id}/leaderboard` - Guild rankings
- `GET /matches/{guild_id}/recent` - Recent matches for guild

### MVP Rating System
- **Simple Glicko-2**: μ (skill), σ (uncertainty)
- **Initial Values**: μ=1500, σ=350
- **Team Rating**: Average μ of all players
- **Post-Match**: Basic rating updates

**MVP Deliverable**: Working database + API with core functionality

---

## MVP Phase 2: Basic Discord Bot
**Duration**: 2 days | **Priority**: Critical | **Component**: Discord Bot

### MVP Bot Features
- `/register [region]` - Register user in system with optional region
- `/set_region <region_code>` - Update user's region (NA, EU, AS, etc.)
- `/stats [@user]` - Show user stats
- `/create_teams` - Generate teams from waiting room
- `/record_result <winning_team>` - Record match outcome

### MVP User Management
- Auto-register users on first command
- Basic stats display (rating, games, win%)
- Guild-specific data isolation

### MVP Voice Channel Detection
- Detect "Waiting Room" voice channel
- Get list of connected players (6-15 players)
- Validate minimum players for team creation

**MVP Deliverable**: Basic bot with user management and voice detection

---

## MVP Phase 3: Team Balancing
**Duration**: 2 days | **Priority**: Critical | **Component**: Both

### MVP Balancing Algorithm
```python
def create_balanced_teams(players):
    # Simple algorithm for MVP
    sorted_players = sort_by_rating(players)
    teams = distribute_snake_draft(sorted_players, num_teams=3)
    return teams
```

### MVP Balance Logic
- **Primary**: Snake draft by rating (highest→lowest→lowest→highest)
- **Teams**: 3-5 teams of 3-4 players each
- **Fallback**: Random distribution if ratings similar

### MVP Team Display
- Show teams with player names and ratings
- Calculate team average rating
- Simple "Team 1", "Team 2", "Team 3" naming

**MVP Deliverable**: Working team generation with basic balancing

---

## MVP Phase 4: User Interface
**Duration**: 2 days | **Priority**: Critical | **Component**: Discord Bot

### MVP Team Proposal
```
🎮 **Team Proposal** 🎮
**Team 1** (Avg: 1520)
• Player1 (1600)
• Player2 (1450)
• Player3 (1510)

**Team 2** (Avg: 1505)
• Player4 (1580)
• Player5 (1420)
• Player6 (1515)

**Team 3** (Avg: 1495)
• Player7 (1550)
• Player8 (1440)

✅ Accept Teams    ❌ Decline    ⏱️ Expires in 5 minutes
```

### MVP Interaction
- Accept/Decline buttons (Discord interactions)
- 5-minute timeout
- Simple confirmation message
- Basic error handling

**MVP Deliverable**: Interactive team proposal system

---

## MVP Phase 5: Voice Management
**Duration**: 2 days | **Priority**: Critical | **Component**: Discord Bot

### MVP Voice Features
- Create temporary team channels ("Team 1", "Team 2", etc.)
- Move players to their assigned team channels
- Basic cleanup after match ends

### MVP Session Management
- Track active matches
- `/end_match` command to cleanup channels
- Return players to waiting room

**MVP Deliverable**: Automated player movement and channel management

---

## MVP Phase 6: Results & Ratings
**Duration**: 1 day | **Priority**: Critical | **Component**: Both

### MVP Result Recording
- `/record_result 1` (Team 1 wins)
- `/record_result draw` (Draw result)
- Update all player ratings via API

### MVP Rating Updates
- Simple Glicko-2 calculation
- Winner ratings increase, loser ratings decrease
- Draw = smaller rating changes

**MVP Deliverable**: Complete match lifecycle with rating updates

---

# 🚀 POST-MVP ENHANCEMENTS

## Enhancement Phase 1: Advanced Features
**Duration**: 3-4 days | **Priority**: Medium

### Enhanced Balancing
- Region-based distribution
- Multiple balancing algorithms
- Team composition optimization
- Machine learning improvements

### Better UI/UX
- Rich embeds with colors
- Player avatars and regions
- Interactive settings panel
- Better error messages

### Advanced Statistics
- Detailed player analytics
- Match history tracking
- Leaderboards and rankings
- Performance trends

**Deliverable**: Enhanced user experience and balancing

---

## Enhancement Phase 2: Production Features
**Duration**: 2-3 days | **Priority**: Low

### Configuration System
- Guild-specific settings
- Admin configuration panel
- Feature toggles
- Backup/restore functionality

### Monitoring & Reliability
- Health checks and logging
- Error recovery mechanisms
- Performance monitoring
- Database backups

### Integrations
- External API connections
- Webhook notifications
- Data export capabilities
- Multi-server deployment

**Deliverable**: Production-ready system

---

# 📋 MVP DEVELOPMENT CHECKLIST

## Database API (Component 1)
- [ ] SQLite database setup
- [ ] FastAPI service structure
- [ ] User CRUD endpoints
- [ ] Match CRUD endpoints
- [ ] Basic Glicko-2 implementation
- [ ] API testing and documentation

## Discord Bot (Component 2)
- [ ] Discord.py bot setup
- [ ] Basic command structure
- [ ] Voice channel monitoring
- [ ] User registration system
- [ ] Team balancing algorithm
- [ ] Interactive UI components
- [ ] Voice channel management
- [ ] API integration layer

## Integration Testing
- [ ] End-to-end user flow
- [ ] Error handling validation
- [ ] Performance testing
- [ ] Multi-guild testing
- [ ] Load testing with multiple users

---

# 🛠️ TECHNICAL SETUP

## Project Structure (MVP)
```
discord-team-bot/
├── api/                    # Component 1: Database API
│   ├── main.py            # FastAPI entry point
│   ├── models.py          # Database models
│   ├── routes.py          # API endpoints
│   ├── database.py        # Database connection
│   └── rating.py          # Glicko-2 calculations
├── bot/                   # Component 2: Discord Bot
│   ├── main.py            # Bot entry point
│   ├── commands.py        # Slash commands
│   ├── teams.py           # Team balancing logic
│   ├── voice.py           # Voice channel management
│   ├── ui.py              # Discord UI components
│   └── api_client.py      # API integration
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables
└── README.md             # Setup instructions
```

## MVP Technology Stack
- **Discord Bot**: discord.py 2.3+
- **API**: FastAPI (faster development than Flask)
- **Database**: SQLite3 with SQLAlchemy ORM
- **Testing**: pytest for unit tests
- **Deployment**: Docker containers (optional)

## MVP Success Metrics
- [ ] Creates balanced teams (team rating variance < 150)
- [ ] Successful team creation rate > 90%
- [ ] Player movement success rate > 95%
- [ ] Rating system converges appropriately
- [ ] 5-minute setup time from command to game start
- [ ] Zero data loss in match recording

---

This reorganized plan prioritizes MVP delivery in ~10 days, with clear component separation and post-MVP enhancement phases.
