import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional
from datetime import datetime

from services.api_client import api_client
from services.voice_manager import VoiceManager
from utils.embeds import EmbedTemplates
from utils.constants import Config, VALID_REGIONS
from utils.version import get_bot_footer_text

logger = logging.getLogger(__name__)

class UserCommands(commands.Cog):
    """User management commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.voice_manager = VoiceManager(bot)
    
    async def _sync_username_if_needed(self, guild_id: int, user: discord.Member, user_data: dict) -> dict:
        """
        Check if username needs updating and sync it if different
        Returns updated user_data if changed, original if unchanged
        """
        current_username = user.display_name
        stored_username = user_data.get('username', '')
        
        if current_username != stored_username:
            logger.info(f"Username sync needed for {user.id}: '{stored_username}' -> '{current_username}'")
            try:
                updated_data = await api_client.update_user(
                    guild_id=guild_id,
                    user_id=user.id,
                    username=current_username
                )
                if updated_data:
                    logger.info(f"Successfully synced username for {user.id}")
                    return updated_data
                else:
                    logger.warning(f"Failed to sync username for {user.id}")
            except Exception as e:
                logger.error(f"Error syncing username for {user.id}: {e}")
        
        return user_data
    
    async def _sync_multiple_usernames(self, guild: discord.Guild, users_data: list) -> list:
        """
        Sync usernames for multiple users in bulk
        Returns updated users_data list
        """
        updated_users = []
        sync_count = 0
        
        for user_data in users_data:
            user_id = user_data.get('user_id')
            if not user_id:
                updated_users.append(user_data)
                continue
                
            # Find the Discord member
            member = guild.get_member(user_id)
            if not member:
                # User not in guild anymore, keep original data
                updated_users.append(user_data)
                continue
            
            # Sync username if needed
            updated_data = await self._sync_username_if_needed(guild.id, member, user_data)
            if updated_data != user_data:
                sync_count += 1
            updated_users.append(updated_data)
        
        if sync_count > 0:
            logger.info(f"Synced usernames for {sync_count} users in guild {guild.name}")
        
        return updated_users
    
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
    
    @app_commands.command(name="stats", description="Show player statistics (auto-syncs username, includes OpenSkill beta)")
    @app_commands.describe(user="The user to show stats for (defaults to yourself)")
    async def stats(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """Display user statistics based only on COMPLETED matches"""
        await interaction.response.defer(ephemeral=True)
        
        target_user = user or interaction.user
        
        try:
            # Get user data with completed match statistics only
            user_data = await api_client.get_user_completed_stats(interaction.guild.id, target_user.id)
            
            if not user_data:
                # Check if user is in waiting room for auto-registration
                waiting_members = await self.voice_manager.get_waiting_room_members(interaction.guild)
                
                if target_user in waiting_members:
                    # Auto-register user found in waiting room
                    logger.info(f"Auto-registering {target_user.display_name} from waiting room for /stats")
                    user_data = await api_client.auto_register_user(
                        guild_id=interaction.guild.id,
                        user_id=target_user.id,
                        username=target_user.display_name
                    )
                    
                    if user_data:
                        # Convert to completed stats format
                        user_data = {
                            'guild_id': user_data['guild_id'],
                            'user_id': user_data['user_id'],
                            'username': user_data['username'],
                            'region_code': user_data.get('region_code'),
                            'rating_mu': user_data['rating_mu'],
                            'rating_sigma': user_data['rating_sigma'],
                            'games_played': 0,  # New user has no completed matches
                            'wins': 0,
                            'losses': 0,
                            'draws': 0,
                            'created_at': user_data['created_at'],
                            'last_updated': user_data['last_updated']
                        }
                
                if not user_data:
                    if target_user == interaction.user:
                        embed = EmbedTemplates.warning_embed(
                            "Not Registered",
                            "You're not registered yet!\n\n"
                            "**To get registered:**\n"
                            "• Join the **Waiting Room** voice channel, then run `/stats` again\n"
                            "• Or use `/register` to register manually"
                        )
                    else:
                        embed = EmbedTemplates.warning_embed(
                            "User Not Found",
                            f"{target_user.display_name} is not registered in the system.\n\n"
                            f"They can get registered by joining the **Waiting Room** voice channel."
                        )
                    await interaction.followup.send(embed=embed)
                    return
            else:
                # Sync username if user exists and name has changed
                user_data = await self._sync_username_if_needed(interaction.guild.id, target_user, user_data)
            
            # Get teammate statistics (top 5 for each category)
            teammate_stats = await api_client.get_user_teammate_stats(
                guild_id=interaction.guild.id,
                user_id=target_user.id,
                limit=5
            )
            
            # Try to get OpenSkill rating (beta feature)
            openskill_data = None
            try:
                openskill_data = await api_client.get_openskill_rating(interaction.guild.id, target_user.id)
                logger.debug(f"OpenSkill data retrieved for user {target_user.id}: {openskill_data}")
            except Exception as e:
                logger.debug(f"OpenSkill data not available for user {target_user.id}: {e}")
                # This is expected if OpenSkill system isn't fully set up or user has no data
            
            # Create stats embed with completed match data and teammate info
            embed = EmbedTemplates.user_stats_embed(user_data, teammate_stats)
            
            # Add OpenSkill rating as beta feature if available
            if openskill_data and openskill_data.get('games_played', 0) > 0:
                mu = openskill_data.get('mu', 25.0)
                sigma = openskill_data.get('sigma', 8.333)
                display_rating = int(mu * 60)  # Convert to display rating
                games_played = openskill_data.get('games_played', 0)
                
                embed.add_field(
                    name="🧪 OpenSkill Rating (Beta)",
                    value=f"**{display_rating}** ({mu:.1f}μ ± {sigma:.1f}σ)\n"
                          f"Games: {games_played} | Team-based skill assessment",
                    inline=False
                )
            elif openskill_data:
                # User has OpenSkill entry but no games played
                embed.add_field(
                    name="🧪 OpenSkill Rating (Beta)",
                    value="**1500** (25.0μ ± 8.3σ)\n"
                          "Games: 0 | Team-based skill assessment",
                    inline=False
                )
            
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
            await interaction.followup.send(embed=embed)
    
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
    
    @app_commands.command(name="leaderboard", description="Show guild leaderboard (auto-syncs usernames)")
    @app_commands.describe(limit="Number of players to show (default: 10, max: 25)")
    async def leaderboard(self, interaction: discord.Interaction, limit: Optional[int] = 10):
        """Display top players in the guild - shows all registered users"""
        await interaction.response.defer()
        
        # Validate limit
        limit = max(1, min(limit, 25))
        
        try:
            # Auto-register any players currently in waiting room
            waiting_members = await self.voice_manager.get_waiting_room_members(interaction.guild)
            
            if waiting_members:
                logger.info(f"Scanning {len(waiting_members)} waiting room members for auto-registration")
                for member in waiting_members:
                    try:
                        # Check if already registered
                        existing_user = await api_client.get_user(interaction.guild.id, member.id)
                        if not existing_user:
                            # Auto-register new player
                            logger.info(f"Auto-registering {member.display_name} from waiting room for /leaderboard")
                            await api_client.auto_register_user(
                                guild_id=interaction.guild.id,
                                user_id=member.id,
                                username=member.display_name
                            )
                        else:
                            # Sync username for existing user
                            await self._sync_username_if_needed(interaction.guild.id, member, existing_user)
                    except Exception as e:
                        logger.error(f"Error processing {member.display_name}: {e}")
            
            # Get users with completed match statistics (includes users with 0 completed matches)
            users = await api_client.get_guild_users_completed_stats(interaction.guild.id)
            
            if not users:
                embed = EmbedTemplates.warning_embed(
                    "No Players Found",
                    "No players are registered in this guild yet!\n\n"
                    "**To get registered:**\n"
                    "• Join the **Waiting Room** voice channel, then run `/leaderboard` again\n"
                    "• Or use `/register` to register manually"
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Sync usernames for all users in the leaderboard
            users = await self._sync_multiple_usernames(interaction.guild, users)
            
            # Sort by rating (mu) descending, then by games played descending
            users.sort(key=lambda x: (x.get("rating_mu", 1500), x.get("games_played", 0)), reverse=True)
            
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
    
    @app_commands.command(name="match_history", description="Show recent completed match history")
    @app_commands.describe(
        user="The user to show history for (defaults to yourself)",
        limit="Number of completed matches to show (default: 10, max: 10)"
    )
    async def match_history(self, interaction: discord.Interaction, 
                           user: Optional[discord.Member] = None, 
                           limit: Optional[int] = 10):
        """Display completed match history only"""
        await interaction.response.defer(ephemeral=True)
        
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
                await interaction.followup.send(embed=embed)
                return
            
            # Get completed match history only
            matches = await api_client.get_user_completed_match_history(
                guild_id=interaction.guild.id,
                user_id=target_user.id,
                limit=limit
            )
            
            # Get user's current rank for display
            current_rank = await self._get_user_rank(interaction.guild.id, target_user.id)
            
            embed = EmbedTemplates.match_history_embed(
                matches=matches,
                username=target_user.display_name,
                current_rank=current_rank,
                current_rating=user_data.get('rating_mu', 0)
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
            await interaction.followup.send(embed=embed)
    
    async def _get_user_rank(self, guild_id: int, user_id: int) -> int:
        """Get user's current rank in the guild leaderboard"""
        try:
            # Get all users with completed stats, sorted by rating
            all_users = await api_client.get_guild_users_completed_stats(guild_id)
            
            # Sort by rating (descending)
            sorted_users = sorted(all_users, key=lambda x: x.get('rating_mu', 0), reverse=True)
            
            # Find user's position
            for i, user_data in enumerate(sorted_users, 1):
                if user_data.get('user_id') == user_id:
                    return i
            
            return len(sorted_users) + 1  # If not found, put at end
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            return 0  # Return 0 if error
    

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


    @app_commands.command(name="rating_scale", description="Show the Placement Rating System v4.0.0 - balanced for long-term progression")
    async def rating_scale(self, interaction: discord.Interaction):
        """Show the placement rating scale explanation"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            embed = discord.Embed(
                title="🏆 Placement Rating System v4.0.0",
                description="**Balanced for long-term progression**\n"
                           "**Key Feature**: 5th place = 0 points (balanced baseline)\n"
                           "**Range**: +15 (1st place) to -25 (30th place)",
                color=Config.EMBED_COLOR
            )
            
            # Positive tiers
            embed.add_field(
                name="🎯 Positive Tiers",
                value="🥇 **1st Place**: +15 points (Champion)\n"
                      "🥈 **2nd Place**: +10 points (Excellent)\n"
                      "🥉 **3rd Place**: +5 points (Great)\n"
                      "🏆 **4th Place**: +2 points (Good)\n"
                      "⚖️ **5th Place**: 0 points (Baseline)",
                inline=True
            )
            
            # Penalty tiers
            embed.add_field(
                name="📉 Penalty Tiers",
                value="📉 **6th Place**: -3 points\n"
                      "📉 **7th Place**: -6 points\n"
                      "🔻 **8th Place**: -10 points\n"
                      "💀 **9th-30th**: -10 to -25 points\n"
                      "💀 **30th+ Place**: -25 points (max)",
                inline=True
            )
            
            embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer
            
            # Rating progression targets
            embed.add_field(
                name="🎯 Rating Progression Targets",
                value="🏆 **Great Players**: ~2000 (avg +10/game)\n"
                      "⚖️ **Normal Players**: ~1500 (avg 0/game)\n"
                      "📉 **Struggling Players**: ~1000 (avg -10/game)\n"
                      "🌱 **New Players**: ~800 (learning phase)",
                inline=True
            )
            
            # Rating tiers (simplified)
            embed.add_field(
                name="🏆 Rating Tiers",
                value="🏆 **Elite (2000+)**: Top performers\n"
                      "🥇 **Advanced (1600+)**: Strong players\n"
                      "⚖️ **Average (1200-1600)**: Normal range\n"
                      "📊 **Developing (800-1200)**: Learning phase\n"
                      "🌱 **New (<800)**: Just starting",
                inline=True
            )
            
            # System features
            embed.add_field(
                name="✨ System Features",
                value="• **Balanced baseline** - 5th place = no change\n"
                      "• **Moderate rewards** - encourages consistent play\n"
                      "• **Escalating penalties** - discourages poor performance\n"
                      "• **Long-term progression** - designed for ~50 games\n"
                      "• **Simple & fair** - no complex multipliers",
                inline=False
            )
            
            # Examples
            embed.add_field(
                name="📊 Example Progressions",
                value="**Consistent 3rd place**: +5 × 50 games = +250 total (1750 rating)\n"
                      "**Mix of 1st-5th**: Avg +5/game = +250 total (1750 rating)\n"
                      "**Consistent 7th place**: -6 × 50 games = -300 total (1200 rating)\n"
                      "**Very poor performance**: Avg -15/game = -750 total (750 rating)",
                inline=False
            )
            
            embed.set_footer(text=f"Placement Rating System v4.0.0 • {get_bot_footer_text()}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in rating_scale command: {e}")
            embed = EmbedTemplates.error_embed(
                "Rating Scale Error",
                "Failed to display rating scale. Please try again later."
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserCommands(bot))