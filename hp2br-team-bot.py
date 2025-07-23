import discord
from discord.ext import commands
import random
import asyncio
from typing import List, Optional, Tuple
import re, os, time
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
        super().__init__(timeout=900)  # 15 minutes timeout (Discord's maximum)
    
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
        deleted_count, moved_count, failed_moves = await cleanup_old_channels(guild)
        
        if deleted_count > 0:
            response_msg = f"✅ Cleaned up {deleted_count} team channels!"
            if moved_count > 0:
                response_msg += f"\n👥 Moved {moved_count} players to Waiting Room"
            if failed_moves:
                response_msg += f"\n⚠️ Some moves failed: {len(failed_moves)} players"
            
            await interaction.response.send_message(
                response_msg, 
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

class TeamGameView(discord.ui.View):
    def __init__(self, created_channels: List[discord.VoiceChannel], guild: discord.Guild):
        super().__init__(timeout=3600)  # 1 hour timeout for games
        self.created_channels = created_channels
        self.guild = guild
        
        # Add individual team end buttons (max 5 to fit in Discord's limits)
        for i, channel in enumerate(self.created_channels[:5], 1):
            button = discord.ui.Button(
                label=f'🏁 End Team {i}',
                style=discord.ButtonStyle.secondary,
                custom_id=f'end_team_{i}'
            )
            button.callback = self.create_end_team_callback(i-1, channel)
            self.add_item(button)
    
    def create_end_team_callback(self, team_index: int, channel: discord.VoiceChannel):
        """Create a callback function for ending a specific team"""
        async def end_team_callback(interaction: discord.Interaction):
            try:
                # Find the "Waiting Room" channel
                waiting_room = discord.utils.get(self.guild.voice_channels, name="Waiting Room")
                
                if not waiting_room:
                    await interaction.response.send_message(
                        "❌ Could not find 'Waiting Room' voice channel! Please create one or manually move players.",
                        ephemeral=True
                    )
                    return
                
                # Check if channel still exists
                if not channel or channel not in self.created_channels:
                    await interaction.response.send_message(
                        f"❌ Team {team_index + 1} channel no longer exists!",
                        ephemeral=True
                    )
                    return
                
                # Count members moved
                moved_count = 0
                failed_moves = []
                
                # Move all members from this team channel back to waiting room
                if hasattr(channel, 'members'):
                    for member in channel.members.copy():
                        try:
                            await member.move_to(waiting_room)
                            moved_count += 1
                        except discord.HTTPException as e:
                            failed_moves.append(f"{member.display_name}: {str(e)}")
                            print(f"Failed to move {member.display_name}: {e}")
                
                # Delete the team channel
                try:
                    channel_name = channel.name
                    await channel.delete(reason=f"End Team {team_index + 1} - cleaning up team channel")
                    
                    # Remove from our tracking
                    if channel in self.created_channels:
                        self.created_channels.remove(channel)
                    
                    # Remove from global tracking
                    if self.guild.id in team_gen.created_channels:
                        try:
                            team_gen.created_channels[self.guild.id].remove(channel.id)
                        except ValueError:
                            pass  # Channel ID not in list
                    
                except discord.HTTPException as e:
                    await interaction.response.send_message(
                        f"❌ Failed to delete Team {team_index + 1} channel: {str(e)}",
                        ephemeral=True
                    )
                    return
                
                # Create success message
                success_msg = f"✅ **Team {team_index + 1} Ended!**\n"
                success_msg += f"• Moved {moved_count} players to {waiting_room.mention}\n"
                success_msg += f"• Deleted channel: {channel_name}"
                
                if failed_moves:
                    success_msg += f"\n⚠️ Failed to move: {', '.join(failed_moves[:3])}"
                
                # Disable the button for this team
                for item in self.children:
                    if hasattr(item, 'custom_id') and item.custom_id == f'end_team_{team_index + 1}':
                        item.disabled = True
                        break
                
                # Check if we need to clean up empty categories
                if len(self.created_channels) == 0:
                    categories_to_check = ["HP2BR Auto Teams", "HP2BRTeams"]
                    for category_name in categories_to_check:
                        category = discord.utils.get(self.guild.categories, name=category_name)
                        if category and len(category.channels) == 0:
                            try:
                                await category.delete(reason="End game cleanup - empty category")
                                print(f"Deleted empty category: {category_name}")
                            except discord.HTTPException:
                                pass
                
                await interaction.response.send_message(success_msg, ephemeral=True)
                
                # Update the view to reflect the disabled button
                try:
                    await interaction.edit_original_response(view=self)
                except discord.NotFound:
                    pass  # Original message might be gone
                
            except Exception as e:
                await interaction.response.send_message(
                    f"❌ An error occurred while ending Team {team_index + 1}: {str(e)}",
                    ephemeral=True
                )
        
        return end_team_callback
    
    @discord.ui.button(label='🏁 End Game All', style=discord.ButtonStyle.red)
    async def end_game_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Find the "Waiting Room" channel
            waiting_room = discord.utils.get(self.guild.voice_channels, name="Waiting Room")
            
            if not waiting_room:
                await interaction.response.send_message(
                    "❌ Could not find 'Waiting Room' voice channel! Please create one or manually move players.",
                    ephemeral=True
                )
                return
            
            # Count members moved
            moved_count = 0
            failed_moves = []
            
            # Move all members from team channels back to waiting room
            for channel in self.created_channels:
                if channel and hasattr(channel, 'members'):  # Check if channel still exists
                    for member in channel.members.copy():  # Copy list to avoid modification during iteration
                        try:
                            await member.move_to(waiting_room)
                            moved_count += 1
                        except discord.HTTPException as e:
                            failed_moves.append(f"{member.display_name}: {str(e)}")
                            print(f"Failed to move {member.display_name}: {e}")
            
            # Delete the team channels
            deleted_count = 0
            for channel in self.created_channels:
                try:
                    if channel:  # Check if channel still exists
                        await channel.delete(reason="End game - cleaning up team channels")
                        deleted_count += 1
                except discord.HTTPException as e:
                    print(f"Failed to delete channel {channel.name if channel else 'Unknown'}: {e}")
            
            # Clean up empty categories
            categories_to_check = ["HP2BR Auto Teams", "HP2BRTeams"]
            for category_name in categories_to_check:
                category = discord.utils.get(self.guild.categories, name=category_name)
                if category and len(category.channels) == 0:
                    try:
                        await category.delete(reason="End game cleanup - empty category")
                        print(f"Deleted empty category: {category_name}")
                    except discord.HTTPException:
                        pass
            
            # Clear stored channel IDs
            if self.guild.id in team_gen.created_channels:
                team_gen.created_channels[self.guild.id] = []
            
            # Create success embed
            embed = discord.Embed(
                title="🏁 Game Ended Successfully!",
                description=f"Moved {moved_count} players back to {waiting_room.mention}\nDeleted {deleted_count} team channels",
                color=0xff6b6b
            )
            
            if failed_moves:
                embed.add_field(
                    name="⚠️ Failed to move some players",
                    value="\n".join(failed_moves[:5]),  # Show first 5 failures
                    inline=False
                )
            
            embed.set_footer(text="All team channels have been cleaned up!")
            
            # Disable all buttons after use
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred while ending the game: {str(e)}",
                ephemeral=True
            )

