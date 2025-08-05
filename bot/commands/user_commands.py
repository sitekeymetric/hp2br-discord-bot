import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from services.api_client import api_client
from utils.embeds import EmbedTemplates
from utils.constants import Config, VALID_REGIONS

logger = logging.getLogger(__name__)

class UserCommands(commands.Cog):
    """User management commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="register", description="Register yourself in the team balance system")
    @app_commands.describe(region="Your region (CA, TX, NY, KR, NA, EU)")
    async def register(self, interaction: discord.Interaction, region: Optional[str] = None):
        """Register user in the database system"""
        await interaction.response.defer()
        
        # Validate region if provided
        if region and region.upper() not in VALID_REGIONS:
            embed = EmbedTemplates.error_embed(
                "Invalid Region",
                f"Valid regions are: {', '.join(VALID_REGIONS)}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Normalize region
        if region:
            region = region.upper()
        
        try:
            # Check if user already exists
            existing_user = await api_client.get_user(interaction.guild.id, interaction.user.id)
            
            if existing_user:
                embed = EmbedTemplates.warning_embed(
                    "Already Registered",
                    f"You're already registered! Use `/stats` to see your statistics."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create new user
            user_data = await api_client.create_user(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                username=interaction.user.display_name,
                region=region
            )
            
            if user_data:
                embed = EmbedTemplates.success_embed(
                    "Registration Successful!",
                    f"Welcome to the team balance system, {interaction.user.display_name}!\n\n"
                    f"🎯 **Starting Rating:** {user_data['rating_mu']:.0f} ± {user_data['rating_sigma']:.0f}\n"
                    f"🌍 **Region:** {region or 'Not Set'}\n\n"
                    f"You can now participate in balanced team matches. Use `/stats` to view your progress!"
                )
                await interaction.followup.send(embed=embed)
                
                logger.info(f"User {interaction.user.display_name} ({interaction.user.id}) registered in guild {interaction.guild.id}")
            else:
                embed = EmbedTemplates.error_embed(
                    "Registration Failed",
                    "Failed to register you in the system. Please try again later."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in register command: {e}")
            embed = EmbedTemplates.error_embed(
                "Registration Error",
                "An error occurred during registration. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="stats", description="Show player statistics")
    @app_commands.describe(user="The user to show stats for (defaults to yourself)")
    async def stats(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Display user statistics"""
        await interaction.response.defer()
        
        target_user = user or interaction.user
        
        try:
            user_data = await api_client.get_user(interaction.guild.id, target_user.id)
            
            if not user_data:
                if target_user == interaction.user:
                    embed = EmbedTemplates.warning_embed(
                        "Not Registered",
                        "You're not registered yet! Use `/register` to join the team balance system."
                    )
                else:
                    embed = EmbedTemplates.warning_embed(
                        "User Not Found",
                        f"{target_user.display_name} is not registered in the system."
                    )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create stats embed
            embed = EmbedTemplates.user_stats_embed(user_data)
            
            # Set user avatar if available
            if target_user.avatar:
                embed.set_thumbnail(url=target_user.avatar.url)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            embed = EmbedTemplates.error_embed(
                "Stats Error",
                "Failed to retrieve user statistics. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="set_region", description="Update your region")
    @app_commands.describe(region="Your region (CA, TX, NY, KR, NA, EU)")
    async def set_region(self, interaction: discord.Interaction, region: str):
        """Update user's region preference"""
        await interaction.response.defer(ephemeral=True)
        
        # Validate region
        region = region.upper()
        if region not in VALID_REGIONS:
            embed = EmbedTemplates.error_embed(
                "Invalid Region",
                f"Valid regions are: {', '.join(VALID_REGIONS)}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        try:
            # Check if user exists
            user_data = await api_client.get_user(interaction.guild.id, interaction.user.id)
            
            if not user_data:
                embed = EmbedTemplates.warning_embed(
                    "Not Registered",
                    "You're not registered yet! Use `/register` to join the system first."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Update region
            updated_user = await api_client.update_user(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                region_code=region
            )
            
            if updated_user:
                embed = EmbedTemplates.success_embed(
                    "Region Updated",
                    f"Your region has been updated to **{region}**!"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                logger.info(f"User {interaction.user.display_name} updated region to {region}")
            else:
                embed = EmbedTemplates.error_embed(
                    "Update Failed",
                    "Failed to update your region. Please try again later."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in set_region command: {e}")
            embed = EmbedTemplates.error_embed(
                "Update Error",
                "An error occurred while updating your region. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="leaderboard", description="Show guild leaderboard")
    @app_commands.describe(limit="Number of players to show (default: 10, max: 25)")
    async def leaderboard(self, interaction: discord.Interaction, limit: Optional[int] = 10):
        """Display top players in the guild"""
        await interaction.response.defer()
        
        # Validate limit
        limit = max(1, min(limit, 25))
        
        try:
            users = await api_client.get_guild_users(interaction.guild.id)
            
            if not users:
                embed = EmbedTemplates.warning_embed(
                    "No Players Found",
                    "No players are registered in this guild yet!\nUse `/register` to be the first!"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Sort by rating (mu) descending
            users.sort(key=lambda x: x.get("rating_mu", 0), reverse=True)
            
            # Limit results
            users = users[:limit]
            
            embed = EmbedTemplates.leaderboard_embed(
                users=users,
                guild_name=interaction.guild.name
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            embed = EmbedTemplates.error_embed(
                "Leaderboard Error",
                "Failed to retrieve leaderboard. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="match_history", description="Show recent match history")
    @app_commands.describe(
        user="The user to show history for (defaults to yourself)",
        limit="Number of matches to show (default: 5, max: 10)"
    )
    async def match_history(self, interaction: discord.Interaction, 
                           user: Optional[discord.Member] = None, 
                           limit: Optional[int] = 5):
        """Display match history"""
        await interaction.response.defer()
        
        target_user = user or interaction.user
        limit = max(1, min(limit, 10))
        
        try:
            # Check if user is registered
            user_data = await api_client.get_user(interaction.guild.id, target_user.id)
            
            if not user_data:
                embed = EmbedTemplates.warning_embed(
                    "User Not Found",
                    f"{target_user.display_name} is not registered in the system."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Get match history
            matches = await api_client.get_user_match_history(
                guild_id=interaction.guild.id,
                user_id=target_user.id,
                limit=limit
            )
            
            embed = EmbedTemplates.match_history_embed(
                matches=matches,
                username=target_user.display_name
            )
            
            # Set user avatar if available
            if target_user.avatar:
                embed.set_thumbnail(url=target_user.avatar.url)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in match_history command: {e}")
            embed = EmbedTemplates.error_embed(
                "History Error",
                "Failed to retrieve match history. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    

    @app_commands.command(name="delete_account", description="Delete your account from the system")
    async def delete_account(self, interaction: discord.Interaction):
        """Delete user's account with confirmation"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user exists
            user_data = await api_client.get_user(interaction.guild.id, interaction.user.id)
            
            if not user_data:
                embed = EmbedTemplates.warning_embed(
                    "Not Registered",
                    "You're not registered in the system, so there's nothing to delete."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create confirmation embed
            embed = EmbedTemplates.warning_embed(
                "⚠️ Delete Account Confirmation",
                f"Are you sure you want to delete your account?\n\n"
                f"**This will permanently remove:**\n"
                f"• Your rating ({user_data['rating_mu']:.0f} ± {user_data['rating_sigma']:.0f})\n"
                f"• Your statistics ({user_data['games_played']} games played)\n"
                f"• Your match history\n\n"
                f"**This action cannot be undone!**"
            )
            
            # Create confirmation view
            from utils.views import ConfirmationView
            view = ConfirmationView(timeout=30)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
            # Wait for user response
            await view.wait()
            
            if view.value is None:
                # Timeout
                embed = EmbedTemplates.error_embed(
                    "Timeout",
                    "Account deletion cancelled due to timeout."
                )
                await interaction.edit_original_response(embed=embed, view=None)
                return
            
            if not view.value:
                # User cancelled
                embed = EmbedTemplates.success_embed(
                    "Cancelled",
                    "Account deletion cancelled. Your account is safe!"
                )
                await interaction.edit_original_response(embed=embed, view=None)
                return
            
            # User confirmed - delete account
            success = await api_client.delete_user(interaction.guild.id, interaction.user.id)
            
            if success:
                embed = EmbedTemplates.success_embed(
                    "Account Deleted",
                    "Your account has been successfully deleted from the system.\n"
                    "You can register again anytime using `/register`."
                )
                await interaction.edit_original_response(embed=embed, view=None)
                
                logger.info(f"User {interaction.user.display_name} ({interaction.user.id}) deleted their account")
            else:
                embed = EmbedTemplates.error_embed(
                    "Deletion Failed",
                    "Failed to delete your account. Please try again later or contact an administrator."
                )
                await interaction.edit_original_response(embed=embed, view=None)
                
        except Exception as e:
            logger.error(f"Error in delete_account command: {e}")
            embed = EmbedTemplates.error_embed(
                "Deletion Error",
                "An error occurred while deleting your account. Please try again later."
            )
            await interaction.edit_original_response(embed=embed, view=None)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))