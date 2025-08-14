import discord
from discord.ext import commands
import asyncio
import logging
from utils.constants import Config
from utils.version import print_startup_version, get_version_embed_field
import aiohttp

# Set up logging
logging.basicConfig(
    level=logging.INFO if not Config.DEBUG_MODE else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(
    command_prefix='!',  # Fallback prefix, mainly using slash commands
    intents=intents,
    help_command=None  # Disable default help command
)

async def sync_commands_with_retry():
    """
    Sync slash commands with proper rate limit handling.
    Respects Discord's Retry-After header and implements exponential backoff.
    """
    max_retries = Config.SYNC_RETRY_ATTEMPTS
    base_delay = Config.SYNC_BASE_DELAY
    
    for attempt in range(max_retries + 1):
        try:
            logger.info(f'Attempting to sync commands (attempt {attempt + 1}/{max_retries + 1})')
            synced = await bot.tree.sync()
            logger.info(f'Successfully synced {len(synced)} command(s)')
            return synced
            
        except discord.HTTPException as e:
            if e.status == 429:  # Rate limited
                # Print complete response headers for debugging (if enabled)
                if Config.SYNC_DEBUG_HEADERS:
                    logger.warning("=== DISCORD RATE LIMIT RESPONSE (429) ===")
                    logger.warning(f"Status Code: {e.status}")
                    logger.warning(f"Response Text: {e.text}")
                    
                    # Print all available response headers
                    if hasattr(e, 'response') and e.response:
                        logger.warning("Response Headers:")
                        if hasattr(e.response, 'headers'):
                            for key, value in e.response.headers.items():
                                logger.warning(f"  {key}: {value}")
                        else:
                            logger.warning("  No headers attribute found on response")
                        
                        # Also try to access the raw aiohttp response if available
                        if hasattr(e.response, '_response'):
                            logger.warning("Raw aiohttp Response Headers:")
                            try:
                                raw_response = e.response._response
                                if hasattr(raw_response, 'headers'):
                                    for key, value in raw_response.headers.items():
                                        logger.warning(f"  {key}: {value}")
                            except Exception as header_ex:
                                logger.warning(f"  Could not access raw headers: {header_ex}")
                    else:
                        logger.warning("  No response object available")
                    
                    # Print all exception attributes
                    logger.warning("Exception Attributes:")
                    for attr in dir(e):
                        if not attr.startswith('_'):
                            try:
                                value = getattr(e, attr)
                                if not callable(value):
                                    logger.warning(f"  {attr}: {value}")
                            except:
                                logger.warning(f"  {attr}: <could not access>")
                    
                    logger.warning("========================================")
                
                # Extract retry_after from the exception
                retry_after = getattr(e, 'retry_after', None)
                if retry_after is None:
                    # Fallback to exponential backoff if no retry_after
                    retry_after = base_delay * (2 ** attempt)
                
                logger.warning(f'Rate limited (429). Retry-After: {retry_after}s. Waiting...')
                
                if attempt < max_retries:
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    logger.error(f'Failed to sync commands after {max_retries + 1} attempts due to rate limiting')
                    logger.error(f'Discord is heavily rate limiting command syncing. Please wait {retry_after}s before restarting.')
                    return None
            else:
                logger.error(f'HTTP error during command sync: {e.status} {e.text}')
                if attempt < max_retries:
                    delay = base_delay * (2 ** attempt)
                    logger.info(f'Retrying in {delay}s...')
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f'Failed to sync commands after {max_retries + 1} attempts')
                    return None
                    
        except Exception as e:
            logger.error(f'Unexpected error during command sync: {e}')
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)
                logger.info(f'Retrying in {delay}s...')
                await asyncio.sleep(delay)
                continue
            else:
                logger.error(f'Failed to sync commands after {max_retries + 1} attempts')
                return None
    
    return None