class TeamCreationView(discord.ui.View):
    def __init__(self, teams: List[List[discord.Member]], team_stats: List[Tuple[float, List[int]]], 
                 guild: discord.Guild, balanced: bool):
        super().__init__(timeout=900)  # 15 minutes timeout (Discord's maximum)
        self.teams = teams
        self.team_stats = team_stats
        self.guild = guild
        self.balanced = balanced
        self.created_channels = []  # Store created channels for cleanup
    
    @discord.ui.button(label='🎯 Create Team Channels & Move Players', style=discord.ButtonStyle.green)
    async def create_teams_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Clean up old team channels first
            deleted_count, moved_count, failed_moves = await cleanup_old_channels(self.guild)
            
            # Find or create a category for team channels
            category = None
            try:
                category = discord.utils.get(self.guild.categories, name="HP2BRTeams")
                if not category:
                    category = await self.guild.create_category("HP2BRTeams")
            except discord.HTTPException as e:
                print(f"Warning: Failed to create category, channels will be created without category: {e}")
                category = None
            
            # Create team channels and move members
            created_channels = await team_gen.create_team_channels(self.guild, category, self.teams)
            
            # Store created channels for cleanup
            self.created_channels = created_channels
            if self.guild.id not in team_gen.created_channels:
                team_gen.created_channels[self.guild.id] = []
            team_gen.created_channels[self.guild.id].extend([ch.id for ch in created_channels])
            
            # Create success embed
            embed = discord.Embed(
                title="✅ Teams Created Successfully!",
                description=f"Created {len(self.teams)} team channels and moved all players!",
                color=0x00ff00
            )
            
            for i, (team, channel) in enumerate(zip(self.teams, created_channels), 1):
                team_names = [f"• {member.display_name}" for member in team]
                embed.add_field(
                    name=f"Team {i} - {channel.name}",
                    value="\n".join(team_names),
                    inline=True
                )
            
            embed.set_footer(text="All members have been moved to their team channels! Use individual team buttons or 'End Game All' when finished.")
            
            # Add note if there are more than 5 teams (button limit)
            if len(self.teams) > 5:
                embed.add_field(
                    name="⚠️ Note",
                    value=f"Only showing End buttons for first 5 teams. Teams 6-{len(self.teams)} can be ended with 'End Game All' or manual cleanup.",
                    inline=False
                )
            
            # Disable the create button immediately
            button.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            
            # Wait 5 seconds before showing End Game controls
            await asyncio.sleep(5)
            
            # Create new view with End Game button after delay
            new_view = TeamGameView(self.created_channels, self.guild)
            
            # Update the message with End Game controls
            embed.add_field(
                name="🎮 Game Controls Available",
                value="You can now end individual teams or the entire game using the buttons below.",
                inline=False
            )
            
            try:
                await interaction.edit_original_response(embed=embed, view=new_view)
            except discord.NotFound:
                # If original message was deleted, send a new one
                await interaction.followup.send(embed=embed, view=new_view)
            
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to create channels or move members!", 
                ephemeral=True
            )
        except discord.HTTPException as e:
            if "Parent_id: Category does not exist" in str(e):
                await interaction.response.send_message(
                    "❌ Category creation failed. Retrying without category...", 
                    ephemeral=True
                )
                # Retry without category
                try:
                    created_channels = await team_gen.create_team_channels(self.guild, None, self.teams)
                    if created_channels:
                        self.created_channels = created_channels
                        embed = discord.Embed(
                            title="✅ Teams Created (No Category)",
                            description=f"Created {len(self.teams)} team channels without category!",
                            color=0x00ff00
                        )
                        embed.set_footer(text="Teams created successfully! Use individual team buttons or 'End Game All' when finished.")
                        
                        # Add note if there are more than 5 teams (button limit)
                        if len(self.teams) > 5:
                            embed.add_field(
                                name="⚠️ Note",
                                value=f"Only showing End buttons for first 5 teams. Teams 6-{len(self.teams)} can be ended with 'End Game All' or manual cleanup.",
                                inline=False
                            )
                        
                        # Disable the create button immediately
                        button.disabled = True
                        await interaction.edit_original_response(embed=embed, view=self)
                        
                        # Wait 5 seconds before showing End Game controls
                        await asyncio.sleep(5)
                        
                        # Create new view with End Game button after delay
                        new_view = TeamGameView(self.created_channels, self.guild)
                        
                        # Update the message with End Game controls
                        embed.add_field(
                            name="🎮 Game Controls Available",
                            value="You can now end individual teams or the entire game using the buttons below.",
                            inline=False
                        )
                        
                        try:
                            await interaction.edit_original_response(embed=embed, view=new_view)
                        except discord.NotFound:
                            # If original message was deleted, send a new one
                            await interaction.followup.send(embed=embed, view=new_view)
                except Exception as retry_e:
                    await interaction.followup.send(f"❌ Retry failed: {str(retry_e)}", ephemeral=True)
            else:
                await interaction.response.send_message(
                    f"❌ Discord API error: {str(e)}", 
                    ephemeral=True
                )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ An error occurred while creating teams: {str(e)}", 
                ephemeral=True
            )

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
    
    async def create_team_channels(self, guild: discord.Guild, category: Optional[discord.CategoryChannel], 
                                 teams: List[List[discord.Member]]) -> List[discord.VoiceChannel]:
        """Create voice channels for each team"""
        created_channels = []
        
        # Ensure category exists or create it
        if category is None:
            try:
                category = discord.utils.get(guild.categories, name="HP2BRTeams")
                if not category:
                    category = await guild.create_category("HP2BRTeams")
            except discord.HTTPException as e:
                print(f"Failed to create category: {e}")
                category = None
        
        for i, team in enumerate(teams, 1):
            channel_name = f"HP2BR-Team-{i}"
            
            # Create the voice channel with or without category
            try:
                if category:
                    channel = await guild.create_voice_channel(
                        name=channel_name,
                        category=category,
                        reason="Team generator bot - creating team channels"
                    )
                else:
                    # Create without category if category creation failed
                    channel = await guild.create_voice_channel(
                        name=channel_name,
                        reason="Team generator bot - creating team channels"
                    )
                
                created_channels.append(channel)
                
                # Move members to the new channel with 1-second delay between moves
                for member in team:
                    try:
                        if member.voice:  # Check if member is still in a voice channel
                            await member.move_to(channel)
                            await asyncio.sleep(1)  # 1-second delay after moving each player
                    except discord.HTTPException:
                        print(f"Failed to move {member.display_name} to {channel_name}")
                        
            except discord.HTTPException as e:
                print(f"Failed to create channel {channel_name}: {e}")
                # Continue with other channels even if one fails
                continue
        
        return created_channels

