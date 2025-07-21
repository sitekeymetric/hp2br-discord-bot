import discord
from discord.ext import commands
import random
import asyncio
from typing import List, Optional
import re,os
import certifi

# Bot setup
#intents = discord.Intents.default()
intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
#os.environ["SSL_CERT_FILE"] = certifi.where()
#print(os.environ["SSL_CERT_FILE"])

bot = commands.Bot(command_prefix='!', intents=intents)

class CleanupView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)  # 5 minutes timeout
    
    @discord.ui.button(label='🧹 Cleanup Debug Channels', style=discord.ButtonStyle.red)
    async def cleanup_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user has permissions
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message(
                "❌ You need 'Manage Channels' permission to use this button!", 
                ephemeral=True
            )
            return
        
        guild = interaction.guild
        deleted_count = await cleanup_old_channels(guild)
        
        if deleted_count > 0:
            await interaction.response.send_message(
                f"✅ Cleaned up {deleted_count} team channels!", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "ℹ️ No team channels found to clean up.", 
                ephemeral=True
            )
        
        # Disable the button after use
        button.disabled = True
        await interaction.edit_original_response(view=self)

class TeamGenerator:
    def __init__(self):
        self.created_channels = {}  # Guild ID -> List of created channel IDs
    
    def parse_team_format(self, format_str: str) -> List[int]:
        """Parse team format like '4:4:2' into [4, 4, 2]"""
        try:
            teams = [int(x) for x in format_str.split(':')]
            if any(team <= 0 for team in teams):
                raise ValueError("Team sizes must be positive")
            return teams
        except ValueError:
            raise ValueError("Invalid format. Use format like '4:4:2' for team sizes")
    
    def create_teams(self, members: List[discord.Member], team_sizes: List[int]) -> List[List[discord.Member]]:
        """Create random teams based on specified sizes"""
        total_needed = sum(team_sizes)
        if len(members) < total_needed:
            raise ValueError(f"Not enough members! Need {total_needed}, but only {len(members)} available")
        
        # Shuffle members randomly
        shuffled_members = members.copy()
        random.shuffle(shuffled_members)
        
        teams = []
        current_index = 0
        
        for size in team_sizes:
            team = shuffled_members[current_index:current_index + size]
            teams.append(team)
            current_index += size
        
        return teams
    
    async def create_team_channels(self, guild: discord.Guild, category: discord.CategoryChannel, 
                                 teams: List[List[discord.Member]]) -> List[discord.VoiceChannel]:
        """Create voice channels for each team"""
        created_channels = []
        
        for i, team in enumerate(teams, 1):
            channel_name = f"HP2BR-Team-{i}"
            
            # Create the voice channel
            channel = await guild.create_voice_channel(
                name=channel_name,
                category=category,
                reason="Team generator bot - creating team channels"
            )
            
            created_channels.append(channel)
            
            # Move members to the new channel
            for member in team:
                try:
                    await member.move_to(channel)
                except discord.HTTPException:
                    print(f"Failed to move {member.display_name} to {channel_name}")
        
        return created_channels

team_gen = TeamGenerator()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready and connected to {len(bot.guilds)} guilds')

async def create_debug_channel(ctx):
    """Create a debug voice channel and move the caller to it"""
    guild = ctx.guild
    author = ctx.author
    
    try:
        # Find or create a category for team channels
        category = discord.utils.get(guild.categories, name="HP2BR Auto Teams")
        if not category:
            category = await guild.create_category("HP2BR Auto Teams")
        
        # Check if debug channel already exists
        existing_debug = discord.utils.get(guild.voice_channels, name="HP2BR-Debug")
        if existing_debug:
            # Move user to existing debug channel
            await author.move_to(existing_debug)
            await ctx.send(f"✅ Moved you to existing debug channel: {existing_debug.mention}")
            return
        
        # Create the debug voice channel
        debug_channel = await guild.create_voice_channel(
            name="HP2BR-Debug",
            category=category,
            reason="Debug channel created by team bot"
        )
        
        # Move the caller to the debug channel
        await author.move_to(debug_channel)
        
        # Store the channel for cleanup
        if guild.id not in team_gen.created_channels:
            team_gen.created_channels[guild.id] = []
        team_gen.created_channels[guild.id].append(debug_channel.id)
        
        # Send confirmation with cleanup button
        embed = discord.Embed(
            title="🐛 Debug Channel Created!",
            description=f"Created debug channel and moved {author.display_name} to it.",
            color=0xffaa00
        )
        embed.add_field(
            name="Channel",
            value=debug_channel.mention,
            inline=False
        )
        
        view = CleanupView()
        await ctx.send(embed=embed, view=view)
        
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to create channels or move members!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred while creating debug channel: {str(e)}")

