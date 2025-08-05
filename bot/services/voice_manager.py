import discord
import asyncio
import logging
from typing import List, Optional, Dict
from utils.constants import Config, TEAM_EMOJIS

logger = logging.getLogger(__name__)

class VoiceManager:
    """Voice channel detection and management"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_matches: Dict[int, Dict] = {}  # guild_id -> match_info
    
    async def get_waiting_room_members(self, guild: discord.Guild) -> List[discord.Member]:
        """Get all members in waiting room voice channel"""
        waiting_room = None
        
        # Find waiting room channel
        for channel in guild.voice_channels:
            if channel.name.lower() == Config.WAITING_ROOM_NAME.lower():
                waiting_room = channel
                break
        
        if not waiting_room:
            logger.warning(f"Waiting room not found in guild {guild.name}")
            return []
        
        # Filter out bots
        members = [member for member in waiting_room.members if not member.bot]
        
        logger.info(f"Found {len(members)} members in waiting room: {[m.display_name for m in members]}")
        return members
    
    async def create_team_channels(self, guild: discord.Guild, num_teams: int) -> List[discord.VoiceChannel]:
        """Create temporary team voice channels"""
        created_channels = []
        
        # Find category for team channels (or use waiting room's category)
        category = None
        waiting_room = discord.utils.get(guild.voice_channels, name=Config.WAITING_ROOM_NAME)
        if waiting_room and waiting_room.category:
            category = waiting_room.category
        
        try:
            for i in range(num_teams):
                emoji = TEAM_EMOJIS[i] if i < len(TEAM_EMOJIS) else "🔹"
                channel_name = f"{emoji} {Config.TEAM_CHANNEL_PREFIX} {i+1}"
                
                # Check if channel already exists
                existing_channel = discord.utils.get(guild.voice_channels, name=channel_name)
                if existing_channel:
                    created_channels.append(existing_channel)
                    logger.info(f"Using existing team channel: {channel_name}")
                    continue
                
                # Create new channel
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(connect=False),
                    guild.me: discord.PermissionOverwrite(
                        connect=True,
                        move_members=True,
                        manage_channels=True
                    )
                }
                
                channel = await guild.create_voice_channel(
                    name=channel_name,
                    category=category,
                    overwrites=overwrites,
                    reason="Team balance match"
                )
                
                created_channels.append(channel)
                logger.info(f"Created team channel: {channel_name}")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
        
        except discord.HTTPException as e:
            logger.error(f"Failed to create team channels: {e}")
            # Clean up any channels we managed to create
            for channel in created_channels:
                try:
                    await channel.delete(reason="Cleanup due to error")
                except:
                    pass
            return []
        except Exception as e:
            logger.error(f"Unexpected error creating team channels: {e}")
            return []
        
        return created_channels
    
    async def move_players_to_teams(self, teams: List[List[discord.Member]], team_channels: List[discord.VoiceChannel]):
        """Move players to their assigned team channels"""
        if len(teams) != len(team_channels):
            logger.error("Mismatch between number of teams and channels")
            return False
        
        moved_count = 0
        failed_moves = []
        
        try:
            for team_idx, (team, channel) in enumerate(zip(teams, team_channels)):
                # Allow team members to connect to their channel
                for member in team:
                    await channel.set_permissions(
                        member,
                        connect=True,
                        speak=True,
                        reason=f"Team {team_idx + 1} member"
                    )
                
                # Move members to team channel
                for member in team:
                    try:
                        if member.voice and member.voice.channel:
                            await member.move_to(channel, reason=f"Team {team_idx + 1} assignment")
                            moved_count += 1
                            logger.info(f"Moved {member.display_name} to Team {team_idx + 1}")
                        else:
                            logger.warning(f"{member.display_name} is not in a voice channel")
                            failed_moves.append(member.display_name)
                    except discord.HTTPException as e:
                        logger.error(f"Failed to move {member.display_name}: {e}")
                        failed_moves.append(member.display_name)
                    except Exception as e:
                        logger.error(f"Unexpected error moving {member.display_name}: {e}")
                        failed_moves.append(member.display_name)
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.5)
        
        except Exception as e:
            logger.error(f"Error during player movement: {e}")
            return False
        
        if failed_moves:
            logger.warning(f"Failed to move {len(failed_moves)} players: {failed_moves}")
        
        logger.info(f"Successfully moved {moved_count} players to team channels")
        return moved_count > 0
    
    async def cleanup_team_channels(self, guild: discord.Guild, return_to_waiting: bool = True):
        """Remove temporary team channels and optionally return players to waiting room"""
        waiting_room = None
        if return_to_waiting:
            waiting_room = discord.utils.get(guild.voice_channels, name=Config.WAITING_ROOM_NAME)
        
        team_channels = []
        
        # Find team channels to clean up
        for channel in guild.voice_channels:
            if Config.TEAM_CHANNEL_PREFIX.lower() in channel.name.lower():
                # Check if it looks like a temporary team channel
                for emoji in TEAM_EMOJIS:
                    if emoji in channel.name:
                        team_channels.append(channel)
                        break
        
        if not team_channels:
            logger.info("No team channels found to cleanup")
            return
        
        moved_count = 0
        
        try:
            # Move players back to waiting room
            if return_to_waiting and waiting_room:
                for channel in team_channels:
                    for member in channel.members:
                        try:
                            await member.move_to(waiting_room, reason="Match ended - return to waiting room")
                            moved_count += 1
                            logger.info(f"Returned {member.display_name} to waiting room")
                        except discord.HTTPException as e:
                            logger.error(f"Failed to return {member.display_name} to waiting room: {e}")
                        except Exception as e:
                            logger.error(f"Unexpected error returning {member.display_name}: {e}")
                        
                        # Small delay to avoid rate limits
                        await asyncio.sleep(0.5)
            
            # Wait a moment for moves to complete
            await asyncio.sleep(2)
            
            # Delete team channels
            for channel in team_channels:
                try:
                    await channel.delete(reason="Team balance match ended")
                    logger.info(f"Deleted team channel: {channel.name}")
                except discord.HTTPException as e:
                    logger.error(f"Failed to delete channel {channel.name}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error deleting channel {channel.name}: {e}")
                
                # Small delay to avoid rate limits
                await asyncio.sleep(0.5)
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        logger.info(f"Cleanup completed. Moved {moved_count} players back to waiting room.")
    
    async def setup_voice_channels(self, guild: discord.Guild) -> bool:
        """Initial setup of required voice channels"""
        try:
            # Check if waiting room exists
            waiting_room = discord.utils.get(guild.voice_channels, name=Config.WAITING_ROOM_NAME)
            
            if not waiting_room:
                # Create waiting room
                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(connect=True, speak=True),
                    guild.me: discord.PermissionOverwrite(
                        connect=True,
                        move_members=True,
                        manage_channels=True
                    )
                }
                
                waiting_room = await guild.create_voice_channel(
                    name=Config.WAITING_ROOM_NAME,
                    overwrites=overwrites,
                    reason="Team balance bot setup"
                )
                
                logger.info(f"Created waiting room: {Config.WAITING_ROOM_NAME}")
                return True
            else:
                logger.info("Waiting room already exists")
                return True
                
        except discord.HTTPException as e:
            logger.error(f"Failed to setup voice channels: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error setting up voice channels: {e}")
            return False
    
    def set_active_match(self, guild_id: int, match_info: Dict):
        """Store active match information"""
        self.active_matches[guild_id] = match_info
        logger.info(f"Set active match for guild {guild_id}: {match_info.get('match_id', 'unknown')}")
    
    def get_active_match(self, guild_id: int) -> Optional[Dict]:
        """Get active match information"""
        return self.active_matches.get(guild_id)
    
    def clear_active_match(self, guild_id: int):
        """Clear active match information"""
        if guild_id in self.active_matches:
            del self.active_matches[guild_id]
            logger.info(f"Cleared active match for guild {guild_id}")
    
    async def validate_voice_setup(self, guild: discord.Guild) -> tuple[bool, str]:
        """Validate that voice channels are properly set up"""
        # Check if waiting room exists
        waiting_room = discord.utils.get(guild.voice_channels, name=Config.WAITING_ROOM_NAME)
        
        if not waiting_room:
            return False, f"Waiting room '{Config.WAITING_ROOM_NAME}' not found. Use `/setup` to create it."
        
        # Check bot permissions
        permissions = waiting_room.permissions_for(guild.me)
        
        if not permissions.move_members:
            return False, "Bot needs 'Move Members' permission in voice channels."
        
        if not permissions.manage_channels:
            return False, "Bot needs 'Manage Channels' permission to create team channels."
        
        return True, "Voice setup is valid"