# async def play_sound_in_waiting_room(guild: discord.Guild):
#     """Play ggs.mp3 sound file in the Waiting Room channel"""
#     try:
#         # Find the Waiting Room voice channel
#         waiting_room = discord.utils.get(guild.voice_channels, name="Waiting Room")
        
#         if not waiting_room:
#             print("Warning: Could not find 'Waiting Room' voice channel for playing sound")
#             return
        
#         # Check if the ggs.mp3 file exists
#         sound_file = "ggs.mp3"
#         if not os.path.exists(sound_file):
#             print(f"Warning: Sound file '{sound_file}' not found. Please add ggs.mp3 to the bot directory.")
#             return
        
#         # Check if bot is already connected to a voice channel in this guild
#         if guild.voice_client is not None:
#             # If already connected, move to Waiting Room
#             await guild.voice_client.move_to(waiting_room)
#         else:
#             # Connect to the Waiting Room
#             voice_client = await waiting_room.connect()
        
#         # Play the sound file
#         if guild.voice_client and not guild.voice_client.is_playing():
#             audio_source = discord.FFmpegPCMAudio(sound_file)
#             guild.voice_client.play(audio_source)
            
#             # Wait for the audio to finish playing
#             while guild.voice_client.is_playing():
#                 await asyncio.sleep(0.5)
            