@bot.event
async def on_ready():
    """Bot startup event"""
    print_startup_version()  # Display version info at startup
    logger.info(f'{bot.user} has connected to Discord!')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')
    
    # Sync slash commands with rate limit handling (if enabled)
    if Config.SYNC_COMMANDS_ON_STARTUP:
        synced = await sync_commands_with_retry()
        if synced is None:
            logger.warning('Command syncing failed, but bot will continue running with existing commands')
    else:
        logger.info('Command syncing disabled via SYNC_COMMANDS=false')
    
    # Set bot status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="for team balance opportunities"
        )
    )

@bot.event
async def on_guild_join(guild):
    """Handle bot joining a new guild"""
    logger.info(f'Bot joined guild: {guild.name} (ID: {guild.id})')
    
    # Send welcome message to system channel or first available text channel
    channel = guild.system_channel or discord.utils.get(guild.text_channels, name='general')
    if channel and channel.permissions_for(guild.me).send_messages:
        embed = discord.Embed(
            title="🎮 Team Balance Bot",
            description="Thanks for adding me! I help create balanced teams for competitive games.",
            color=Config.EMBED_COLOR
        )
        embed.add_field(
            name="Getting Started",
            value="• Use `/setup` to configure voice channels\n• Players use `/register` to join the system\n• Use `/create_teams` when players are in the waiting room",
            inline=False
        )
        embed.add_field(
            name="Need Help?",
            value="Use `/help` to see all available commands",
            inline=False
        )
        try:
            await channel.send(embed=embed)
        except Exception as e:
            logger.error(f'Failed to send welcome message in {guild.name}: {e}')

@bot.event
async def on_application_command_error(interaction, error):
    """Global error handler for slash commands"""
    logger.error(f'Command error in {interaction.guild.name if interaction.guild else "DM"}: {error}')
    
    if interaction.response.is_done():
        await interaction.followup.send(
            "❌ An error occurred while processing your command. Please try again.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ An error occurred while processing your command. Please try again.",
            ephemeral=True
        )


