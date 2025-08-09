"""
Advanced Rating System Commands
New commands for the v3.0.0 rating system with opponent strength consideration
"""

import discord
from discord.ext import commands
from typing import Dict, List, Optional
import logging

from services.api_client import api_client
from services.voice_manager import VoiceManager
from utils.advanced_rating_ui import AdvancedRatingEmbeds, AdvancedRatingView
from utils.embeds import EmbedTemplates
from utils.version import get_version_string

logger = logging.getLogger(__name__)


class AdvancedRatingCommands(commands.Cog):
    """Commands for the advanced rating system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.voice_manager = VoiceManager()
    
    @discord.slash_command(
        name="rating_preview",
        description="Preview rating changes for different placements (Advanced Rating System v3.0)"
    )
    async def rating_preview(
        self,
        ctx: discord.ApplicationContext,
        user: discord.Member = None
    ):
        """Preview rating changes based on current waiting room composition"""
        
        await ctx.defer()
        
        try:
            target_user = user or ctx.author
            guild_id = ctx.guild.id
            
            # Get user's current rating
            user_data = await api_client.get_user(guild_id, target_user.id)
            if not user_data:
                # Try to auto-register
                user_data = await api_client.auto_register_user(guild_id, target_user.id, target_user.display_name)
                if not user_data:
                    embed = EmbedTemplates.error_embed("User not found", "Please register first using `/register`")
                    await ctx.followup.send(embed=embed, ephemeral=True)
                    return
            
            player_rating = user_data['rating_mu']
            
            # Get waiting room members to simulate team composition
            waiting_room_members = await self.voice_manager.get_waiting_room_members(ctx.guild)
            
            if len(waiting_room_members) < 3:
                embed = EmbedTemplates.error_embed(
                    "Not Enough Players", 
                    "Need at least 3 players in Waiting Room to preview ratings.\n"
                    "Join the Waiting Room voice channel to see your rating preview!"
                )
                await ctx.followup.send(embed=embed, ephemeral=True)
                return
            
            # Calculate team averages (simulate 3 teams)
            team_size = len(waiting_room_members) // 3
            if team_size == 0:
                team_size = 1
            
            # Get ratings for all players
            player_ratings = {}
            for member in waiting_room_members:
                member_data = await api_client.get_user_or_register(guild_id, member.id, member.display_name)
                if member_data:
                    player_ratings[member.id] = member_data['rating_mu']
                else:
                    player_ratings[member.id] = 1500.0  # Default rating
            
            # Sort players by rating for team simulation
            sorted_players = sorted(waiting_room_members, key=lambda m: player_ratings[m.id], reverse=True)
            
            # Create simulated teams using snake draft
            teams = [[] for _ in range(3)]
            for i, player in enumerate(sorted_players):
                team_index = i % 3 if (i // 3) % 2 == 0 else 2 - (i % 3)
                teams[team_index].append(player)
            
            # Find which team the target user is on
            user_team_index = None
            for i, team in enumerate(teams):
                if target_user in team:
                    user_team_index = i
                    break
            
            if user_team_index is None:
                embed = EmbedTemplates.error_embed(
                    "User Not in Waiting Room",
                    f"{target_user.display_name} is not in the Waiting Room voice channel."
                )
                await ctx.followup.send(embed=embed, ephemeral=True)
                return
            
            # Calculate team averages
            team_averages = []
            for team in teams:
                if team:
                    avg_rating = sum(player_ratings[member.id] for member in team) / len(team)
                    team_averages.append(avg_rating)
                else:
                    team_averages.append(1500.0)
            
            user_team_avg = team_averages[user_team_index]
            
            # Create opponent teams data
            opponent_teams = []
            for i, avg_rating in enumerate(team_averages):
                if i != user_team_index:
                    opponent_teams.append({"avg_rating": avg_rating})
            
            # Get rating preview from API
            preview_data = await api_client.preview_rating_changes(
                player_rating, user_team_avg, opponent_teams
            )
            
            if not preview_data:
                embed = EmbedTemplates.error_embed("Preview Failed", "Could not generate rating preview")
                await ctx.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create preview embed
            embed = AdvancedRatingEmbeds.create_rating_preview_embed(
                player_rating=player_rating,
                team_avg=user_team_avg,
                opponent_teams=opponent_teams,
                previews=preview_data.get('placement_previews', {}),
                username=target_user.display_name
            )
            
            # Add team composition info
            team_info = f"**Simulated Teams ({len(waiting_room_members)} players):**\n"
            for i, team in enumerate(teams):
                if team:
                    team_ratings = [player_ratings[member.id] for member in team]
                    avg_rating = sum(team_ratings) / len(team_ratings)
                    
                    if i == user_team_index:
                        team_info += f"🔹 **Your Team {i+1}:** {avg_rating:.0f} avg ({len(team)} players)\n"
                    else:
                        team_info += f"⚪ **Team {i+1}:** {avg_rating:.0f} avg ({len(team)} players)\n"
            
            embed.add_field(
                name="👥 Current Waiting Room",
                value=team_info,
                inline=False
            )
            
            # Create view with interactive buttons
            view = AdvancedRatingView()
            
            await ctx.followup.send(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error in rating_preview command: {str(e)}")
            embed = EmbedTemplates.error_embed("Preview Error", f"Failed to generate rating preview: {str(e)}")
            await ctx.followup.send(embed=embed, ephemeral=True)
    
    @discord.slash_command(
        name="advanced_rating_scale",
        description="Show the complete Advanced Rating System v3.0 scale and information"
    )
    async def advanced_rating_scale(self, ctx: discord.ApplicationContext):
        """Show comprehensive rating scale for advanced system"""
        
        try:
            # Get rating scale data from API
            scale_data = await api_client.get_advanced_rating_scale()
            
            # Create comprehensive rating scale embed
            embed = AdvancedRatingEmbeds.create_advanced_rating_scale_embed()
            
            # Create view with interactive buttons
            view = AdvancedRatingView()
            
            await ctx.respond(embed=embed, view=view)
            
        except Exception as e:
            logger.error(f"Error in advanced_rating_scale command: {str(e)}")
            embed = EmbedTemplates.error_embed("Rating Scale Error", f"Failed to get rating scale: {str(e)}")
            await ctx.respond(embed=embed, ephemeral=True)
    
    @discord.slash_command(
        name="record_advanced_result",
        description="Record match result using Advanced Rating System v3.0 (Admin only)"
    )
    @commands.has_permissions(administrator=True)
    async def record_advanced_result(self, ctx: discord.ApplicationContext):
        """Record match result with advanced rating calculations"""
        
        await ctx.defer()
        
        try:
            # Check if there's an active match
            # This would need to be implemented with match tracking
            embed = EmbedTemplates.error_embed(
                "Feature Coming Soon",
                "Advanced result recording will be integrated with the existing `/record_result` command.\n\n"
                "The system will automatically use Advanced Rating System v3.0 for all new matches."
            )
            await ctx.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in record_advanced_result command: {str(e)}")
            embed = EmbedTemplates.error_embed("Recording Error", f"Failed to record result: {str(e)}")
            await ctx.followup.send(embed=embed, ephemeral=True)


def setup(bot):
    """Setup function for the cog"""
    bot.add_cog(AdvancedRatingCommands(bot))