@bot.command(name='teams', help='Generate random teams from voice channel members. Usage: !teams 4:4:2 or !teams debug')
async def generate_teams(ctx, team_format: str = None):
    """Generate random teams from voice channel members or create debug channel"""
    
    # Check if user is in a voice channel
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ You need to be in a voice channel to use this command!")
        return
    
    # Handle debug command
    if team_format and team_format.lower() == 'debug':
        await create_debug_channel(ctx)
        return
    
    # Check if format is provided
    if not team_format:
        await ctx.send("❌ Please specify team format! Example: `!teams 4:4:2` or `!teams debug`")
        return
    
    voice_channel = ctx.author.voice.channel
    guild = ctx.guild
    
    # Get members in the voice channel (exclude bots)
    members = [member for member in voice_channel.members if not member.bot]
    
    if len(members) < 2:
        await ctx.send("❌ Need at least 2 members in the voice channel!")
        return
    
    try:
        # Parse team format
        team_sizes = team_gen.parse_team_format(team_format)
        
        # Create teams
        teams = team_gen.create_teams(members, team_sizes)
        
        # Find or create a category for team channels
        category = discord.utils.get(guild.categories, name="HP2BRTeams")
        if not category:
            category = await guild.create_category("HP2BRTeams")
        
        # Clean up old team channels first
        await cleanup_old_channels(guild)
        
        # Create team channels and move members
        created_channels = await team_gen.create_team_channels(guild, category, teams)
        
        # Store created channels for cleanup
        if guild.id not in team_gen.created_channels:
            team_gen.created_channels[guild.id] = []
        team_gen.created_channels[guild.id].extend([ch.id for ch in created_channels])
        
        # Create response embed
        embed = discord.Embed(
            title="🎯 Teams Generated!",
            description=f"Created {len(teams)} teams from {len(members)} members",
            color=0x00ff00
        )
        
        for i, team in enumerate(teams, 1):
            team_names = [member.display_name for member in team]
            embed.add_field(
                name=f"Team {i} ({len(team)} members)",
                value="\n".join(f"• {name}" for name in team_names),
                inline=True
            )
        
        embed.set_footer(text="Members have been moved to their team channels!")
        await ctx.send(embed=embed)
        
    except ValueError as e:
        await ctx.send(f"❌ {str(e)}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to create channels or move members!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@bot.command(name='cleanup', help='Clean up all HP2BR team channels')
async def cleanup_teams(ctx):
    """Clean up all created team channels"""
    if not ctx.author.guild_permissions.manage_channels:
        await ctx.send("❌ You need 'Manage Channels' permission to use this command!")
        return
    
    guild = ctx.guild
    deleted_count = await cleanup_old_channels(guild)
    
    if deleted_count > 0:
        await ctx.send(f"✅ Cleaned up {deleted_count} team channels!")
    else:
        await ctx.send("ℹ️ No team channels found to clean up.")

async def cleanup_old_channels(guild: discord.Guild):
    """Clean up old HP2BR team channels, debug channels, and empty categories"""
    deleted_count = 0
    
    # Find all HP2BR team channels and debug channels
    for channel in guild.voice_channels:
        if channel.name.startswith("HP2BR-Team-") or channel.name == "HP2BR-Debug":
            try:
                await channel.delete(reason="Team generator cleanup")
                deleted_count += 1
            except discord.HTTPException:
                print(f"Failed to delete channel {channel.name}")
    
    # Clean up empty categories
    categories_to_check = ["HP2BR Auto Teams", "HP2BRTeams"]
    for category_name in categories_to_check:
        category = discord.utils.get(guild.categories, name=category_name)
        if category:
            # Check if category is empty (no channels)
            if len(category.channels) == 0:
                try:
                    await category.delete(reason="Team generator cleanup - empty category")
                    print(f"Deleted empty category: {category_name}")
                except discord.HTTPException:
                    print(f"Failed to delete category {category_name}")
    
    # Clear stored channel IDs
    if guild.id in team_gen.created_channels:
        team_gen.created_channels[guild.id] = []
    
    return deleted_count

@bot.command(name='teamhelp', help='Show detailed help for team commands')
async def team_help(ctx):
    """Show detailed help information"""
    embed = discord.Embed(
        title="🤖 Team Generator Bot Help",
        description="Generate random teams from voice channel members!",
        color=0x0099ff
    )
    
    embed.add_field(
        name="📋 Commands",
        value=(
            "`!teams <format>` - Generate teams\n"
            "`!teams debug` - Create debug channel\n"
            "`!cleanup` - Clean up team channels\n"
            "`!teamhelp` - Show this help"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📝 Team Format Examples",
        value=(
            "`!teams 4:4` - Two teams of 4 members each\n"
            "`!teams 3:3:2` - Two teams of 3, one team of 2\n"
            "`!teams 5:5:5:5` - Four teams of 5 members each\n"
            "`!teams debug` - Create HP2BR-Debug channel"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎯 How it works",
        value=(
            "1. Join a voice channel\n"
            "2. Run `!teams <format>` or `!teams debug`\n"
            "3. Bot creates team/debug channels and moves members\n"
            "4. Use `!cleanup` to remove channels when done"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Requirements",
        value=(
            "• Bot needs 'Manage Channels' and 'Move Members' permissions\n"
            "• You must be in a voice channel\n"
            "• Enough members for the specified team sizes (teams only)"
        ),
        inline=False
    )
    
    embed.set_footer(text="Team channels are created in the 'HP2BRTeams' category")
    await ctx.send(embed=embed)

@generate_teams.error
async def teams_error(ctx, error):
    """Error handler for teams command"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Please specify team format! Example: `!teams 4:4:2` or `!teams debug`")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")

# Run the bot
if __name__ == "__main__":
    print("Starting Discord Team Generator Bot...")
    print("Make sure to:")
    print("1. Replace 'YOUR_BOT_TOKEN' with your actual bot token")
    print("2. Invite the bot with proper permissions:")
    print("   - Manage Channels")
    print("   - Move Members") 
    print("   - Send Messages")
    print("   - Connect to Voice Channels")
    
    # Replace with your bot token
    # print(os.environ["DISCORD_TOKEN"])
    bot.run(os.environ["DISCORD_TOKEN"])