@bot.tree.command(name="help", description="Show all available commands")
async def help_command(interaction: discord.Interaction):
    """Display help information"""
    embed = discord.Embed(
        title="🎮 Team Balance Bot Commands",
        description="Create balanced teams for competitive gameplay",
        color=Config.EMBED_COLOR
    )
    
    embed.add_field(
        name="👤 User Commands",
        value="• `/register [region]` - Register in the system\n"
              "• `/stats [@user]` - View player statistics (auto-syncs username, includes OpenSkill beta)\n"
              "• `/set_region <region>` - Update your region\n"
              "• `/leaderboard [limit] [rating_system]` - Show top players (traditional/openskill)\n"
              "• `/delete_account` - Delete your account\n"
              "• `/match_history [@user]` - View match history\n"
              "• `/rating_scale` - View placement-based rating scale",
        inline=False
    )
    
    embed.add_field(
        name="🎯 Team Commands",
        value="• `/create_teams [np] [region] [format] [rating_system]` - Create balanced teams (traditional/openskill)\n"
              "• `/record_result` - Record match results (placement-based)\n"
              "• `/cancel_match` - Cancel current match\n"
              "• `/update_team` - Update team memberships based on voice channels (available to all)\n"
              "• `/cleanup` - Clean up team channels (available to all)",
        inline=False
    )
    
    embed.add_field(
        name="🏆 Placement Rating System v4.0.0",
        value="**Balanced for long-term progression!** All matches now use placement-based ratings:\n"
              "• **5th Place** = 0 points (balanced baseline)\n"
              "• **1st Place** = +15 points maximum\n"
              "• **30th+ Place** = -25 points maximum\n"
              "• **Guild Matches**: Use consecutive ranks (1, 2, 3...)\n"
              "• **External Competitions**: Use actual ranks (1-30)\n"
              "• Use `/rating_scale` to see the full scale",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Admin Commands",
        value="• `/setup` - Initial bot setup\n"
              "• `/admin_cleanup` - Admin cleanup with detailed logging\n"
              "• `/admin_delete_user <@user>` - Delete user account\n"
              "• `/admin_update_user <@user>` - Update user info\n"
              "• `/admin_reset_rating <@user>` - Reset user rating",
        inline=False
    )
    
    embed.add_field(
        name="📝 How to Use",
        value="1. Players join the **Waiting Room** voice channel\n"
              "2. Use `/create_teams` to generate balanced teams\n"
              "3. Players are moved to team voice channels\n"
              "4. After the match, use `/record_result` to update ratings",
        inline=False
    )
    
    embed.add_field(
        name="🚀 New User?",
        value="Use `/getting_started` for a complete beginner's guide!",
        inline=False
    )
    
    # Add version information
    version_field = get_version_embed_field()
    embed.add_field(
        name=version_field["name"],
        value=version_field["value"],
        inline=version_field["inline"]
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="getting_started", description="Complete guide for new players")
async def getting_started(interaction: discord.Interaction):
    """Detailed getting started guide for new users"""
    embed = discord.Embed(
        title="🚀 Getting Started with Team Balance Bot",
        description="Welcome! Here's everything you need to know:",
        color=Config.EMBED_COLOR
    )
    
    embed.add_field(
        name="1️⃣ First Time Setup",
        value="• Use `/register` to join the team balance system\n"
              "• Optionally add your region: `/register NA` (or EU, AS, OCE, etc.)\n"
              "• Check your stats with `/stats` to confirm registration",
        inline=False
    )
    
    embed.add_field(
        name="2️⃣ Joining a Match",
        value="• Join the **Waiting Room** voice channel\n"
              "• Wait for others to join (need at least 6 players)\n"
              "• Someone with permissions uses `/create_teams`\n"
              "• Vote ✅ to accept or ❌ to decline the team proposal",
        inline=False
    )
    
    embed.add_field(
        name="3️⃣ During the Match",
        value="• You'll be automatically moved to your team's voice channel\n"
              "• Play your match with your balanced team\n"
              "• Stay in your team channel until the match ends",
        inline=False
    )
    
    embed.add_field(
        name="4️⃣ After the Match",
        value="• Someone records the result with `/record_result 1` (if Team 1 won)\n"
              "• Your rating will be updated automatically\n"
              "• You'll be moved back to the waiting room\n"
              "• Check your new stats with `/stats`!",
        inline=False
    )
    
    embed.add_field(
        name="🎯 Quick Tips",
        value="• Your rating starts at 1500 and changes based on wins/losses\n"
              "• Better opponents = bigger rating gains when you win\n"
              "• More games = more accurate rating and better team balance\n"
              "• Use `/leaderboard` to see top players in your server",
        inline=False
    )
    
    embed.add_field(
        name="❓ Need More Help?",
        value="• Use `/help` for all available commands\n"
              "• Ask an admin to run `/setup` if voice channels are missing",
        inline=False
    )
    
    embed.set_footer(text="Ready to play? Use /register to get started!")
    
    await interaction.response.send_message(embed=embed)

async def load_extensions():
    """Load all command modules"""
    extensions = [
        'commands.user_commands',
        'commands.team_commands', 
        'commands.admin_commands',
        'commands.openskill_commands'  # OpenSkill parallel rating system
        # 'commands.advanced_rating_commands'  # Advanced Rating System v3.0 - Disabled due to conflicts
    ]
    
    for extension in extensions:
        try:
            await bot.load_extension(extension)
            logger.info(f'Loaded extension: {extension}')
        except Exception as e:
            logger.error(f'Failed to load extension {extension}: {e}')

async def main():
    """Main bot startup function"""
    try:
        # Load command extensions
        await load_extensions()
        
        # Start the bot
        logger.info('Starting bot...')
        await bot.start(Config.DISCORD_TOKEN)
        
    except Exception as e:
        logger.error(f'Failed to start bot: {e}')
    finally:
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info('Bot shutdown requested by user')
    except Exception as e:
        logger.error(f'Fatal error: {e}')