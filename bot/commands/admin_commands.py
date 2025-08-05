import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from services.api_client import api_client
from services.voice_manager import VoiceManager
from utils.embeds import EmbedTemplates
from utils.views import ConfirmationView
from utils.constants import Config

logger = logging.getLogger(__name__)

class AdminCommands(commands.Cog):
    """Administrative commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.voice_manager = VoiceManager(bot)
    
    @app_commands.command(name="setup", description="Setup bot for this guild")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        """Initial guild configuration"""
        await interaction.response.defer()
        
        try:
            # Check current setup
            setup_issues = []
            
            # Check for waiting room
            waiting_room = discord.utils.get(interaction.guild.voice_channels, name=Config.WAITING_ROOM_NAME)
            if not waiting_room:
                setup_issues.append("Missing waiting room voice channel")
            
            # Check bot permissions
            bot_member = interaction.guild.me
            
            # Check general permissions
            if not bot_member.guild_permissions.manage_channels:
                setup_issues.append("Bot needs 'Manage Channels' permission")
            
            if not bot_member.guild_permissions.move_members:
                setup_issues.append("Bot needs 'Move Members' permission")
            
            if not bot_member.guild_permissions.send_messages:
                setup_issues.append("Bot needs 'Send Messages' permission")
            
            if not bot_member.guild_permissions.use_slash_commands:
                setup_issues.append("Bot needs 'Use Slash Commands' permission")
            
            # If no issues, report current status
            if not setup_issues:
                embed = EmbedTemplates.success_embed(
                    "Setup Complete",
                    "✅ Bot is properly configured for this guild!\n\n"
                    f"**Waiting Room:** {Config.WAITING_ROOM_NAME}\n"
                    f"**Permissions:** All required permissions granted\n\n"
                    "Players can now use `/register` to join the system and `/create_teams` to start matches!"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Setup needed - create waiting room if missing
            created_items = []
            
            if not waiting_room:
                success = await self.voice_manager.setup_voice_channels(interaction.guild)
                if success:
                    created_items.append(f"✅ Created '{Config.WAITING_ROOM_NAME}' voice channel")
                else:
                    setup_issues.append("❌ Failed to create waiting room (check permissions)")
            
            # Report setup results
            embed = discord.Embed(
                title="🔧 Guild Setup",
                color=Config.EMBED_COLOR
            )
            
            if created_items:
                embed.add_field(
                    name="Created Items",
                    value="\n".join(created_items),
                    inline=False
                )
            
            if setup_issues:
                embed.add_field(
                    name="⚠️ Setup Issues",
                    value="\n".join([f"• {issue}" for issue in setup_issues]),
                    inline=False
                )
                embed.add_field(
                    name="📝 Next Steps",
                    value="Please grant the bot the required permissions and run `/setup` again.",
                    inline=False
                )
                embed.color = Config.WARNING_COLOR
            else:
                embed.description = "✅ Setup completed successfully!"
                embed.add_field(
                    name="🎮 Ready to Use",
                    value="Players can now use `/register` and `/create_teams`!",
                    inline=False
                )
                embed.color = Config.SUCCESS_COLOR
            
            await interaction.followup.send(embed=embed)
            logger.info(f"Setup completed for guild {interaction.guild.name}")
            
        except Exception as e:
            logger.error(f"Error in setup command: {e}")
            embed = EmbedTemplates.error_embed(
                "Setup Error",
                "An error occurred during setup. Please check bot permissions and try again."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="reset_user", description="Reset user's rating and stats")
    @app_commands.describe(user="The user to reset")
    @app_commands.default_permissions(administrator=True)
    async def reset_user(self, interaction: discord.Interaction, user: discord.Member):
        """Admin function to reset user data"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user exists
            user_data = await api_client.get_user(interaction.guild.id, user.id)
            
            if not user_data:
                embed = EmbedTemplates.warning_embed(
                    "User Not Found",
                    f"{user.display_name} is not registered in the system."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Show current stats and ask for confirmation
            current_rating = user_data.get('rating_mu', 1500)
            current_games = user_data.get('games_played', 0)
            
            embed = discord.Embed(
                title="⚠️ Confirm User Reset",
                description=f"Are you sure you want to reset **{user.display_name}**'s data?",
                color=Config.WARNING_COLOR
            )
            
            embed.add_field(
                name="Current Stats",
                value=f"**Rating:** {current_rating:.0f}\n**Games:** {current_games}",
                inline=True
            )
            
            embed.add_field(
                name="After Reset",
                value=f"**Rating:** {Config.DEFAULT_RATING_MU:.0f}\n**Games:** 0",
                inline=True
            )
            
            embed.set_footer(text="This action cannot be undone!")
            
            # Create confirmation view
            view = ConfirmationView()
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
            # Wait for confirmation
            await view.wait()
            
            if view.result is True:
                # Reset user by deleting and recreating
                # Note: This is a simplified approach. In production, you might want a proper reset endpoint
                
                # For now, we'll update their rating to default values
                reset_user = await api_client.update_user_rating(
                    guild_id=interaction.guild.id,
                    user_id=user.id,
                    new_mu=Config.DEFAULT_RATING_MU,
                    new_sigma=Config.DEFAULT_RATING_SIGMA
                )
                
                if reset_user:
                    embed = EmbedTemplates.success_embed(
                        "User Reset Complete",
                        f"✅ {user.display_name}'s rating has been reset to default values.\n\n"
                        f"**New Rating:** {Config.DEFAULT_RATING_MU:.0f} ± {Config.DEFAULT_RATING_SIGMA:.0f}"
                    )
                    await interaction.edit_original_response(embed=embed, view=None)
                    
                    logger.info(f"Admin {interaction.user.display_name} reset user {user.display_name} in guild {interaction.guild.id}")
                else:
                    embed = EmbedTemplates.error_embed(
                        "Reset Failed",
                        "Failed to reset user data. Please try again later."
                    )
                    await interaction.edit_original_response(embed=embed, view=None)
            
            elif view.result is False:
                embed = EmbedTemplates.warning_embed(
                    "Reset Cancelled",
                    "User reset was cancelled."
                )
                await interaction.edit_original_response(embed=embed, view=None)
            
            else:  # Timeout
                embed = EmbedTemplates.warning_embed(
                    "Reset Expired",
                    "Reset confirmation timed out."
                )
                await interaction.edit_original_response(embed=embed, view=None)
            
        except Exception as e:
            logger.error(f"Error in reset_user command: {e}")
            embed = EmbedTemplates.error_embed(
                "Reset Error",
                "An error occurred while resetting user data. Please try again."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="guild_stats", description="Show guild statistics")
    @app_commands.default_permissions(administrator=True)
    async def guild_stats(self, interaction: discord.Interaction):
        """Display guild-wide statistics"""
        await interaction.response.defer()
        
        try:
            # Get all users in guild
            users = await api_client.get_guild_users(interaction.guild.id)
            
            if not users:
                embed = EmbedTemplates.warning_embed(
                    "No Data",
                    "No players are registered in this guild yet."
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Calculate statistics
            total_players = len(users)
            total_games = sum(user.get('games_played', 0) for user in users)
            active_players = len([u for u in users if u.get('games_played', 0) > 0])
            
            # Rating statistics
            ratings = [user.get('rating_mu', 1500) for user in users]
            avg_rating = sum(ratings) / len(ratings) if ratings else 1500
            highest_rating = max(ratings) if ratings else 1500
            lowest_rating = min(ratings) if ratings else 1500
            
            # Get recent matches
            recent_matches = await api_client.get_guild_matches(interaction.guild.id, limit=10)
            matches_today = len([m for m in recent_matches if m.get('status') == 'completed'])
            
            embed = discord.Embed(
                title=f"📊 Guild Statistics - {interaction.guild.name}",
                color=Config.EMBED_COLOR
            )
            
            embed.add_field(
                name="👥 Players",
                value=f"**Total:** {total_players}\n**Active:** {active_players}",
                inline=True
            )
            
            embed.add_field(
                name="🎮 Matches",
                value=f"**Total Games:** {total_games}\n**Recent:** {matches_today}",
                inline=True
            )
            
            embed.add_field(
                name="📈 Ratings",
                value=f"**Average:** {avg_rating:.0f}\n**Range:** {lowest_rating:.0f} - {highest_rating:.0f}",
                inline=True
            )
            
            # Top players
            if users:
                top_users = sorted(users, key=lambda x: x.get('rating_mu', 0), reverse=True)[:5]
                top_text = []
                for i, user in enumerate(top_users):
                    username = user.get('username', 'Unknown')
                    rating = user.get('rating_mu', 1500)
                    games = user.get('games_played', 0)
                    top_text.append(f"{i+1}. {username} - {rating:.0f} ({games} games)")
                
                embed.add_field(
                    name="🏆 Top Players",
                    value="\n".join(top_text),
                    inline=False
                )
            
            # Voice channel status
            waiting_room = discord.utils.get(interaction.guild.voice_channels, name=Config.WAITING_ROOM_NAME)
            if waiting_room:
                current_waiting = len([m for m in waiting_room.members if not m.bot])
                embed.add_field(
                    name="🎯 Current Status",
                    value=f"**In Waiting Room:** {current_waiting} players",
                    inline=True
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in guild_stats command: {e}")
            embed = EmbedTemplates.error_embed(
                "Stats Error",
                "Failed to retrieve guild statistics. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="cleanup", description="Clean up abandoned team channels")
    @app_commands.default_permissions(administrator=True)
    async def cleanup(self, interaction: discord.Interaction):
        """Clean up abandoned team channels"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Find team channels
            team_channels = []
            for channel in interaction.guild.voice_channels:
                if Config.TEAM_CHANNEL_PREFIX.lower() in channel.name.lower():
                    team_channels.append(channel)
            
            if not team_channels:
                embed = EmbedTemplates.success_embed(
                    "No Cleanup Needed",
                    "No team channels found to clean up."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Perform cleanup
            await self.voice_manager.cleanup_team_channels(interaction.guild, return_to_waiting=True)
            
            # Clear any active match
            self.voice_manager.clear_active_match(interaction.guild.id)
            
            embed = EmbedTemplates.success_embed(
                "Cleanup Complete",
                f"✅ Cleaned up {len(team_channels)} team channels.\n"
                f"✅ Returned players to waiting room.\n"
                f"✅ Cleared active match data."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            logger.info(f"Admin cleanup performed by {interaction.user.display_name} in guild {interaction.guild.id}")
            
        except Exception as e:
            logger.error(f"Error in cleanup command: {e}")
            embed = EmbedTemplates.error_embed(
                "Cleanup Error",
                "An error occurred during cleanup. Please try again."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))