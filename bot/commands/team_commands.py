import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
import asyncio
from datetime import datetime

from services.api_client import api_client
from services.voice_manager import VoiceManager
from services.team_balancer import TeamBalancer
from utils.embeds import EmbedTemplates
from utils.views import TeamProposalView
from utils.constants import Config
from utils.version import get_bot_footer_text

logger = logging.getLogger(__name__)

class TeamCommands(commands.Cog):
    """Team creation and management commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.voice_manager = VoiceManager(bot)
        # Don't create team balancer here - create fresh instance each time
    
    @app_commands.command(name="create_teams", description="Create balanced teams from waiting room")
    @app_commands.describe(
        np="New Partners mode - prioritize players who haven't played together often",
        region="Require a player from this region in each team (CA, TX, NY, KR, NA, EU)",
        format="Custom team sizes (e.g., '3:3:4' for teams of 3, 3, and 4 players)"
    )
    async def create_teams(self, interaction: discord.Interaction, 
                          np: Optional[bool] = False, 
                          region: Optional[str] = None,
                          format: Optional[str] = None):
        """Main team balancing functionality with special cases for small player counts and region requirements"""
        await interaction.response.defer()
        
        try:
            # Validate region parameter if provided
            if region:
                region = region.upper()
                if region not in Config.VALID_REGIONS:
                    embed = EmbedTemplates.error_embed(
                        "Invalid Region",
                        f"Valid regions are: {', '.join(Config.VALID_REGIONS)}"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            # Parse and validate format parameter if provided
            custom_team_sizes = None
            if format:
                try:
                    # Parse format like "3:3:4" into [3, 3, 4]
                    custom_team_sizes = [int(x.strip()) for x in format.split(':')]
                    
                    # Validate format
                    if len(custom_team_sizes) > 6:
                        embed = EmbedTemplates.error_embed(
                            "Too Many Teams",
                            "Maximum 6 teams allowed in custom format."
                        )
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return
                    
                    if len(custom_team_sizes) < 2:
                        embed = EmbedTemplates.error_embed(
                            "Invalid Format",
                            "Need at least 2 teams. Example: `3:3` or `3:3:4`"
                        )
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return
                    
                    if any(size < 1 for size in custom_team_sizes):
                        embed = EmbedTemplates.error_embed(
                            "Invalid Team Size",
                            "All team sizes must be at least 1 player."
                        )
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return
                    
                    if any(size > 8 for size in custom_team_sizes):
                        embed = EmbedTemplates.error_embed(
                            "Team Too Large",
                            "Maximum 8 players per team."
                        )
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        return
                    
                    
                except ValueError:
                    embed = EmbedTemplates.error_embed(
                        "Invalid Format",
                        "Format must be numbers separated by colons. Example: `3:3:4`"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            # Check if there's already an active match
            active_match = self.voice_manager.get_active_match(interaction.guild.id)
            if active_match:
                embed = EmbedTemplates.warning_embed(
                    "Match Already Active",
                    f"There's already an active match in this guild. Use `/cancel_match` to cancel it first."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Validate voice setup
            is_valid, error_msg = await self.voice_manager.validate_voice_setup(interaction.guild)
            if not is_valid:
                embed = EmbedTemplates.error_embed("Voice Setup Issue", error_msg)
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Get players from waiting room
            waiting_members = await self.voice_manager.get_waiting_room_members(interaction.guild)
            
            if len(waiting_members) < Config.MIN_PLAYERS_FOR_TEAMS:
                embed = EmbedTemplates.warning_embed(
                    "Not Enough Players",
                    f"Need at least {Config.MIN_PLAYERS_FOR_TEAMS} player in the waiting room to create teams.\n"
                    f"Currently have {len(waiting_members)} players."
                )
                await interaction.followup.send(embed=embed)
                return
            
            if len(waiting_members) > Config.MAX_PLAYERS_PER_MATCH:
                embed = EmbedTemplates.warning_embed(
                    "Too Many Players",
                    f"Maximum {Config.MAX_PLAYERS_PER_MATCH} players per match.\n"
                    f"Currently have {len(waiting_members)} players in waiting room."
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Validate custom format against actual player count
            if custom_team_sizes:
                required_players = sum(custom_team_sizes)
                actual_players = len(waiting_members)
                
                if required_players != actual_players:
                    embed = EmbedTemplates.error_embed(
                        "Player Count Mismatch",
                        f"Format `{format}` requires {required_players} players but there are {actual_players} players in the waiting room.\n"
                        f"Either adjust the format or change the number of players."
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            # Determine number of teams based on custom format or player count
            player_count = len(waiting_members)
            
            if custom_team_sizes:
                # Use custom format
                actual_num_teams = len(custom_team_sizes)
                format_display = ':'.join(map(str, custom_team_sizes))
                special_case_msg = f"**Custom Format**: {format_display} - creating teams with specified sizes"
            elif player_count <= Config.SINGLE_TEAM_THRESHOLD:
                # 1-4 players: Single team
                actual_num_teams = 1
                special_case_msg = f"**Special Case**: {player_count} players - creating single team for practice/warmup"
            elif player_count == Config.TWO_TEAM_THRESHOLD:
                # 5 players: 2 teams (2:3 split)
                actual_num_teams = 2
                special_case_msg = f"**Special Case**: 5 players - splitting into 2 teams (2:3)"
            else:
                # 6+ players: Calculate optimal team count automatically
                # Aim for 4-5 players per team, minimum 3 players per team
                if player_count <= 8:
                    actual_num_teams = 2  # 6-8 players: 2 teams (3-4 players each)
                elif player_count <= 12:
                    actual_num_teams = 3  # 9-12 players: 3 teams (3-4 players each)
                elif player_count <= 16:
                    actual_num_teams = 4  # 13-16 players: 4 teams (3-4 players each)
                elif player_count <= 20:
                    actual_num_teams = 5  # 17-20 players: 5 teams (3-4 players each)
                else:
                    actual_num_teams = 6  # 21+ players: 6 teams (3+ players each)
                
                # Add NP mode notification
                if np:
                    special_case_msg = f"**New Partners Mode**: Minimizing repeated partnerships among {player_count} players"
                else:
                    special_case_msg = None
                
                # Ensure teams are valid (automatic calculation should always be valid)
                if actual_num_teams < 2:
                    actual_num_teams = 2
                elif actual_num_teams > 6:
                    actual_num_teams = 6
                
                # Adjust if too many teams for player count (safety check)
                max_teams_possible = player_count // Config.MIN_PLAYERS_PER_TEAM
                if actual_num_teams > max_teams_possible:
                    actual_num_teams = max_teams_possible
                    logger.info(f"Auto-adjusted team count to {actual_num_teams} to ensure minimum {Config.MIN_PLAYERS_PER_TEAM} players per team")
            
            # Create fresh team balancer instance for each team creation
            team_balancer = TeamBalancer()
            
            # Check if region requirement can be met
            if region:
                # Get user data to check regions
                players_with_ratings = await team_balancer._get_player_ratings(
                    waiting_members, interaction.guild.id
                )
                
                # Count players from the required region
                region_players = [p for p in players_with_ratings if p.get('region_code') == region]
                
                if not region_players:
                    embed = EmbedTemplates.warning_embed(
                        "No Regional Players",
                        f"No players from region **{region}** found in the waiting room.\n"
                        f"Region requirement cannot be satisfied."
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # Check if we have enough regional players for the number of teams
                if actual_num_teams and len(region_players) < actual_num_teams:
                    embed = EmbedTemplates.warning_embed(
                        "Insufficient Regional Players",
                        f"Only **{len(region_players)}** players from region **{region}** found, but **{actual_num_teams}** teams requested.\n"
                        f"Need at least one **{region}** player per team.\n\n"
                        f"Try reducing the number of teams or removing the region requirement."
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            # Create balanced teams
            if custom_team_sizes:
                # Use custom format
                teams, team_ratings, balance_score = await team_balancer.create_teams_with_custom_sizes(
                    waiting_members, custom_team_sizes, interaction.guild.id, required_region=region
                )
            else:
                # Use standard balancing with optional NP mode
                teams, team_ratings, balance_score = await team_balancer.create_balanced_teams(
                    waiting_members, actual_num_teams, interaction.guild.id, required_region=region, np_mode=np
                )
            
            # Validate teams
            if not team_balancer.validate_teams(teams, waiting_members):
                embed = EmbedTemplates.error_embed(
                    "Team Creation Failed",
                    "Failed to create valid teams. Please try again."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Check region requirement after team creation
            if region:
                teams_without_region = []
                for i, team in enumerate(teams):
                    team_has_region = any(p.get('region_code') == region for p in team)
                    if not team_has_region:
                        teams_without_region.append(i + 1)
                
                if teams_without_region:
                    embed = EmbedTemplates.warning_embed(
                        "Region Requirement Not Met",
                        f"Could not place a **{region}** player in team(s): {', '.join(map(str, teams_without_region))}.\n"
                        f"Not enough **{region}** players for the number of teams requested.\n\n"
                        f"Try reducing the number of teams or removing the region requirement."
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            # Voice channels will be created when "Create Team" button is clicked
            
            # Create match in database
            match_data = await api_client.create_match(
                guild_id=interaction.guild.id,
                created_by=interaction.user.id,
                total_teams=actual_num_teams
            )
            
            if not match_data:
                embed = EmbedTemplates.error_embed(
                    "Database Error",
                    "Failed to create match in database. Please try again."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            match_id = match_data['match_id']
            logger.info(f"Created match {match_id} with {actual_num_teams} teams")
            
            # Add players to match in database
            for team_idx, team in enumerate(teams):
                for player in team:
                    await api_client.add_player_to_match(
                        match_id=match_id,
                        user_id=player['user_id'],
                        guild_id=interaction.guild.id,
                        team_number=team_idx + 1
                    )
            
            # Create team proposal embed
            embed = EmbedTemplates.team_proposal_embed(teams, team_ratings, balance_score)
            
            # Add special case message if applicable
            if special_case_msg:
                embed.insert_field_at(0, name="ℹ️ Special Configuration", value=special_case_msg, inline=False)
            
            
            # Add match info
            balance_text = 'Excellent' if balance_score < 50 else 'Good' if balance_score < 100 else 'Fair'
            if actual_num_teams == 1:
                balance_text = 'Single Team'  # No balance score for single team
            
            embed.add_field(
                name="📊 Match Info",
                value=f"**Players:** {len(waiting_members)}\n**Teams:** {actual_num_teams}\n**Balance:** {balance_text}",
                inline=True
            )
            
            # Create interactive view
            view = TeamProposalView(
                teams=teams,
                num_teams=actual_num_teams,
                match_id=match_id,
                voice_manager=self.voice_manager
            )
            
            await interaction.followup.send(embed=embed, view=view)
            
            # No timeout handling needed - buttons stay active until clicked
            
        except ValueError as e:
            embed = EmbedTemplates.error_embed("Invalid Input", str(e))
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in create_teams command: {e}")
            embed = EmbedTemplates.error_embed(
                "Team Creation Error",
                "An error occurred while creating teams. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="record_result", description="Record match result using placement-based system")
    async def record_result(self, interaction: discord.Interaction):
        """Record match outcome using placement-based system"""
        await interaction.response.defer()
        
        try:
            # Check for active match
            active_match = self.voice_manager.get_active_match(interaction.guild.id)
            if not active_match:
                embed = EmbedTemplates.warning_embed(
                    "No Active Match",
                    "There's no active match to record results for. Use `/create_teams` to start a new match."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            match_id = active_match['match_id']
            teams = active_match['teams']
            
            # Create placement-based result recording view
            from utils.views import PlacementResultView
            view = PlacementResultView(
                teams=teams,
                match_id=match_id,
                voice_manager=self.voice_manager
            )
            
            # Create initial embed explaining the new system
            embed = discord.Embed(
                title="🏆 Record Match Results (Placement-Based)",
                description=f"**New System**: Results are now based on team placements, not simple win/loss!\n\n"
                           f"**Teams in Match**: {len(teams)}\n"
                           f"**Rating System**: Rank 7 = 1500 baseline (no change)\n"
                           f"**Range**: +25 (1st place) to -40 (30th+ place)",
                color=Config.EMBED_COLOR
            )
            embed.set_footer(text=get_bot_footer_text())
            
            # Show teams
            team_list = []
            for i, team in enumerate(teams):
                team_names = [player['username'] for player in team]
                team_display = ', '.join(team_names[:3])
                if len(team_names) > 3:
                    team_display += f" (+{len(team_names)-3} more)"
                team_list.append(f"**Team {i+1}**: {team_display}")
            
            embed.add_field(
                name="👥 Teams",
                value="\n".join(team_list),
                inline=False
            )
            
            # Show rating examples for this match
            embed.add_field(
                name="📊 Rating Changes for This Match",
                value=f"🥇 **1st Place**: +{view.calculate_rating_change(1):.1f} rating\n"
                      f"🥈 **2nd Place**: +{view.calculate_rating_change(2):.1f} rating\n" +
                      (f"🥉 **3rd Place**: +{view.calculate_rating_change(3):.1f} rating\n" if len(teams) >= 3 else "") +
                      (f"📊 **{len(teams)}th Place**: {view.calculate_rating_change(len(teams)):+.1f} rating" if len(teams) > 3 else ""),
                inline=False
            )
            
            embed.add_field(
                name="📝 Instructions",
                value="1. Click each team's button to set their placement\n"
                      "2. Enter 1 for 1st place, 2 for 2nd place, etc.\n"
                      "3. **Guild matches**: Use consecutive ranks (1, 2, 3...)\n"
                      "4. **External competitions**: Use actual ranks (1-30)\n"
                      "5. Click 'Finalize Results' when all placements are set",
                inline=False
            )
            
            embed.set_footer(text="Use /rating_scale to see the full rating system")
            
            await interaction.followup.send(embed=embed, view=view)
            
            # Wait for results to be submitted
            await view.wait()
            
            # If results were submitted, clean up
            if view.result_sent:
                # Clean up voice channels and return players to waiting room
                await asyncio.sleep(2)  # Give people time to see the result
                await self.voice_manager.cleanup_team_channels(interaction.guild, return_to_waiting=True)
                
                # Clear active match
                self.voice_manager.clear_active_match(interaction.guild.id)
            else:
                # Timeout occurred
                embed_timeout = EmbedTemplates.warning_embed(
                    "Result Recording Timeout",
                    "The result recording dialogue timed out. Use `/record_result` to try again."
                )
                await interaction.followup.send(embed=embed_timeout, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in record_result command: {e}")
            embed = EmbedTemplates.error_embed(
                "Result Recording Error",
                "An error occurred while setting up result recording. Please try again."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="cancel_match", description="Cancel the current match")
    async def cancel_match(self, interaction: discord.Interaction):
        """Cancel active match"""
        await interaction.response.defer()
        
        try:
            # Check for active match
            active_match = self.voice_manager.get_active_match(interaction.guild.id)
            if not active_match:
                embed = EmbedTemplates.warning_embed(
                    "No Active Match",
                    "There's no active match to cancel."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            match_id = active_match['match_id']
            
            # Cancel match in database
            await api_client.cancel_match(match_id)
            
            # Clean up voice channels and return players to waiting room
            await self.voice_manager.cleanup_team_channels(interaction.guild, return_to_waiting=True)
            
            # Clear active match
            self.voice_manager.clear_active_match(interaction.guild.id)
            
            embed = EmbedTemplates.success_embed(
                "Match Cancelled",
                "The active match has been cancelled and players have been returned to the waiting room."
            )
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Match {match_id} cancelled by {interaction.user.display_name}")
            
        except Exception as e:
            logger.error(f"Error in cancel_match command: {e}")
            embed = EmbedTemplates.error_embed(
                "Cancellation Error",
                "An error occurred while cancelling the match. Please try again."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="cleanup", description="Clean up team voice channels and return players to waiting room")
    async def cleanup(self, interaction: discord.Interaction):
        """Clean up team channels - available to all users"""
        await interaction.response.defer()
        
        try:
            # Find existing team channels
            team_channels = []
            for channel in interaction.guild.voice_channels:
                if Config.TEAM_CHANNEL_PREFIX.lower() in channel.name.lower():
                    team_channels.append(channel)
            
            if not team_channels:
                embed = EmbedTemplates.success_embed(
                    "No Cleanup Needed",
                    "No team channels found to clean up."
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Count players in team channels
            players_in_teams = 0
            for channel in team_channels:
                players_in_teams += len([m for m in channel.members if not m.bot])
            
            # Perform cleanup - return players to waiting room
            await self.voice_manager.cleanup_team_channels(interaction.guild, return_to_waiting=True)
            
            # Clear any active match
            self.voice_manager.clear_active_match(interaction.guild.id)
            
            embed = EmbedTemplates.success_embed(
                "Cleanup Complete",
                f"✅ Cleaned up {len(team_channels)} team channel{'s' if len(team_channels) != 1 else ''}.\n"
                f"✅ Returned {players_in_teams} player{'s' if players_in_teams != 1 else ''} to waiting room.\n"
                f"✅ Cleared active match data."
            )
            await interaction.followup.send(embed=embed)
            
            logger.info(f"Cleanup performed by {interaction.user.display_name} in guild {interaction.guild.id}")
            
        except Exception as e:
            logger.error(f"Error in cleanup command: {e}")
            embed = EmbedTemplates.error_embed(
                "Cleanup Error",
                "An error occurred during cleanup. Please try again or contact an administrator."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="update_team", description="Update team memberships based on current voice channels")
    @app_commands.default_permissions(manage_channels=True)
    async def update_team(self, interaction: discord.Interaction):
        """Update team memberships to match current voice channel occupancy"""
        await interaction.response.defer()
        
        try:
            # Check for active match
            active_match = self.voice_manager.get_active_match(interaction.guild.id)
            if not active_match:
                embed = EmbedTemplates.warning_embed(
                    "No Active Match",
                    "There's no active match to update. Use `/create_teams` to start a new match."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            match_id = active_match['match_id']
            team_channels = active_match['team_channels']
            
            # Get current database teams
            db_teams = await api_client.get_match_teams(match_id)
            if not db_teams:
                embed = EmbedTemplates.error_embed(
                    "Database Error",
                    "Failed to retrieve current match teams from database."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Scan current voice channel memberships
            current_voice_teams = {}
            for i, channel in enumerate(team_channels, 1):
                current_voice_teams[i] = [
                    member for member in channel.members 
                    if not member.bot  # Exclude bots
                ]
            
            # Build sets for comparison
            db_player_ids = set()
            db_player_teams = {}  # player_id -> team_number
            for team_num_str, players in db_teams.items():
                team_num = int(team_num_str)  # Convert string key to int
                for player in players:
                    player_id = player['user_id']
                    db_player_ids.add(player_id)
                    db_player_teams[player_id] = team_num
            
            voice_player_ids = set()
            voice_player_teams = {}  # player_id -> team_number
            for team_num, members in current_voice_teams.items():
                for member in members:
                    voice_player_ids.add(member.id)
                    voice_player_teams[member.id] = team_num
            
            # Track changes
            changes = {
                'added': [],      # New players
                'removed': [],    # Players who left
                'moved': [],      # Players who changed teams
                'unchanged': []   # Players in same team
            }
            
            # Process changes
            for player_id in voice_player_ids:
                if player_id not in db_player_ids:
                    # New player - need to add to match
                    member = discord.utils.get(interaction.guild.members, id=player_id)
                    if member:
                        team_num = voice_player_teams[player_id]
                        try:
                            await api_client.add_player_to_match(
                                match_id=match_id,
                                user_id=player_id,
                                guild_id=interaction.guild.id,
                                team_number=team_num
                            )
                            changes['added'].append({
                                'username': member.display_name,
                                'team': team_num
                            })
                        except Exception as e:
                            logger.error(f"Failed to add player {member.display_name} to match: {e}")
                elif voice_player_teams[player_id] != db_player_teams[player_id]:
                    # Player moved teams
                    member = discord.utils.get(interaction.guild.members, id=player_id)
                    if member:
                        old_team = db_player_teams[player_id]
                        new_team = voice_player_teams[player_id]
                        try:
                            await api_client.update_player_team_assignment(
                                match_id=match_id,
                                user_id=player_id,
                                guild_id=interaction.guild.id,
                                new_team_number=new_team
                            )
                            changes['moved'].append({
                                'username': member.display_name,
                                'from_team': old_team,
                                'to_team': new_team
                            })
                        except Exception as e:
                            logger.error(f"Failed to move player {member.display_name} to team {new_team}: {e}")
                else:
                    # Player unchanged
                    member = discord.utils.get(interaction.guild.members, id=player_id)
                    if member:
                        changes['unchanged'].append({
                            'username': member.display_name,
                            'team': voice_player_teams[player_id]
                        })
            
            # Handle removed players
            for player_id in db_player_ids:
                if player_id not in voice_player_ids:
                    # Player left - remove from match
                    member = discord.utils.get(interaction.guild.members, id=player_id)
                    username = member.display_name if member else f"User {player_id}"
                    old_team = db_player_teams[player_id]
                    try:
                        await api_client.remove_player_from_match(
                            match_id=match_id,
                            user_id=player_id,
                            guild_id=interaction.guild.id
                        )
                        changes['removed'].append({
                            'username': username,
                            'team': old_team
                        })
                    except Exception as e:
                        logger.error(f"Failed to remove player {username} from match: {e}")
            
            # Update in-memory active match data
            if changes['added'] or changes['removed'] or changes['moved']:
                # Rebuild teams data for active match
                new_teams = []
                for team_num, members in current_voice_teams.items():
                    team_data = []
                    for member in members:
                        # Get player ratings for team balancer format
                        try:
                            user_data = await api_client.get_user(interaction.guild.id, member.id)
                            if user_data:
                                player_data = {
                                    'user_id': member.id,
                                    'username': member.display_name,
                                    'rating_mu': user_data['rating_mu'],
                                    'rating_sigma': user_data['rating_sigma'],
                                    'discord_member': member
                                }
                                team_data.append(player_data)
                        except Exception as e:
                            logger.error(f"Failed to get user data for {member.display_name}: {e}")
                    
                    new_teams.append(team_data)
                
                # Update active match in voice manager
                active_match['teams'] = new_teams
                self.voice_manager.set_active_match(interaction.guild.id, active_match)
            
            # Create summary embed
            embed = discord.Embed(
                title="🔄 Team Update Complete",
                description="Team memberships have been updated based on current voice channels.",
                color=Config.EMBED_COLOR
            )
            embed.set_footer(text=get_bot_footer_text())
            
            # Add changes summary
            if changes['added']:
                added_text = '\n'.join([f"• {p['username']} → Team {p['team']}" for p in changes['added']])
                embed.add_field(name="➕ Added Players", value=added_text, inline=False)
            
            if changes['removed']:
                removed_text = '\n'.join([f"• {p['username']} (was Team {p['team']})" for p in changes['removed']])
                embed.add_field(name="➖ Removed Players", value=removed_text, inline=False)
            
            if changes['moved']:
                moved_text = '\n'.join([f"• {p['username']}: Team {p['from_team']} → Team {p['to_team']}" for p in changes['moved']])
                embed.add_field(name="↔️ Moved Players", value=moved_text, inline=False)
            
            if changes['unchanged']:
                unchanged_count = len(changes['unchanged'])
                embed.add_field(name="✅ Unchanged", value=f"{unchanged_count} players remained in their teams", inline=False)
            
            # Show current team summary
            team_summary = []
            for team_num, members in current_voice_teams.items():
                if members:
                    member_names = [m.display_name for m in members]
                    team_summary.append(f"**Team {team_num}**: {', '.join(member_names)}")
            
            if team_summary:
                embed.add_field(name="👥 Current Teams", value='\n'.join(team_summary), inline=False)
            
            # Add note about what this affects
            embed.add_field(
                name="📝 Note", 
                value="These changes will be reflected when `/record_result` is used.", 
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
            # Log the changes
            total_changes = len(changes['added']) + len(changes['removed']) + len(changes['moved'])
            logger.info(f"Team update completed by {interaction.user.display_name}: {total_changes} changes made")
            
        except Exception as e:
            logger.error(f"Error in update_team command: {e}")
            embed = EmbedTemplates.error_embed(
                "Update Error",
                "An error occurred while updating team memberships. Please try again."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(TeamCommands(bot))