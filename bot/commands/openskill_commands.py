"""
OpenSkill Commands
Discord bot commands for OpenSkill parallel rating system
"""

import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from services.api_client import api_client
from utils.embeds import EmbedTemplates
from utils.constants import Config
from utils.version import get_bot_footer_text

logger = logging.getLogger(__name__)

class OpenSkillCommands(commands.Cog):
    """OpenSkill rating system commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="openskill_stats", description="Show OpenSkill ratings and statistics")
    @app_commands.describe(user="The user to show OpenSkill stats for (defaults to yourself)")
    async def openskill_stats(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Show OpenSkill statistics for a user"""
        await interaction.response.defer(ephemeral=True)
        
        target_user = user or interaction.user
        
        try:
            # Get OpenSkill rating
            openskill_data = await api_client.get_openskill_rating(interaction.guild.id, target_user.id)
            
            if not openskill_data:
                embed = EmbedTemplates.warning_embed(
                    "No OpenSkill Data",
                    f"{target_user.display_name} hasn't played any matches with OpenSkill tracking yet."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Get OpenSkill match history
            history = await api_client.get_openskill_history(interaction.guild.id, target_user.id, limit=5)
            
            # Create stats embed
            embed = discord.Embed(
                title=f"🎯 OpenSkill Statistics - {target_user.display_name}",
                color=Config.EMBED_COLOR
            )
            
            # Basic stats
            display_rating = openskill_data.get('display_rating', 1500)
            mu = openskill_data.get('mu', 25.0)
            sigma = openskill_data.get('sigma', 8.333)
            ordinal = openskill_data.get('ordinal', 0)
            games_played = openskill_data.get('games_played', 0)
            
            embed.add_field(
                name="📊 OpenSkill Rating",
                value=f"**Display Rating:** {display_rating:.0f}\n"
                      f"**Skill (μ):** {mu:.1f}\n"
                      f"**Uncertainty (σ):** {sigma:.1f}\n"
                      f"**Conservative:** {ordinal:.0f}",
                inline=True
            )
            
            embed.add_field(
                name="🎮 Games Played",
                value=f"**Total:** {games_played}",
                inline=True
            )
            
            embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer
            
            # Recent match history
            if history:
                history_text = []
                for match in history[:5]:
                    rating_change = match.get('rating_change', 0)
                    placement = match.get('team_placement', 0)
                    comp_type = match.get('competition_type', 'unknown')
                    total_competitors = match.get('total_competitors', 0)
                    
                    # Format rating change
                    if rating_change > 0:
                        change_str = f"+{rating_change:.1f}"
                        icon = "📈"
                    elif rating_change < 0:
                        change_str = f"{rating_change:.1f}"
                        icon = "📉"
                    else:
                        change_str = "±0.0"
                        icon = "➖"
                    
                    # Format competition info
                    if comp_type == "guild_only":
                        comp_str = f"{placement}/{total_competitors} (Guild)"
                    else:
                        comp_str = f"{placement}/{total_competitors} (External)"
                    
                    history_text.append(f"{icon} {comp_str}: {change_str}")
                
                embed.add_field(
                    name="📋 Recent Matches",
                    value="\n".join(history_text),
                    inline=False
                )
            
            # System info
            embed.add_field(
                name="ℹ️ About OpenSkill",
                value="OpenSkill is a team-based rating system that considers team composition "
                      "and handles multi-team competitions better than individual ratings.",
                inline=False
            )
            
            embed.set_footer(text=f"OpenSkill Parallel System • {get_bot_footer_text()}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in openskill_stats command: {e}")
            embed = EmbedTemplates.error_embed(
                "OpenSkill Stats Error",
                "Failed to retrieve OpenSkill statistics. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="openskill_leaderboard", description="Show OpenSkill leaderboard")
    @app_commands.describe(limit="Number of players to show (default: 10, max: 25)")
    async def openskill_leaderboard(self, interaction: discord.Interaction, limit: Optional[int] = 10):
        """Show OpenSkill leaderboard for the guild"""
        await interaction.response.defer()
        
        # Validate limit
        if limit < 1 or limit > 25:
            limit = 10
        
        try:
            # Get OpenSkill leaderboard
            leaderboard = await api_client.get_openskill_leaderboard(interaction.guild.id, limit)
            
            if not leaderboard:
                embed = EmbedTemplates.warning_embed(
                    "No OpenSkill Data",
                    "No players have OpenSkill ratings yet. Play some matches to generate ratings!"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create leaderboard embed
            embed = discord.Embed(
                title=f"🏆 OpenSkill Leaderboard - {interaction.guild.name}",
                description=f"Top {len(leaderboard)} players by OpenSkill rating",
                color=Config.EMBED_COLOR
            )
            
            leaderboard_text = []
            for i, player in enumerate(leaderboard, 1):
                display_rating = player.get('display_rating', 1500)
                mu = player.get('mu', 25.0)
                sigma = player.get('sigma', 8.333)
                games_played = player.get('games_played', 0)
                user_id = player.get('user_id')
                
                # Try to get Discord member for display name
                try:
                    member = interaction.guild.get_member(user_id)
                    display_name = member.display_name if member else f"User {user_id}"
                except:
                    display_name = f"User {user_id}"
                
                # Format entry
                if i <= 3:
                    medals = ["🥇", "🥈", "🥉"]
                    medal = medals[i-1]
                else:
                    medal = f"{i:2d}."
                
                leaderboard_text.append(
                    f"{medal} **{display_name}** - {display_rating:.0f} "
                    f"({mu:.1f}±{sigma:.1f}) - {games_played} games"
                )
            
            embed.add_field(
                name="Rankings",
                value="\n".join(leaderboard_text),
                inline=False
            )
            
            embed.add_field(
                name="📊 Rating Format",
                value="**Display Rating** (Skill±Uncertainty) - Games Played\n"
                      "Higher skill and lower uncertainty = better rating",
                inline=False
            )
            
            embed.set_footer(text=f"OpenSkill Parallel System • {get_bot_footer_text()}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in openskill_leaderboard command: {e}")
            embed = EmbedTemplates.error_embed(
                "OpenSkill Leaderboard Error",
                "Failed to retrieve OpenSkill leaderboard. Please try again later."
            )
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="rating_comparison", description="Compare OpenSkill and Placement rating systems")
    @app_commands.describe(user="The user to compare ratings for (defaults to yourself)")
    async def rating_comparison(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Compare both rating systems for a user"""
        await interaction.response.defer(ephemeral=True)
        
        target_user = user or interaction.user
        
        try:
            # Get both rating systems
            placement_data = await api_client.get_user(interaction.guild.id, target_user.id)
            openskill_data = await api_client.get_openskill_rating(interaction.guild.id, target_user.id)
            
            if not placement_data:
                embed = EmbedTemplates.warning_embed(
                    "User Not Found",
                    f"{target_user.display_name} is not registered in the system."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create comparison embed
            embed = discord.Embed(
                title=f"⚖️ Rating System Comparison - {target_user.display_name}",
                color=Config.EMBED_COLOR
            )
            
            # Placement system stats
            placement_rating = placement_data.get('rating_mu', 1500)
            placement_games = placement_data.get('games_played', 0)
            placement_wins = placement_data.get('wins', 0)
            placement_losses = placement_data.get('losses', 0)
            
            embed.add_field(
                name="📊 Placement Rating System",
                value=f"**Rating:** {placement_rating:.0f}\n"
                      f"**Games:** {placement_games}\n"
                      f"**Record:** {placement_wins}W-{placement_losses}L",
                inline=True
            )
            
            # OpenSkill system stats
            if openskill_data:
                openskill_display = openskill_data.get('display_rating', 1500)
                openskill_mu = openskill_data.get('mu', 25.0)
                openskill_sigma = openskill_data.get('sigma', 8.333)
                openskill_games = openskill_data.get('games_played', 0)
                
                embed.add_field(
                    name="🎯 OpenSkill Rating System",
                    value=f"**Display Rating:** {openskill_display:.0f}\n"
                          f"**Skill (μ):** {openskill_mu:.1f}\n"
                          f"**Uncertainty (σ):** {openskill_sigma:.1f}\n"
                          f"**Games:** {openskill_games}",
                    inline=True
                )
                
                # Calculate difference
                rating_diff = openskill_display - placement_rating
                if rating_diff > 0:
                    diff_text = f"OpenSkill is {rating_diff:.0f} points higher"
                elif rating_diff < 0:
                    diff_text = f"Placement is {abs(rating_diff):.0f} points higher"
                else:
                    diff_text = "Ratings are identical"
                
                embed.add_field(
                    name="📈 Comparison",
                    value=diff_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎯 OpenSkill Rating System",
                    value="**No OpenSkill data yet**\n"
                          "Play matches to generate OpenSkill ratings",
                    inline=True
                )
            
            # System explanations
            embed.add_field(
                name="ℹ️ System Differences",
                value="**Placement System:** Based on final team placement (1st, 2nd, 3rd, etc.)\n"
                      "**OpenSkill System:** Team-based skill assessment with uncertainty modeling\n"
                      "**Both systems:** Run in parallel, tracking the same matches",
                inline=False
            )
            
            embed.set_footer(text=f"Rating Comparison • {get_bot_footer_text()}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in rating_comparison command: {e}")
            embed = EmbedTemplates.error_embed(
                "Rating Comparison Error",
                "Failed to compare rating systems. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="openskill_recalculate", description="Recalculate OpenSkill ratings from match history (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def openskill_recalculate(self, interaction: discord.Interaction):
        """Admin command to recalculate OpenSkill ratings from history"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # This would trigger the historical calculation
            embed = discord.Embed(
                title="🔄 OpenSkill Recalculation",
                description="This feature will recalculate all OpenSkill ratings from match history.\n\n"
                           "**Note:** This is currently a manual process. Please run the migration script:\n"
                           "`python3 api/migrations/calculate_openskill_history.py`",
                color=Config.WARNING_COLOR
            )
            
            embed.add_field(
                name="⚠️ Important",
                value="This will reset all current OpenSkill ratings and recalculate from scratch.",
                inline=False
            )
            
            embed.set_footer(text=f"Admin Command • {get_bot_footer_text()}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in openskill_recalculate command: {e}")
            embed = EmbedTemplates.error_embed(
                "Recalculation Error",
                "Failed to initiate OpenSkill recalculation. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(OpenSkillCommands(bot))
