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

logger = logging.getLogger(__name__)

class TeamCommands(commands.Cog):
    """Team creation and management commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.voice_manager = VoiceManager(bot)
        self.team_balancer = TeamBalancer()
    
    @app_commands.command(name="create_teams", description="Create balanced teams from waiting room")
    @app_commands.describe(
        num_teams="Number of teams to create (default: auto, max: 6)",
        region="Require a player from this region in each team (CA, TX, NY, KR, NA, EU)",
        format="Custom team sizes (e.g., '3:3:4' for teams of 3, 3, and 4 players)"
    )
    async def create_teams(self, interaction: discord.Interaction, 
                          num_teams: Optional[int] = None, 
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
                    
                    # Check if num_teams conflicts with format
                    if num_teams is not None and num_teams != len(custom_team_sizes):
                        embed = EmbedTemplates.error_embed(
                            "Conflicting Parameters",
                            f"Format specifies {len(custom_team_sizes)} teams but num_teams is {num_teams}. Use only one parameter."
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
            team_adjustment_msg = None  # Initialize for later use
            
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
                # 6+ players: Use specified num_teams or calculate optimal default
                if num_teams is None:
                    # Calculate optimal team count: prioritize fewer teams with more players
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
                else:
                    actual_num_teams = num_teams
                special_case_msg = None
                
                # Validate num_teams for normal cases
                if actual_num_teams < 2:
                    embed = EmbedTemplates.error_embed(
                        "Invalid Team Count",
                        "Need at least 2 teams for balanced matches!"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                if actual_num_teams > 6:
                    embed = EmbedTemplates.error_embed(
                        "Too Many Teams",
                        "Maximum 6 teams allowed!"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                # Adjust team count to ensure minimum players per team
                # Calculate maximum teams possible with minimum players per team
                max_teams_possible = player_count // Config.MIN_PLAYERS_PER_TEAM
                original_num_teams = actual_num_teams
                
                # If user specified num_teams, validate it doesn't create teams too small
                if actual_num_teams > max_teams_possible:
                    actual_num_teams = max_teams_possible
                    logger.info(f"Adjusted team count from {original_num_teams} to {actual_num_teams} to ensure minimum {Config.MIN_PLAYERS_PER_TEAM} players per team")
                
                # Ensure we have at least 2 teams for 6+ players
                if actual_num_teams < 2:
                    actual_num_teams = 2
                
                # Create adjustment message if teams were changed
                team_adjustment_msg = None
                if num_teams is not None and actual_num_teams != original_num_teams:
                    avg_players = player_count / actual_num_teams
                    team_adjustment_msg = f"**Team count adjusted:** {original_num_teams} → {actual_num_teams} teams\n**Reason:** Ensures minimum {Config.MIN_PLAYERS_PER_TEAM} players per team ({avg_players:.1f} avg)"
            
            # Check if region requirement can be met
            if region:
                # Get user data to check regions
                players_with_ratings = await self.team_balancer._get_player_ratings(
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
                teams, team_ratings, balance_score = await self.team_balancer.create_teams_with_custom_sizes(
                    waiting_members, custom_team_sizes, interaction.guild.id, required_region=region
                )
            else:
                # Use standard balancing
                teams, team_ratings, balance_score = await self.team_balancer.create_balanced_teams(
                    waiting_members, actual_num_teams, interaction.guild.id, required_region=region
                )
            
            # Validate teams
            if not self.team_balancer.validate_teams(teams, waiting_members):
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
            
            # Create team voice channels
            team_channels = await self.voice_manager.create_team_channels(interaction.guild, actual_num_teams)
            
            if len(team_channels) != actual_num_teams:
                embed = EmbedTemplates.error_embed(
                    "Channel Creation Failed",
                    "Failed to create team voice channels. Please check bot permissions."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create match in database
            match_data = await api_client.create_match(
                guild_id=interaction.guild.id,
                created_by=interaction.user.id,
                total_teams=actual_num_teams
            )
            
            if not match_data:
                # Clean up channels if match creation failed
                await self.voice_manager.cleanup_team_channels(interaction.guild, return_to_waiting=False)
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
            
            # Add team adjustment message if applicable
            if team_adjustment_msg:
                embed.insert_field_at(0, name="⚖️ Team Count Adjusted", value=team_adjustment_msg, inline=False)
            
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
                team_channels=team_channels,
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
                color=Config.EMBED_COLOR,
                timestamp=datetime.utcnow()
            )
            
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

async def setup(bot):
    await bot.add_cog(TeamCommands(bot))