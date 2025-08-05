import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
import asyncio

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
    @app_commands.describe(num_teams="Number of teams to create (default: auto, max: 6)")
    async def create_teams(self, interaction: discord.Interaction, num_teams: Optional[int] = None):
        """Main team balancing functionality with special cases for small player counts"""
        await interaction.response.defer()
        
        try:
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
            
            # Determine number of teams based on player count and special cases
            player_count = len(waiting_members)
            if player_count <= Config.SINGLE_TEAM_THRESHOLD:
                # 1-4 players: Single team
                actual_num_teams = 1
                special_case_msg = f"**Special Case**: {player_count} players - creating single team for practice/warmup"
            elif player_count == Config.TWO_TEAM_THRESHOLD:
                # 5 players: 2 teams (2:3 split)
                actual_num_teams = 2
                special_case_msg = f"**Special Case**: 5 players - splitting into 2 teams (2:3)"
            else:
                # 6+ players: Use specified num_teams or default
                if num_teams is None:
                    actual_num_teams = Config.DEFAULT_NUM_TEAMS
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
                
                # Adjust team count if needed for balanced distribution
                min_teams_needed = max(2, (len(waiting_members) + 4) // 5)  # Rough estimate for balanced teams
                if actual_num_teams < min_teams_needed:
                    actual_num_teams = min_teams_needed
                    logger.info(f"Adjusted team count to {actual_num_teams} for {len(waiting_members)} players")
            
            # Create balanced teams
            teams, team_ratings, balance_score = await self.team_balancer.create_balanced_teams(
                waiting_members, actual_num_teams, interaction.guild.id
            )
            
            # Validate teams
            if not self.team_balancer.validate_teams(teams, waiting_members):
                embed = EmbedTemplates.error_embed(
                    "Team Creation Failed",
                    "Failed to create valid teams. Please try again."
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
            
            # Handle timeout
            await view.wait()
            if view.result_sent:
                return  # Already handled by the view
            
            # Timeout occurred
            embed_timeout = EmbedTemplates.warning_embed(
                "Team Proposal Expired",
                "The team proposal timed out. Use `/create_teams` to generate new teams."
            )
            
            # Clean up
            await self.voice_manager.cleanup_team_channels(interaction.guild, return_to_waiting=False)
            await api_client.cancel_match(match_id)
            
            await interaction.followup.send(embed=embed_timeout)
            
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
    
    @app_commands.command(name="record_result", description="Record match result and update ratings")
    @app_commands.describe(
        winning_team="The team that won (1, 2, 3, etc.) or leave empty for draw",
        result_type="Type of result (win_loss or draw)"
    )
    @app_commands.choices(result_type=[
        app_commands.Choice(name="Win/Loss", value="win_loss"),
        app_commands.Choice(name="Draw", value="draw"),
        app_commands.Choice(name="Cancel", value="cancelled")
    ])
    async def record_result(self, interaction: discord.Interaction, 
                           winning_team: Optional[int] = None,
                           result_type: str = "win_loss"):
        """Record match outcome and update ratings"""
        await interaction.response.defer()
        
        try:
            # Check for active match
            active_match = self.voice_manager.get_active_match(interaction.guild.id)
            if not active_match:
                embed = EmbedTemplates.warning_embed(
                    "No Active Match",
                    "There's no active match to record results for."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            match_id = active_match['match_id']
            teams = active_match['teams']
            
            # Validate winning team if provided
            if result_type == "win_loss":
                if winning_team is None:
                    embed = EmbedTemplates.error_embed(
                        "Missing Winner",
                        "Please specify which team won (1, 2, 3, etc.)"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                if winning_team < 1 or winning_team > len(teams):
                    embed = EmbedTemplates.error_embed(
                        "Invalid Team",
                        f"Team number must be between 1 and {len(teams)}"
                    )
                    await interaction.followup.send(embed=embed, ephemeral=True)
                    return
            
            # Record result in database
            result_data = await api_client.record_match_result(
                match_id=match_id,
                result_type=result_type,
                winning_team=winning_team
            )
            
            if not result_data:
                embed = EmbedTemplates.error_embed(
                    "Database Error",
                    "Failed to record match result. Please try again."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Get updated match data for display
            match_data = await api_client.get_match(match_id)
            
            # Create result embed
            if result_type == "win_loss" and winning_team:
                title = f"🏆 Team {winning_team} Wins!"
                description = f"Congratulations to Team {winning_team}! Ratings have been updated."
                color = Config.SUCCESS_COLOR
            elif result_type == "draw":
                title = "🤝 Match Draw"
                description = "The match ended in a draw. Ratings have been updated."
                color = Config.WARNING_COLOR
            else:
                title = "❌ Match Cancelled"
                description = "The match was cancelled. No rating changes applied."
                color = Config.ERROR_COLOR
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=color
            )
            
            # Add team information
            for i, team in enumerate(teams):
                team_names = [player['username'] for player in team]
                team_result = ""
                
                if result_type == "win_loss" and winning_team:
                    if i + 1 == winning_team:
                        team_result = " 🏆"
                    else:
                        team_result = " 💔"
                elif result_type == "draw":
                    team_result = " 🤝"
                
                embed.add_field(
                    name=f"Team {i+1}{team_result}",
                    value="\n".join([f"• {name}" for name in team_names]),
                    inline=True
                )
            
            embed.set_footer(text="Match completed! Players can return to the waiting room.")
            
            await interaction.followup.send(embed=embed)
            
            # Clean up voice channels and return players to waiting room
            await asyncio.sleep(2)  # Give people time to see the result
            await self.voice_manager.cleanup_team_channels(interaction.guild, return_to_waiting=True)
            
            # Clear active match
            self.voice_manager.clear_active_match(interaction.guild.id)
            
            logger.info(f"Match {match_id} completed with result: {result_type}, winner: {winning_team}")
            
        except Exception as e:
            logger.error(f"Error in record_result command: {e}")
            embed = EmbedTemplates.error_embed(
                "Result Recording Error",
                "An error occurred while recording the match result. Please try again."
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