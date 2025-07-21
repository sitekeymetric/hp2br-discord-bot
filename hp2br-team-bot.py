import discord
from discord.ext import commands
import random
import asyncio
from typing import List, Optional, Tuple
import re, os
import certifi
import sqlite3
import statistics
from itertools import combinations

# Bot setup
intents = discord.Intents.all()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

class PlayerDatabase:
    def __init__(self, db_path: str = "hp2br_players.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the SQLite database and create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    skill_level INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
    
    def add_or_update_player(self, user_id: int, username: str, skill_level: int = 1):
        """Add a new player or update existing player's skill level"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO players (user_id, username, skill_level, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, username, skill_level))
            conn.commit()
    
    def get_player(self, user_id: int) -> Optional[Tuple[int, str, int]]:
        """Get player information by user ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, username, skill_level FROM players WHERE user_id = ?', (user_id,))
            return cursor.fetchone()
    
    def get_all_players(self) -> List[Tuple[int, str, int]]:
        """Get all players from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, username, skill_level FROM players ORDER BY username')
            return cursor.fetchall()
    
    def get_player_skill(self, user_id: int) -> int:
        """Get player's skill level, return 1 if not found"""
        player = self.get_player(user_id)
        return player[2] if player else 1
    
    def set_player_skill(self, user_id: int, username: str, skill_level: int) -> bool:
        """Set player's skill level (1-10)"""
        if not 1 <= skill_level <= 10:
            return False
        self.add_or_update_player(user_id, username, skill_level)
        return True

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
        self.db = PlayerDatabase()
    
    def parse_team_format(self, format_str: str) -> Tuple[List[int], bool]:
        """Parse team format like '4:4:2' or '3:3:3 balanced' into ([4, 4, 2], balanced_flag)"""
        try:
            # Check for 'balanced' keyword
            balanced = 'balanced' in format_str.lower()
            
            # Remove 'balanced' keyword and clean up the format string
            clean_format = format_str.lower().replace('balanced', '').strip()
            
            teams = [int(x) for x in clean_format.split(':')]
            if any(team <= 0 for team in teams):
                raise ValueError("Team sizes must be positive")
            return teams, balanced
        except ValueError:
            raise ValueError("Invalid format. Use format like '4:4:2' or '4:4:2 balanced' for team sizes")
    
    def create_random_teams(self, members: List[discord.Member], team_sizes: List[int]) -> List[List[discord.Member]]:
        """Create random teams without considering skill levels"""
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
    
    def create_balanced_teams(self, members: List[discord.Member], team_sizes: List[int]) -> List[List[discord.Member]]:
        """Create balanced teams considering skill levels"""
        total_needed = sum(team_sizes)
        if len(members) < total_needed:
            raise ValueError(f"Not enough members! Need {total_needed}, but only {len(members)} available")
        
        # Ensure all players are in database with at least skill level 1
        for member in members:
            if not self.db.get_player(member.id):
                self.db.add_or_update_player(member.id, member.display_name, 1)
        
        # Get member skill levels
        member_skills = []
        for member in members[:total_needed]:  # Only consider the needed members
            skill = self.db.get_player_skill(member.id)
            member_skills.append((member, skill))
        
        # Try to create balanced teams using a heuristic approach
        best_teams = None
        best_balance_score = float('inf')
        
        # Try multiple random arrangements to find the best balance
        for attempt in range(1000):  # Try up to 1000 combinations
            shuffled = member_skills.copy()
            random.shuffle(shuffled)
            
            teams = []
            current_index = 0
            team_averages = []
            
            # Create teams
            for size in team_sizes:
                team_members = shuffled[current_index:current_index + size]
                teams.append([member for member, skill in team_members])
                
                # Calculate team average skill
                team_avg = sum(skill for member, skill in team_members) / size
                team_averages.append(team_avg)
                current_index += size
            
            # Calculate balance score (lower is better)
            if len(team_averages) > 1:
                balance_score = max(team_averages) - min(team_averages)
            else:
                balance_score = 0
            
            # Keep the best balanced teams
            if balance_score < best_balance_score:
                best_balance_score = balance_score
                best_teams = teams.copy()
                
                # If we found perfect balance, stop searching
                if balance_score < 0.1:
                    break
        
        return best_teams if best_teams else self.create_random_teams(members, team_sizes)
    
    def calculate_team_stats(self, teams: List[List[discord.Member]]) -> List[Tuple[float, List[int]]]:
        """Calculate team statistics (average skill, individual skills)"""
        team_stats = []
        for team in teams:
            skills = []
            for member in team:
                skill = self.db.get_player_skill(member.id)
                skills.append(skill)
            
            avg_skill = sum(skills) / len(skills) if skills else 1.0
            team_stats.append((avg_skill, skills))
        
        return team_stats
    
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

# Initialize global instances
team_gen = TeamGenerator()
player_db = PlayerDatabase()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready and connected to {len(bot.guilds)} guilds')
    print(f'Player database initialized at: {player_db.db_path}')

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

@bot.group(name='teams', help='Team management commands', invoke_without_command=True)
async def teams_group(ctx, *, team_format: str = None):
    """Generate random or balanced teams from voice channel members or create debug channel"""
    
    # Handle debug command
    if team_format and team_format.lower() == 'debug':
        # Check if user is in a voice channel for debug
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("❌ You need to be in a voice channel to create a debug channel!")
            return
        await create_debug_channel(ctx)
        return
    
    # Check if format is provided
    if not team_format:
        await ctx.send("❌ Please specify team format! Example: `!teams 4:4:2` or `!teams 3:3:3 balanced`")
        return
    
    # Check if user is in a voice channel for team generation
    if not ctx.author.voice or not ctx.author.voice.channel:
        await ctx.send("❌ You need to be in a voice channel to generate teams!")
        return
    
    voice_channel = ctx.author.voice.channel
    guild = ctx.guild
    
    # Get members in the voice channel (exclude bots)
    members = [member for member in voice_channel.members if not member.bot]
    
    if len(members) < 2:
        await ctx.send("❌ Need at least 2 members in the voice channel to generate teams!")
        return
    
    try:
        # Parse team format
        team_sizes, balanced = team_gen.parse_team_format(team_format)
        
        # Create teams (balanced or random)
        if balanced:
            teams = team_gen.create_balanced_teams(members, team_sizes)
            team_type = "Balanced Teams"
        else:
            teams = team_gen.create_random_teams(members, team_sizes)
            team_type = "Random Teams"
        
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
        
        # Calculate team statistics
        team_stats = team_gen.calculate_team_stats(teams)
        
        # Create response embed
        embed = discord.Embed(
            title=f"🎯 {team_type} Generated!",
            description=f"Created {len(teams)} teams from {len(members)} members",
            color=0x00ff00 if not balanced else 0x0099ff
        )
        
        for i, (team, (avg_skill, skills)) in enumerate(zip(teams, team_stats), 1):
            team_names = []
            for j, member in enumerate(team):
                skill = skills[j]
                team_names.append(f"• {member.display_name} (Skill: {skill})")
            
            field_value = "\n".join(team_names)
            if balanced:
                field_value += f"\n**Average Skill: {avg_skill:.1f}**"
            
            embed.add_field(
                name=f"Team {i} ({len(team)} members)",
                value=field_value,
                inline=True
            )
        
        if balanced and len(team_stats) > 1:
            skill_averages = [stats[0] for stats in team_stats]
            balance_score = max(skill_averages) - min(skill_averages)
            embed.add_field(
                name="Balance Score",
                value=f"{balance_score:.2f} (lower is better)",
                inline=False
            )
        
        embed.set_footer(text="Members have been moved to their team channels!")
        await ctx.send(embed=embed)
        
    except ValueError as e:
        await ctx.send(f"❌ {str(e)}")
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to create channels or move members!")
    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")

@teams_group.command(name='skill', help='Set or view player skill level (1-10)')
async def skill_command(ctx, member: Optional[discord.Member] = None, skill_level: Optional[int] = None):
    """Set or view player skill level"""
    
    # If no member specified, use the command author
    if member is None:
        member = ctx.author
    
    # If no skill level specified, show current skill
    if skill_level is None:
        current_skill = player_db.get_player_skill(member.id)
        embed = discord.Embed(
            title="📊 Player Skill Level",
            description=f"{member.display_name}'s current skill level: **{current_skill}/10**",
            color=0x0099ff
        )
        await ctx.send(embed=embed)
        return
    
    # Set skill level
    if not 1 <= skill_level <= 10:
        await ctx.send("❌ Skill level must be between 1 and 10!")
        return
    
    # Check if trying to set someone else's skill level
    if member != ctx.author and not ctx.author.guild_permissions.manage_roles:
        await ctx.send("❌ You can only set your own skill level, or you need 'Manage Roles' permission to set others!")
        return
    
    success = player_db.set_player_skill(member.id, member.display_name, skill_level)
    
    if success:
        embed = discord.Embed(
            title="✅ Skill Level Updated",
            description=f"Set {member.display_name}'s skill level to **{skill_level}/10**",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("❌ Failed to update skill level!")

@teams_group.command(name='players', help='List all players and their skill levels')
async def players_command(ctx):
    """List all players in the database with their skill levels"""
    players = player_db.get_all_players()
    
    if not players:
        await ctx.send("📝 No players found in the database!")
        return
    
    embed = discord.Embed(
        title="📋 Player Skill Levels",
        description=f"Total players: {len(players)}",
        color=0x0099ff
    )
    
    # Group players by skill level for better organization
    skill_groups = {}
    for user_id, username, skill in players:
        if skill not in skill_groups:
            skill_groups[skill] = []
        skill_groups[skill].append(username)
    
    # Add fields for each skill level (in reverse order, highest first)
    for skill in sorted(skill_groups.keys(), reverse=True):
        players_list = skill_groups[skill]
        if len(players_list) <= 10:
            value = "\n".join(f"• {name}" for name in players_list)
        else:
            value = "\n".join(f"• {name}" for name in players_list[:10])
            value += f"\n... and {len(players_list) - 10} more"
        
        embed.add_field(
            name=f"Skill {skill} ({len(players_list)} players)",
            value=value,
            inline=True
        )
    
    await ctx.send(embed=embed)

@teams_group.command(name='cleanup', help='Clean up all HP2BR team channels')
async def cleanup_teams_subcommand(ctx):
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

@teams_group.command(name='help', help='Show detailed help for team commands')
async def team_help_subcommand(ctx):
    """Show detailed help information"""
    embed = discord.Embed(
        title="🤖 Enhanced Team Generator Bot Help",
        description="Generate random or balanced teams with skill-based balancing!",
        color=0x0099ff
    )
    
    embed.add_field(
        name="📋 Team Commands",
        value=(
            "`!teams <format>` - Generate random teams\n"
            "`!teams <format> balanced` - Generate balanced teams\n"
            "`!teams debug` - Create debug channel\n"
            "`!teams cleanup` - Clean up team channels"
        ),
        inline=False
    )
    
    embed.add_field(
        name="👤 Player Commands",
        value=(
            "`!teams skill` - View your skill level\n"
            "`!teams skill <level>` - Set your skill level (1-10)\n"
            "`!teams skill @user <level>` - Set user's skill level (requires Manage Roles)\n"
            "`!teams players` - List all players and skill levels"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📝 Team Format Examples",
        value=(
            "`!teams 4:4` - Two random teams of 4\n"
            "`!teams 3:3:2 balanced` - Balanced teams (3,3,2)\n"
            "`!teams 5:5:5:5` - Four random teams of 5\n"
            "`!teams 2:2:2:2 balanced` - Four balanced teams of 2"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚖️ Balanced Teams",
        value=(
            "• Uses player skill levels (1-10) to create fair teams\n"
            "• Automatically creates players with skill level 1\n"
            "• Shows team averages and balance score\n"
            "• Lower balance score = more balanced teams"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎯 How it works",
        value=(
            "1. Set your skill level with `!teams skill <1-10>`\n"
            "2. Join a voice channel\n"
            "3. Run `!teams <format>` (random) or `!teams <format> balanced`\n"
            "4. Bot creates team channels and moves members\n"
            "5. Use `!teams cleanup` to remove channels when done"
        ),
        inline=False
    )
    
    embed.set_footer(text="Player data is stored in SQLite database")
    await ctx.send(embed=embed)

@teams_group.error
async def teams_error(ctx, error):
    """Error handler for teams command group"""
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Please specify team format! Example: `!teams 4:4:2` or `!teams 3:3:3 balanced`")
    else:
        await ctx.send(f"❌ An error occurred: {str(error)}")

# Run the bot
if __name__ == "__main__":
    print("Starting Enhanced Discord Team Generator Bot...")
    print("Features:")
    print("- SQLite database for player skill storage")
    print("- Random team generation")
    print("- Balanced team generation based on skill levels")
    print("- Player skill management commands")
    print()
    print("Make sure to:")
    print("1. Set your DISCORD_TOKEN environment variable")
    print("2. Invite the bot with proper permissions:")
    print("   - Manage Channels")
    print("   - Move Members") 
    print("   - Send Messages")
    print("   - Connect to Voice Channels")
    
    # Replace with your bot token
    bot.run(os.environ["DISCORD_TOKEN"])
