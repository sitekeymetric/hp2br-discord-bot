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
    
    @app_commands.command(name="stats", description="Show player statistics (based on completed matches only)")
    @app_commands.describe(user="The user to show stats for (defaults to yourself)")
    async def stats(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Display user statistics based only on COMPLETED matches"""
        await interaction.response.defer()
        
        target_user = user or interaction.user
        
        try:
            # Get user data with completed match statistics only
            user_data = await api_client.get_user_completed_stats(interaction.guild.id, target_user.id)
            
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
            
            # Get teammate statistics (top 3 teammates)
            teammate_stats = await api_client.get_user_teammate_stats(
                guild_id=interaction.guild.id,
                user_id=target_user.id,
                limit=3
            )
            
            # Create stats embed with completed match data and teammate info
            embed = EmbedTemplates.user_stats_embed(user_data, teammate_stats)
            
            # Add note about completed matches only
            embed.add_field(
                name="📊 Statistics Note",
                value="Statistics shown are based on **completed matches only**.\nPending or cancelled matches are not included.",
                inline=False
            )
            
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
    
    @app_commands.command(name="leaderboard", description="Show guild leaderboard (all registered players)")
    @app_commands.describe(limit="Number of players to show (default: 10, max: 25)")
    async def leaderboard(self, interaction: discord.Interaction, limit: Optional[int] = 10):
        """Display top players in the guild - shows all registered users"""
        await interaction.response.defer()
        
        # Validate limit
        limit = max(1, min(limit, 25))
        
        try:
            # Get users with completed match statistics (includes users with 0 completed matches)
            users = await api_client.get_guild_users_completed_stats(interaction.guild.id)
            
            if not users:
                embed = EmbedTemplates.warning_embed(
                    "No Players Found",
                    "No players are registered in this guild yet!\nUse `/register` to be the first!"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Sort by rating (mu) descending, then by games played descending
            users.sort(key=lambda x: (x.get("rating_mu", 1500), x.get("games_played", 0)), reverse=True)
            
            # Limit results
            users = users[:limit]
            
            embed = EmbedTemplates.leaderboard_embed(
                users=users,
                guild_name=interaction.guild.name
            )
            
            # Count users with and without completed matches
            users_with_matches = len([u for u in users if u.get("games_played", 0) > 0])
            users_without_matches = len(users) - users_with_matches
            
            # Add informative note
            note_text = "Rankings are based on **rating and completed matches**."
            if users_without_matches > 0:
                note_text += f"\n{users_without_matches} player(s) shown have not completed matches yet."
            
            embed.add_field(
                name="📊 Leaderboard Note",
                value=note_text,
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard command: {e}")
            embed = EmbedTemplates.error_embed(
                "Leaderboard Error",
                "Failed to retrieve leaderboard. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="match_history", description="Show recent completed match history")
    @app_commands.describe(
        user="The user to show history for (defaults to yourself)",
        limit="Number of completed matches to show (default: 5, max: 10)"
    )
    async def match_history(self, interaction: discord.Interaction, 
                           user: Optional[discord.Member] = None, 
                           limit: Optional[int] = 5):
        """Display completed match history only"""
        await interaction.response.defer()
        
        target_user = user or interaction.user
        limit = max(1, min(limit, 10))
        
        try:
            # Check if user is registered using completed stats
            user_data = await api_client.get_user_completed_stats(interaction.guild.id, target_user.id)
            
            if not user_data:
                embed = EmbedTemplates.warning_embed(
                    "User Not Found",
                    f"{target_user.display_name} is not registered in the system."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Get completed match history only
            matches = await api_client.get_user_completed_match_history(
                guild_id=interaction.guild.id,
                user_id=target_user.id,
                limit=limit
            )
            
            embed = EmbedTemplates.match_history_embed(
                matches=matches,
                username=target_user.display_name
            )
            
            # Add note about completed matches only
            embed.add_field(
                name="📊 History Note",
                value="Only **completed matches** are shown.\nPending or cancelled matches are not included.",
                inline=False
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

    @app_commands.command(name="teammates", description="Show your most frequent teammates and win rates")
    @app_commands.describe(
        user="The user to show teammates for (defaults to yourself)",
        limit="Number of teammates to show (default: 5, max: 10)"
    )
    async def teammates(self, interaction: discord.Interaction, 
                       user: Optional[discord.Member] = None, 
                       limit: Optional[int] = 5):
        """Show teammate statistics - most frequent teammates and win rates"""
        await interaction.response.defer()
        
        try:
            # Determine target user
            target_user = user if user else interaction.user
            
            # Validate limit
            if limit is None:
                limit = 5
            elif limit < 1:
                limit = 1
            elif limit > 10:
                limit = 10
            
            # Get teammate statistics
            teammate_stats = await api_client.get_user_teammate_stats(
                guild_id=interaction.guild.id,
                user_id=target_user.id,
                limit=limit
            )
            
            # Create embed
            embed = EmbedTemplates.teammate_stats_embed(
                teammate_stats=teammate_stats,
                username=target_user.display_name
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in teammates command: {e}")
            embed = EmbedTemplates.error_embed(
                "Teammates Error",
                "An error occurred while fetching teammate statistics. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))