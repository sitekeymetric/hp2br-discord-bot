# OpenSkill Parallel Rating System

## 🎯 Overview

The OpenSkill parallel rating system runs alongside the existing placement-based rating system, providing team-based skill assessment for multi-team competitions. Both systems process the same matches simultaneously, allowing for direct comparison and analysis.

## ✨ Key Features

- **🔄 Parallel Processing**: Runs alongside existing placement system without interference
- **👥 Team-Based**: Considers team composition and synergy, not just individual skill
- **🏆 Multi-Team Support**: Handles 2-30 teams in competitions
- **🌍 External Competition**: Models guild teams competing against external opponents
- **📊 Uncertainty Modeling**: Tracks confidence in skill estimates
- **🔍 Conservative Estimates**: Provides reliable skill assessments

## 🎮 How It Works

### **Rating Components**
- **μ (Mu)**: Skill estimate (higher = more skilled)
- **σ (Sigma)**: Uncertainty (lower = more confident estimate)
- **Display Rating**: μ × 60 (scaled to familiar 1500 baseline)
- **Ordinal**: μ - 3σ (conservative skill estimate)

### **Team Strength Calculation**
OpenSkill combines individual player ratings to calculate team strength:
```
Team Skill = Sum of player μ values
Team Uncertainty = √(Sum of player σ² values)
```

### **Competition Types**
1. **Guild-Only**: All teams from your guild (consecutive placements 1,2,3...)
2. **External**: Guild teams competing against external teams (gaps in placements)
3. **Mixed**: Combination of guild and external teams

## 📋 Commands

### **User Commands**
- `/openskill_stats [@user]` - View OpenSkill ratings and recent matches
- `/openskill_leaderboard [limit]` - Guild OpenSkill leaderboard
- `/rating_comparison [@user]` - Compare OpenSkill vs Placement ratings

### **Admin Commands**
- `/openskill_recalculate` - Recalculate from historical matches (manual process)

### **Existing Commands Enhanced**
- `/record_result` - Now updates both rating systems automatically
- `/stats` - Shows placement ratings (OpenSkill available via separate commands)

## 🔧 API Endpoints

### **OpenSkill Endpoints**
```
GET /openskill/ratings/{guild_id}           # Leaderboard
GET /openskill/ratings/{guild_id}/{user_id} # User rating
GET /openskill/history/{guild_id}/{user_id} # Match history
GET /openskill/stats/{guild_id}             # Guild statistics
GET /openskill/compare/{guild_id}           # System comparison
POST /openskill/process-match/{match_id}    # Process match
POST /openskill/initialize/{guild_id}       # Initialize ratings
```

### **Enhanced Existing Endpoints**
```
PUT /matches/{match_id}/placement-result    # Now processes both systems
```

## 📊 Database Schema

### **New Tables**
```sql
-- OpenSkill user ratings
openskill_ratings (
    guild_id, user_id,           -- Primary key
    mu, sigma,                   -- OpenSkill rating values
    games_played,                -- Match count
    created_at, last_updated     -- Timestamps
)

-- OpenSkill match history
openskill_match_history (
    id,                          -- Auto-increment primary key
    match_id, guild_id, user_id, -- Match and user reference
    team_number, team_placement, -- Team info
    total_competitors,           -- Competition size
    guild_teams_count,           -- Guild teams in competition
    external_teams_count,        -- External teams
    competition_type,            -- 'guild_only', 'mixed', 'external'
    mu_before, sigma_before,     -- Rating before match
    mu_after, sigma_after,       -- Rating after match
    rating_change,               -- Display rating change
    display_rating_before,       -- Display rating before
    display_rating_after,        -- Display rating after
    created_at                   -- Timestamp
)
```

## 🚀 Installation

### **Automatic Setup**
```bash
# Run the setup script (recommended)
python3 setup_openskill.py
```

### **Manual Setup**
```bash
# 1. Install OpenSkill
cd api && pip install openskill==5.0.0

# 2. Create database tables
cd api && python3 migrations/create_openskill_tables.py

# 3. Calculate historical ratings
cd api && python3 migrations/calculate_openskill_history.py

# 4. Restart bot and API
```

## 📈 Rating Progression Examples

### **New Player Journey**
```
Start: 1500 (25.0μ ± 8.33σ) - High uncertainty
After 5 games: 1480 (24.7μ ± 6.2σ) - Uncertainty decreasing
After 20 games: 1520 (25.3μ ± 4.1σ) - More stable rating
After 50 games: 1580 (26.3μ ± 2.8σ) - Confident estimate
```

