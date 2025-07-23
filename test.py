import discord
from discord.ext import commands
import base64
import aiohttp
import os
import asyncio
import logging

# Configure logging to provide more detailed output for debugging.
# This helps in tracking the bot's activities and identifying potential issues.
logging.basicConfig(level=logging.INFO, format='%(asctime)s:%(levelname)s:%(name)s: %(message)s')
_log = logging.getLogger(__name__)

# --- Bot Setup ---
# Define the intents your bot will use. Intents are a way for Discord to tell your bot
# which types of events it wants to receive. This helps in scaling and performance.
# - message_content: Required to read the content of messages, essential for processing commands.
# - guilds: Necessary to access guild (server) specific information, like channels and members.
# - voice_states: Crucial for the bot to interact with voice channels (joining, leaving, playing audio).
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

# Retrieve the bot token from environment variables.
# It is highly recommended to store your bot token securely as an environment variable
# rather than hardcoding it directly in your script. This prevents accidental exposure.
TOKEN = os.environ.get("DISCORD_TOKEN")

# Check if the token is available. If not, exit with an error.
if TOKEN is None:
    _log.error("DISCORD_TOKEN environment variable not set. Please set it before running the bot.")
    exit(1)

# Create an instance of commands.AutoShardedBot.
# AutoShardedBot automatically handles sharding, which is Discord's way of distributing
# large bots across multiple gateway connections. This improves scalability and reliability.
# For smaller bots, it still provides a robust connection mechanism.
bot = commands.AutoShardedBot(command_prefix='!', intents=intents)

# --- Event: on_ready ---
@bot.event
async def on_ready():
    """
    This event fires when the bot successfully connects to Discord and is ready to operate.
    It's a good place to confirm the bot's login status and perform any startup tasks.
    """
    _log.info(f'Logged in as {bot.user} (ID: {bot.user.id})')
    _log.info(f'Bot is ready and serving {len(bot.guilds)} guilds.')
    _log.info('------')

# --- Command: createsoundboard ---
@bot.command(
    name="createsoundboard",
    help="Creates a new soundboard sound in the current server. Usage: !createsoundboard <sound_name> [emoji_name] [volume (0-100)]"
)

