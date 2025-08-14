# 🎮 Player OpenSkill Analyzer

A comprehensive Python script to generate OpenSkill performance analysis for any player in your Discord bot database.

## 📋 Features

- **Complete OpenSkill Analysis**: μ (skill), σ (uncertainty), conservative rating
- **Visual Dashboard**: 8 different charts showing performance metrics
- **Match History**: Detailed progression over time
- **Performance Trends**: Rolling averages and confidence intervals
- **Automatic Saving**: Generates PNG files with analysis results

## 🚀 Usage

### Basic Usage
```bash
# Analyze a player by user_id (uses default guild)
python3 player_openskill_analyzer.py <user_id>

# Examples:
python3 player_openskill_analyzer.py 746147492399284237  # paizen
python3 player_openskill_analyzer.py 1095054798350454885  # aKyle
```

### Advanced Usage
```bash
# Specify custom guild_id
python3 player_openskill_analyzer.py <user_id> <guild_id>

# Specify custom database path
python3 player_openskill_analyzer.py <user_id> --db /path/to/database.db

# Full example with all options
python3 player_openskill_analyzer.py 746147492399284237 696226047229952110 --db api/team_balance.db
```

### Help
```bash
python3 player_openskill_analyzer.py --help
```

## 📊 Output

The script generates:

1. **PNG File**: `{username}_openskill_analysis.png` - Complete visual dashboard
2. **Console Output**: Key statistics summary
3. **Interactive Display**: Shows the graph on screen (if display available)

## 📈 Dashboard Components

### 1. **Rating Progression Over Time**
- μ (Skill) progression
- Conservative rating trend
- 99.7% confidence intervals
- Starting baseline and current status

### 2. **Skill vs Uncertainty Evolution**
- Skill level changes over matches
- Uncertainty reduction over time
- System confidence in rating

### 3. **Match Results Distribution**
- Win/Loss pie chart
- Win rate percentage

### 4. **Placement Distribution**
- Frequency of each placement
- Highlights 1st place finishes (wins)

### 5. **Skill Changes Per Match**
- Individual match performance impact
- Biggest gains and losses highlighted
- Green = skill increase, Red = skill decrease

### 6. **Confidence Evolution**
- 99.7%, 95.4%, and 68.2% confidence bands
- Conservative rating progression
- System certainty visualization

### 7. **Performance Trends**
- Rolling averages (5-match windows)
- Skill and placement trends
- Performance trajectory

### 8. **Statistics Summary**
- Current ratings and changes
- Performance insights
- Trend analysis

## 🔍 Example Players

### Known User IDs in Database:
- **paizen**: `746147492399284237`
- **aKyle (a카일)**: `1095054798350454885`
- **Natedog**: `183105528627462144`
- **wegotseven**: `234493397694414848`
- **데트**: `413581018214301718`

## 📁 File Structure

```
hp2br-discord-bot/
├── player_openskill_analyzer.py    # Main script
├── api/team_balance.db             # Database file
└── {username}_openskill_analysis.png  # Generated output
```

## 🛠️ Requirements

- Python 3.7+
- matplotlib
- pandas
- seaborn
- numpy

Install dependencies:
```bash
pip3 install matplotlib pandas seaborn numpy
```

## 🎯 OpenSkill Metrics Explained

### **μ (Mu) - Skill Level**
- Represents the player's estimated skill
- Higher = better player
- Starts at 25.0 for new players

### **σ (Sigma) - Uncertainty**
- How confident the system is in the skill rating
- Lower = more confident
- Decreases as more matches are played

### **Conservative Rating**
- μ - 3σ (worst-case skill estimate)
- Used for matchmaking to avoid unfair matches
- Negative values indicate below-average skill

## 🎉 Example Output

```
✅ Found 41 matches for paizen
✅ Analysis saved as: paizen_openskill_analysis.png

📊 paizen's OpenSkill Stats Summary:
   • Total Matches: 41
   • Win Rate: 19.5% (8 wins)
   • Current μ (Skill): 11.7
   • Current σ (Uncertainty): 6.9
   • Conservative Rating: -8.9
   • Skill Change: -13.3
   • Peak Skill: 26.7
   • Average Placement: 4.4
   • Performance Trend: Declining
```

## 🚨 Troubleshooting

### Database Not Found
```
❌ Database file not found: api/team_balance.db
```
**Solution**: Run from the correct directory or specify path with `--db`

### Player Not Found
```
❌ Player with user_id 123456789 not found in guild 696226047229952110
```
**Solution**: Check the user_id and guild_id are correct

### No OpenSkill Data
```
❌ No OpenSkill rating found for username
```
**Solution**: Player hasn't played any matches with OpenSkill tracking enabled