### **Team Performance Impact**
```
Strong team (avg 1600): Smaller rating changes
Weak team (avg 1400): Larger rating changes
Balanced team (avg 1500): Moderate changes
```

### **Competition Size Impact**
```
3-team guild match: ±20 rating change
10-team external competition: ±40 rating change
30-team major competition: ±60 rating change
```

## 🔍 Comparison with Placement System

| Feature | Placement System | OpenSkill System |
|---------|------------------|------------------|
| **Basis** | Final team placement | Team composition + placement |
| **Team Awareness** | Individual focus | Team-based calculations |
| **Uncertainty** | Fixed sigma decay | Dynamic uncertainty modeling |
| **Competition Size** | Fixed point values | Scales with competition size |
| **External Teams** | Ignores external context | Models external opponents |
| **New Players** | Immediate full impact | Gradual confidence building |
| **Rating Range** | 100-3000 | Unlimited (practical ~500-2500) |

## 🎯 Use Cases

### **When OpenSkill Excels**
- **Large external competitions** (10+ teams)
- **Team composition matters** (synergy effects)
- **New player integration** (uncertainty modeling)
- **Varied competition sizes** (adaptive scaling)
- **Long-term accuracy** (confidence building)

### **When Placement System Works Well**
- **Simple guild-only matches** (predictable format)
- **Immediate feedback** (fixed point values)
- **Familiar rating scale** (1500 baseline)
- **Quick calculations** (no team modeling)

## 🔧 Configuration

### **OpenSkill Parameters**
```python
DEFAULT_MU = 25.0        # Initial skill estimate
DEFAULT_SIGMA = 8.333    # Initial uncertainty
DEFAULT_BETA = 4.167     # Performance variance
DEFAULT_TAU = 0.083      # Dynamics factor
```

### **Display Rating Scaling**
```python
display_rating = mu * 60  # 25μ → 1500 display rating
```

## 📊 Monitoring and Analysis

### **Key Metrics to Track**
- **Rating Convergence**: How quickly ratings stabilize
- **Team Balance Quality**: Variance in team strengths
- **Prediction Accuracy**: How well ratings predict outcomes
- **System Correlation**: Agreement between rating systems

### **Analysis Queries**
```sql
-- Compare rating systems
SELECT username, 
       rating_mu as placement_rating,
       (SELECT mu * 60 FROM openskill_ratings WHERE guild_id = u.guild_id AND user_id = u.user_id) as openskill_rating
FROM users u WHERE guild_id = ?;

-- OpenSkill progression
SELECT created_at, display_rating_after 
FROM openskill_match_history 
WHERE guild_id = ? AND user_id = ? 
ORDER BY created_at;
```

## 🛠️ Troubleshooting

### **Common Issues**

#### **OpenSkill ratings not updating**
- Check if OpenSkill tables exist
- Verify API endpoints are accessible
- Check logs for calculation errors

#### **Historical calculation fails**
- Ensure all matches have team_placement data
- Check for database permission issues
- Verify OpenSkill dependency is installed

#### **Rating discrepancies**
- Different systems use different algorithms
- OpenSkill considers team composition
- Competition size affects OpenSkill more

### **Debug Commands**
```bash
# Check OpenSkill installation
python3 -c "import openskill; print('OpenSkill installed')"

# Verify database tables
sqlite3 api/team_balance.db ".tables" | grep openskill

# Check API health
curl http://localhost:8000/openskill/stats/{guild_id}
```

## 🔮 Future Enhancements

### **Planned Features**
- **Hybrid team balancing**: Use both systems for team creation
- **Rating system selection**: Choose which system to use per guild
- **Advanced analytics**: Detailed performance comparisons
- **Machine learning**: Predict match outcomes using both systems

### **Potential Improvements**
- **Dynamic parameters**: Adjust OpenSkill parameters based on guild size
- **Seasonal resets**: Periodic rating adjustments
- **Role-based ratings**: Different ratings for different game roles
- **Tournament mode**: Special handling for tournament formats

## 📚 Resources

- **OpenSkill Library**: [GitHub](https://github.com/vivekjoshy/openskill.py)
- **TrueSkill Paper**: [Microsoft Research](https://www.microsoft.com/en-us/research/publication/trueskilltm-a-bayesian-skill-rating-system/)
- **Rating System Theory**: [Glicko vs TrueSkill vs OpenSkill](https://jmlr.org/papers/v12/weng11a.html)

---

**The OpenSkill parallel rating system provides advanced team-based skill assessment while maintaining complete compatibility with your existing placement-based system. Both systems run concurrently, giving you the best of both worlds for competitive team balancing.**