# --- Command: playsoundboard ---
@bot.command(
    name="playsoundboard",
    help="Plays a native soundboard sound in the 'Waiting Room' voice channel. Usage: !playsoundboard <sound_name>"
)
async def playsoundboard(ctx: commands.Context, sound_name: str):
    """
    Plays an existing native Discord soundboard sound in the 'Waiting Room' voice channel.
    The bot will automatically join the 'Waiting Room' channel if it's not already connected.

    Args:
        ctx (commands.Context): The context object for the command invocation.
        sound_name (str): The name of the soundboard sound to play.
    """
    if not ctx.guild:
        await ctx.send("This command can only be used in a server.")
        return

    _log.info(f"Command 'playsoundboard' invoked by {ctx.author} for sound '{sound_name}' in guild {ctx.guild.name}.")

    # Find the sound ID using the helper function. This ID is essential for the API call.
    sound_id = await _get_sound_id_by_name(ctx.guild, sound_name)
    if not sound_id:
        await ctx.send(f"Could not find a soundboard sound named '{sound_name}' in this server.")
        _log.warning(f"Sound '{sound_name}' not found for playing.")
        return
    else:
        await ctx.send(f"Found sound ID for '{sound_name}': `{sound_id}`")

    # Locate the target voice channel.
    # Using discord.utils.get is a convenient way to find an object in a collection.
    waiting_room_channel = discord.utils.get(ctx.guild.voice_channels, name="Waiting Room")

    if not waiting_room_channel:
        await ctx.send("Could not find a voice channel named 'Waiting Room'. "
                       "Please ensure such a channel exists in this server.")
        _log.error(f"Voice channel 'Waiting Room' not found in guild {ctx.guild.name}.")
        return

    # Check the bot's current voice connection status in the guild.
    voice_client = ctx.guild.voice_client

    # If the bot is not connected, or connected to a different channel, connect to 'Waiting Room'.
    if voice_client is None or voice_client.channel != waiting_room_channel:
        _log.info(f"Bot not connected to 'Waiting Room' or connected elsewhere. Attempting to join.")
        try:
            # If already connected to another channel, disconnect gracefully first.
            if voice_client:
                await voice_client.disconnect()
                _log.info(f"Disconnected from previous voice channel: {voice_client.channel.name}.")
            
            # Connect to the desired voice channel.
            voice_client = await waiting_room_channel.connect()
            await ctx.send(f"Joined voice channel: {waiting_room_channel.name}")
            _log.info(f"Successfully joined voice channel: {waiting_room_channel.name} ({waiting_room_channel.id}).")
        except discord.ClientException:
            # This can happen if the bot is already in the process of connecting.
            await ctx.send("Already connecting or connected to a voice channel. Please wait or try again.")
            _log.warning(f"ClientException during voice channel connection for guild {ctx.guild.id}.")
            return
        except discord.Forbidden:
            # This specific error indicates missing permissions.
            await ctx.send("I don't have permissions to join the 'Waiting Room' voice channel. "
                           "Please ensure my role has 'Connect' and 'Speak' permissions in that channel, "
                           "and that the 'Voice State' intent is enabled in the Discord Developer Portal.")
            _log.error(f"Forbidden to join voice channel {waiting_room_channel.name} in guild {ctx.guild.id}. Check permissions.")
            return
        except Exception as e:
            # Catch any other unexpected errors during voice channel connection.
            await ctx.send(f"An unexpected error occurred while trying to join the voice channel: {e}")
            _log.exception(f"Unexpected error joining voice channel {waiting_room_channel.name} in guild {ctx.guild.id}.")
            return

    # Prepare the JSON payload for playing the soundboard sound via API.
    # Discord API requires `sound_id` and `source_guild_id`.
    payload = {
        "sound_id": sound_id,
        "source_guild_id": str(ctx.guild.id) # Guild ID must be a string
    }

    # Define the Discord API endpoint for sending soundboard sounds to a channel.
    api_url = f"https://discord.com/api/v9/channels/{waiting_room_channel.id}/send-soundboard-sound"

    # Set up HTTP headers for the request.
    headers = {
        "Authorization": f"Bot {bot.http.token}",
        "Content-Type": "application/json"
    }

    await ctx.send(f"Attempting to play sound '{sound_name}' in '{waiting_room_channel.name}'...")
    _log.info(f"Sending POST request to {api_url} for playing sound '{sound_name}'.")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, headers=headers, json=payload) as response:
                if response.status == 204: # HTTP 204 No Content indicates success for this endpoint.
                    await ctx.send(f"Successfully played sound '{sound_name}' in '{waiting_room_channel.name}'.")
                    _log.info(f"Sound '{sound_name}' played successfully.")
                else:
                    # Handle API errors.
                    response_data = await response.json()
                    error_message = response_data.get('message', 'Unknown error')
                    await ctx.send(f"Failed to play soundboard sound: {error_message} "
                                   f"(Status: {response.status})")
                    _log.error(f"Discord API Error playing sound '{sound_name}': Status {response.status}, Message: {error_message}, Response: {response_data}")

    except aiohttp.ClientError as e:
        await ctx.send(f"An HTTP error occurred while trying to connect to Discord API: {e}")
        _log.exception(f"Aiohttp client error during sound playback for '{sound_name}'.")
    except Exception as e:
        await ctx.send(f"An unexpected error occurred: {e}")
        _log.exception(f"An unexpected error occurred during sound playback for '{sound_name}'.")
    finally:
        # The bot remains connected after playing. You might consider adding a !leave command
        # or an auto-disconnect after a period of inactivity.
        pass

# --- Run the Bot ---
# This is the entry point for the bot. It starts the connection to Discord.
# The `bot.run()` method is blocking and will keep the script running.
try:
    _log.info("Starting Discord bot...")
    bot.run(TOKEN)
except discord.LoginFailure:
    _log.critical("Failed to log in. Check your DISCORD_TOKEN. It might be invalid or missing.")
except discord.HTTPException as e:
    _log.critical(f"HTTP exception during bot startup: {e}. This could be a network issue or Discord API problem.")
except Exception as e:
    _log.critical(f"An unhandled exception occurred during bot execution: {e}", exc_info=True)
