import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from services.api_client import api_client
from services.voice_manager import VoiceManager
from utils.embeds import EmbedTemplates
from utils.views import ConfirmationView
from utils.constants import Config, VALID_REGIONS
from utils.version import get_version_embed_field

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
    


    @app_commands.command(name="admin_cleanup", description="Admin cleanup - clean up abandoned team channels with detailed logging")
    @app_commands.default_permissions(administrator=True)
    async def admin_cleanup(self, interaction: discord.Interaction):
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
    
    @app_commands.command(name="admin_delete_user", description="Delete a user from the system")
    @app_commands.describe(user="The user to delete from the system")
    @app_commands.default_permissions(administrator=True)
    async def admin_delete_user(self, interaction: discord.Interaction, user: discord.Member):
        """Admin command to delete a user"""
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
            
            # Create confirmation embed
            embed = EmbedTemplates.warning_embed(
                "⚠️ Admin Delete User Confirmation",
                f"Are you sure you want to delete **{user.display_name}**'s account?\n\n"
                f"**This will permanently remove:**\n"
                f"• Their rating ({user_data['rating_mu']:.0f} ± {user_data['rating_sigma']:.0f})\n"
                f"• Their statistics ({user_data['games_played']} games played)\n"
                f"• Their match history\n\n"
                f"**This action cannot be undone!**"
            )
            
            # Create confirmation view
            from utils.views import ConfirmationView
            view = ConfirmationView(timeout=30)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
            # Wait for admin response
            await view.wait()
            
            if view.value is None:
                # Timeout
                embed = EmbedTemplates.error_embed(
                    "Timeout",
                    "User deletion cancelled due to timeout."
                )
                await interaction.edit_original_response(embed=embed, view=None)
                return
            
            if not view.value:
                # Admin cancelled
                embed = EmbedTemplates.success_embed(
                    "Cancelled",
                    "User deletion cancelled."
                )
                await interaction.edit_original_response(embed=embed, view=None)
                return
            
            # Admin confirmed - delete user
            success = await api_client.delete_user(interaction.guild.id, user.id)
            
            if success:
                embed = EmbedTemplates.success_embed(
                    "User Deleted",
                    f"**{user.display_name}**'s account has been successfully deleted from the system."
                )
                await interaction.edit_original_response(embed=embed, view=None)
                
                logger.info(f"Admin {interaction.user.display_name} deleted user {user.display_name} ({user.id})")
            else:
                embed = EmbedTemplates.error_embed(
                    "Deletion Failed",
                    "Failed to delete the user. Please try again later."
                )
                await interaction.edit_original_response(embed=embed, view=None)
                
        except Exception as e:
            logger.error(f"Error in admin_delete_user command: {e}")
            embed = EmbedTemplates.error_embed(
                "Deletion Error",
                "An error occurred while deleting the user. Please try again later."
            )
            await interaction.edit_original_response(embed=embed, view=None)
    
    @app_commands.command(name="admin_update_user", description="Update a user's information")
    @app_commands.describe(
        user="The user to update",
        username="New username (optional)",
        region="New region (optional)"
    )
    @app_commands.default_permissions(administrator=True)
    async def admin_update_user(self, interaction: discord.Interaction, 
                               user: discord.Member,
                               username: Optional[str] = None,
                               region: Optional[str] = None):
        """Admin command to update user information"""
        await interaction.response.defer(ephemeral=True)
        
        # Validate inputs
        if not username and not region:
            embed = EmbedTemplates.error_embed(
                "No Updates Specified",
                "Please specify at least one field to update (username or region)."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Validate region if provided
        if region:
            region = region.upper()
            if region not in VALID_REGIONS:
                embed = EmbedTemplates.error_embed(
                    "Invalid Region",
                    f"Valid regions are: {', '.join(VALID_REGIONS)}"
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
        
        # Validate username if provided
        if username and len(username) > 32:
            embed = EmbedTemplates.error_embed(
                "Username Too Long",
                "Username must be 32 characters or less."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
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
            
            # Prepare update data
            update_data = {}
            if username:
                update_data['username'] = username.strip()
            if region:
                update_data['region_code'] = region
            
            # Update user
            updated_user = await api_client.update_user(
                guild_id=interaction.guild.id,
                user_id=user.id,
                **update_data
            )
            
            if updated_user:
                changes = []
                if username:
                    changes.append(f"Username: **{username.strip()}**")
                if region:
                    changes.append(f"Region: **{region}**")
                
                embed = EmbedTemplates.success_embed(
                    "User Updated",
                    f"Successfully updated **{user.display_name}**:\n" + "\n".join(changes)
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
                logger.info(f"Admin {interaction.user.display_name} updated user {user.display_name}: {update_data}")
            else:
                embed = EmbedTemplates.error_embed(
                    "Update Failed",
                    "Failed to update the user. Please try again later."
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in admin_update_user command: {e}")
            embed = EmbedTemplates.error_embed(
                "Update Error",
                "An error occurred while updating the user. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="admin_reset_rating", description="Reset a user's rating to default")
    @app_commands.describe(user="The user whose rating to reset")
    @app_commands.default_permissions(administrator=True)
    async def admin_reset_rating(self, interaction: discord.Interaction, user: discord.Member):
        """Admin command to reset user's rating"""
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
            
            # Create confirmation embed
            embed = EmbedTemplates.warning_embed(
                "⚠️ Reset Rating Confirmation",
                f"Are you sure you want to reset **{user.display_name}**'s rating?\n\n"
                f"**Current Rating:** {user_data['rating_mu']:.0f} ± {user_data['rating_sigma']:.0f}\n"
                f"**New Rating:** 1500 ± 350 (default)\n\n"
                f"This action cannot be undone!"
            )
            
            # Create confirmation view
            from utils.views import ConfirmationView
            view = ConfirmationView(timeout=30)
            
            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
            
            # Wait for admin response
            await view.wait()
            
            if view.value is None:
                # Timeout
                embed = EmbedTemplates.error_embed(
                    "Timeout",
                    "Rating reset cancelled due to timeout."
                )
                await interaction.edit_original_response(embed=embed, view=None)
                return
            
            if not view.value:
                # Admin cancelled
                embed = EmbedTemplates.success_embed(
                    "Cancelled",
                    "Rating reset cancelled."
                )
                await interaction.edit_original_response(embed=embed, view=None)
                return
            
            # Admin confirmed - reset rating
            success = await api_client.update_user_rating(
                guild_id=interaction.guild.id,
                user_id=user.id,
                new_mu=1500.0,
                new_sigma=350.0
            )
            
            if success:
                embed = EmbedTemplates.success_embed(
                    "Rating Reset",
                    f"**{user.display_name}**'s rating has been reset to default (1500 ± 350)."
                )
                await interaction.edit_original_response(embed=embed, view=None)
                
                logger.info(f"Admin {interaction.user.display_name} reset rating for user {user.display_name} ({user.id})")
            else:
                embed = EmbedTemplates.error_embed(
                    "Reset Failed",
                    "Failed to reset the user's rating. Please try again later."
                )
                await interaction.edit_original_response(embed=embed, view=None)
                
        except Exception as e:
            logger.error(f"Error in admin_reset_rating command: {e}")
            embed = EmbedTemplates.error_embed(
                "Reset Error",
                "An error occurred while resetting the rating. Please try again later."
            )
            await interaction.edit_original_response(embed=embed, view=None)
    
    @app_commands.command(name="sync_commands", description="Manually sync bot commands with Discord")
    @app_commands.default_permissions(administrator=True)
    async def sync_commands(self, interaction: discord.Interaction):
        """Manually sync slash commands with proper rate limit handling"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Import the sync function from main.py
            from main import sync_commands_with_retry
            
            embed = EmbedTemplates.warning_embed(
                "🔄 Syncing Commands",
                "Starting command sync with Discord API...\nThis may take a moment if rate limited."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Perform sync
            synced = await sync_commands_with_retry()
            
            if synced is not None:
                embed = EmbedTemplates.success_embed(
                    "✅ Commands Synced",
                    f"Successfully synced **{len(synced)}** commands with Discord.\n"
                    f"All slash commands should now be available."
                )
                logger.info(f"Admin {interaction.user.display_name} manually synced {len(synced)} commands")
            else:
                embed = EmbedTemplates.error_embed(
                    "❌ Sync Failed",
                    "Command sync failed after multiple retries.\n"
                    "Discord may be heavily rate limiting. Try again later."
                )
                logger.warning(f"Manual command sync failed for admin {interaction.user.display_name}")
            
            await interaction.edit_original_response(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in sync_commands command: {e}")
            embed = EmbedTemplates.error_embed(
                "Sync Error",
                f"An error occurred during command sync: {str(e)}"
            )
            await interaction.edit_original_response(embed=embed)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))