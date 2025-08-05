# Team Acceptance System Fixes (v1.3.1)

## Issues Fixed

### 1. ❌ **Voting System Removed**
**Problem**: Team acceptance required voting from multiple players, which was unnecessary complexity.
**Solution**: Replaced with simple Accept/Decline buttons that any player in the match can click once.

### 2. ⏰ **Timeout Extended to 15 Minutes**
**Problem**: 5-minute timeout was too short for players to organize and accept teams.
**Solution**: Extended timeout to 15 minutes (900 seconds) for more reasonable decision time.

### 3. 🔧 **Improved Player Movement Error Handling**
**Problem**: "Error moving players" with no detailed feedback about what went wrong.
**Solution**: Enhanced error handling with detailed logging and user feedback.

## Changes Made

### 1. **TeamProposalView (bot/utils/views.py)**
- **Removed voting logic**: No more vote counting or majority requirements
- **Simple accept/decline**: Any player in the match can accept or decline teams
- **Better error handling**: Detailed feedback when player movement fails
- **Enhanced logging**: More detailed logs for troubleshooting movement issues

### 2. **Constants (bot/utils/constants.py)**
- **TEAM_PROPOSAL_TIMEOUT**: 300 → 900 seconds (5 → 15 minutes)
- **PROPOSAL_TIMEOUT**: 300 → 900 seconds (environment variable default)

### 3. **Voice Manager (bot/services/voice_manager.py)**
- **Enhanced move_players_to_teams()**: Better error detection and reporting
- **Detailed logging**: Shows exactly which players failed to move and why
- **Permission handling**: Better handling of permission errors
- **Rate limiting**: Reduced delay between moves (0.5s → 0.3s)

### 4. **UI Updates (bot/utils/embeds.py)**
- **Footer text**: Updated to reflect 15-minute timeout
- **Button labels**: Clarified that it's not voting but simple accept/decline

### 5. **Configuration (.env.example)**
- **PROPOSAL_TIMEOUT**: Updated default from 300 to 900 seconds

## New Behavior

### Team Acceptance Flow:
1. **Team proposal displayed** with Accept/Decline buttons
2. **Any player in the match** can click Accept or Decline
3. **15-minute timeout** for decision making
4. **Immediate processing** when Accept/Decline is clicked (no voting)
5. **Detailed feedback** if player movement fails

### Error Handling:
- **Specific error messages** for different failure types:
  - "Not in voice channel"
  - "Permission denied"
  - "Connection error"
  - "HTTP error"
- **Partial success handling**: Shows how many players moved successfully
- **Manual movement guidance**: Clear instructions when automatic movement fails
- **Match still created**: Even if movement fails, match is recorded for result tracking

### Logging Improvements:
- **Before**: "Error moving players"
- **After**: 
  - "Moving PlayerName from Waiting Room to Team 1"
  - "✅ Successfully moved PlayerName to Team 1"
  - "❌ Permission denied moving PlayerName: Missing Move Members permission"
  - "Movement summary: 3 moved successfully, 1 failed"

## Testing Recommendations

1. **Test with players in voice**: Verify normal movement works
2. **Test with players not in voice**: Check error handling
3. **Test permission issues**: Verify bot has Move Members permission
4. **Test timeout**: Confirm 15-minute timeout works
5. **Test partial failures**: Mix of successful and failed moves

## Bot Permissions Required

Ensure the bot has these permissions in voice channels:
- **Move Members**: Required to move players between channels
- **Manage Channels**: Required to set channel permissions
- **Connect**: Required to access voice channels
- **View Channel**: Required to see voice channels

## Troubleshooting

### Common Issues:
1. **"Permission denied"**: Bot lacks Move Members permission
2. **"Not in voice channel"**: Player left voice before acceptance
3. **"Connection error"**: Discord API rate limiting or network issues
4. **"No voice channel"**: Player's voice state is corrupted

### Solutions:
- Check bot permissions in voice category
- Ensure players stay in Waiting Room until acceptance
- Add delays between operations if rate limited
- Have players rejoin voice if state issues occur