#             # Disconnect after playing
#             await guild.voice_client.disconnect()
            
#         print(f"Successfully played {sound_file} in Waiting Room")
        
#     except discord.errors.ClientException as e:
#         print(f"Discord client error while playing sound: {e}")
#     except Exception as e:
#         print(f"Error playing sound in Waiting Room: {e}")

# Initialize global instances
team_gen = TeamGenerator()
player_db = PlayerDatabase()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is ready and connected to {len(bot.guilds)} guilds')
    print(f'Player database initialized at: {player_db.db_path}')
    
    # Check if ggs.mp3 exists
    # if os.path.exists('ggs.mp3'):
    #     print('✅ ggs.mp3 sound file found')
    # else:
    #     print('⚠️ ggs.mp3 sound file not found - sound functionality will be disabled')

async def create_debug_channel(ctx):
    """Create a debug voice channel, move the caller to it, and play ggs.mp3 in Waiting Room"""
    guild = ctx.guild
    author = ctx.author
    #await play_sound_in_waiting_room(guild)
    time.sleep(5)
    try:
        # Check if debug channel already exists first
        existing_debug = discord.utils.get(guild.voice_channels, name="HP2BR-Debug")
        if existing_debug:
            # Move user to existing debug channel
            if author.voice:  # Check if user is still in a voice channel
                await author.move_to(existing_debug)
            await ctx.send(f"✅ Moved you to existing debug channel: {existing_debug.mention}")
            # Still play sound even if debug channel already exists
            #await play_sound_in_waiting_room(guild)
            return
        
        # Find or create a category for team channels
        category = None
        try:
            category = discord.utils.get(guild.categories, name="HP2BR Auto Teams")
            if not category:
                category = await guild.create_category("HP2BR Auto Teams")
        except discord.HTTPException as e:
            print(f"Warning: Failed to create category, debug channel will be created without category: {e}")
            category = None
        
        # Create the debug voice channel
        if category:
            debug_channel = await guild.create_voice_channel(
                name="HP2BR-Debug",
                category=category,
                reason="Debug channel created by team bot"
            )
        else:
            debug_channel = await guild.create_voice_channel(
                name="HP2BR-Debug",
                reason="Debug channel created by team bot"
            )
        
        # Move the caller to the debug channel
        await author.move_to(debug_channel)
        
        # Store the channel for cleanup
        if guild.id not in team_gen.created_channels:
            team_gen.created_channels[guild.id] = []
        team_gen.created_channels[guild.id].append(debug_channel.id)
        
        # Play sound in Waiting Room
        #await play_sound_in_waiting_room(guild)
        
        # Send confirmation with cleanup button
        embed = discord.Embed(
            title="🐛 Debug Channel Created!",
            description=f"Created debug channel and moved {author.display_name} to it.\n🎵 Playing ggs.mp3 in Waiting Room!",
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
        
        # Calculate team statistics
        team_stats = team_gen.calculate_team_stats(teams)
        
        # Create response embed showing the proposed teams
        embed = discord.Embed(
            title=f"🎯 {team_type} Preview",
            description=f"Generated {len(teams)} teams from {len(members)} members\n**Click the button below to create channels and move players!**",
            color=0x0099ff if not balanced else 0x00aa99
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
        
        embed.set_footer(text="Teams are ready! Click the button to create channels and move players.")
        
        # Create the view with the team creation button
        view = TeamCreationView(teams, team_stats, guild, balanced)
        await ctx.send(embed=embed, view=view)
        
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
    deleted_count, moved_count, failed_moves = await cleanup_old_channels(guild)
    
    if deleted_count > 0:
        embed = discord.Embed(
            title="✅ Cleanup Complete!",
            description=f"Cleaned up {deleted_count} team channels",
            color=0x00ff00
        )
        
        if moved_count > 0:
            embed.add_field(
                name="👥 Players Moved",
                value=f"Moved {moved_count} players to Waiting Room",
                inline=False
            )
        
        if failed_moves:
            embed.add_field(
                name="⚠️ Failed Moves",
                value="\n".join(failed_moves[:5]),  # Show first 5 failures
                inline=False
            )
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("ℹ️ No team channels found to clean up.")

async def cleanup_old_channels(guild: discord.Guild):
    """Clean up old HP2BR team channels, debug channels, and empty categories"""
    deleted_count = 0
    moved_count = 0
    failed_moves = []
    
    # Find the "Waiting Room" channel
    waiting_room = discord.utils.get(guild.voice_channels, name="Waiting Room")
    
    if not waiting_room:
        print("Warning: No 'Waiting Room' channel found. Players will not be moved during cleanup.")
    
    # Find all HP2BR team channels and debug channels
    for channel in guild.voice_channels:
        if channel.name.startswith("HP2BR-Team-") or channel.name == "HP2BR-Debug":
            try:
                # Move all members to Waiting Room before deleting channel
                if waiting_room and hasattr(channel, 'members'):
                    for member in channel.members.copy():  # Copy list to avoid modification during iteration
                        try:
                            await member.move_to(waiting_room)
                            moved_count += 1
                        except discord.HTTPException as e:
                            failed_moves.append(f"{member.display_name}: {str(e)}")
                            print(f"Failed to move {member.display_name} during cleanup: {e}")
                
                # Delete the channel
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
    
    return deleted_count, moved_count, failed_moves

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
            "`!teams <format>` - Generate random teams (shows preview with button)\n"
            "`!teams <format> balanced` - Generate balanced teams (shows preview with button)\n"
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
            "4. **NEW:** Review the team preview and click 'Create Team Channels' button\n"
            "5. Bot creates team channels and moves members\n"
            "6. **NEW:** During game:\n"
            "   • Click 'End Team X' to end individual teams\n"
            "   • Click 'End Game All' to end all teams at once\n"
            "7. Players moved back to 'Waiting Room' and channels deleted\n"
            "8. Alternative: Use `!teams cleanup` to manually remove channels"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📝 Requirements",
        value=(
            "• Create a voice channel named 'Waiting Room' for the End Game functionality\n"
            "• Bot needs 'Manage Channels' and 'Move Members' permissions\n"
            "• Users must be in a voice channel to generate teams"
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
    print("- Button-based team creation (NEW)")
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