import discord
import asyncio
import logging
from typing import Dict, List, Any
from utils.constants import Config

logger = logging.getLogger(__name__)

class TeamProposalView(discord.ui.View):
    """Interactive buttons for team proposals - Create Team or End Game"""
    
    def __init__(self, teams: List[List[Dict]], team_channels: List[discord.VoiceChannel], 
                 match_id: str, voice_manager):
        super().__init__(timeout=None)  # No timeout - buttons stay active
        self.teams = teams
        self.team_channels = team_channels
        self.match_id = match_id
        self.voice_manager = voice_manager
        
        # Get all player IDs for validation
        self.all_players: set = set()
        for team in teams:
            for player in team:
                if 'discord_member' in player:
                    self.all_players.add(player['discord_member'].id)
        
        self.result_sent = False
    
    @discord.ui.button(label='🎮 Create Team', style=discord.ButtonStyle.success)
    async def create_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Create the teams and move players"""
        user_id = interaction.user.id
        
        # Check if user is in the match
        if user_id not in self.all_players:
            await interaction.response.send_message(
                "❌ You're not part of this match!", 
                ephemeral=True
            )
            return
        
        if self.result_sent:
            await interaction.response.send_message(
                "⚠️ Teams have already been processed!", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        await self._handle_create_team(interaction)
    
    @discord.ui.button(label='🛑 End Game', style=discord.ButtonStyle.danger)
    async def end_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """End the game and cleanup (equivalent to /cleanup)"""
        user_id = interaction.user.id
        
        # Check if user is in the match
        if user_id not in self.all_players:
            await interaction.response.send_message(
                "❌ You're not part of this match!", 
                ephemeral=True
            )
            return
        
        if self.result_sent:
            await interaction.response.send_message(
                "⚠️ Game has already been processed!", 
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        await self._handle_end_game(interaction)
    
    async def _handle_create_team(self, interaction: discord.Interaction):
        """Handle team creation and player movement"""
        self.result_sent = True
        
        try:
            # Move players to team channels
            discord_teams = []
            for team in self.teams:
                discord_team = []
                for player in team:
                    if 'discord_member' in player:
                        discord_team.append(player['discord_member'])
                discord_teams.append(discord_team)
            
            # Improved player movement with better error handling
            success, moved_count, failed_players = await self._move_players_with_detailed_feedback(
                discord_teams, self.team_channels
            )
            
            if success and moved_count > 0:
                # Store active match info
                self.voice_manager.set_active_match(interaction.guild.id, {
                    'match_id': self.match_id,
                    'teams': self.teams,
                    'team_channels': self.team_channels,
                    'status': 'active'
                })
                
                embed = discord.Embed(
                    title="🎮 Teams Created!",
                    description=f"Successfully moved {moved_count} players to their team channels. Good luck!",
                    color=Config.SUCCESS_COLOR
                )
                
                if failed_players:
                    embed.add_field(
                        name="⚠️ Manual Movement Needed",
                        value=f"Could not move: {', '.join(failed_players)}\nPlease move these players manually to their team channels.",
                        inline=False
                    )
                
                embed.add_field(
                    name="📝 After Your Match",
                    value="Use `/record_result <winning_team>` to record the outcome and update ratings.",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
            else:
                # Store active match even if movement failed
                self.voice_manager.set_active_match(interaction.guild.id, {
                    'match_id': self.match_id,
                    'teams': self.teams,
                    'team_channels': self.team_channels,
                    'status': 'active'
                })
                
                embed = discord.Embed(
                    title="⚠️ Teams Created - Manual Movement Required",
                    description="Teams were created but players could not be moved automatically.",
                    color=Config.WARNING_COLOR
                )
                embed.add_field(
                    name="🔧 What to do:",
                    value="Please manually move players to their assigned team channels shown above.",
                    inline=False
                )
                embed.add_field(
                    name="📝 After Your Match",
                    value="Use `/record_result <winning_team>` to record the outcome and update ratings.",
                    inline=False
                )
                
                if failed_players:
                    embed.add_field(
                        name="❌ Failed to move:",
                        value=', '.join(failed_players),
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error creating teams: {e}")
            embed = discord.Embed(
                title="❌ Error Creating Teams",
                description=f"An error occurred while creating teams: {str(e)[:200]}",
                color=Config.ERROR_COLOR
            )
            embed.add_field(
                name="🔧 What to do:",
                value="Please manually move players to team channels and use `/record_result` after the match.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(view=self)
    
    async def _handle_end_game(self, interaction: discord.Interaction):
        """Handle ending the game (equivalent to /cleanup)"""
        self.result_sent = True
        
        try:
            # Import api_client here to avoid circular imports
            from services.api_client import api_client
            
            # Cancel the match in database
            await api_client.cancel_match(self.match_id)
            
            # Clean up team channels and return players to waiting room
            await self.voice_manager.cleanup_team_channels(
                interaction.guild, 
                return_to_waiting=True
            )
            
            # Clear active match
            self.voice_manager.clear_active_match(interaction.guild.id)
            
            embed = discord.Embed(
                title="🛑 Game Ended",
                description="The game has been ended and all players have been returned to the waiting room.",
                color=Config.WARNING_COLOR
            )
            embed.add_field(
                name="🔄 What's Next",
                value="Use `/create_teams` to start a new match when ready.",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error ending game: {e}")
            embed = discord.Embed(
                title="❌ Error Ending Game",
                description=f"An error occurred while ending the game: {str(e)[:200]}",
                color=Config.ERROR_COLOR
            )
            embed.add_field(
                name="🔧 Manual Cleanup",
                value="You may need to use `/cleanup` command to manually clean up channels.",
                inline=False
            )
            await interaction.followup.send(embed=embed)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(view=self)
    
    async def _move_players_with_detailed_feedback(self, teams, team_channels):
        """Enhanced player movement with detailed feedback"""
        if len(teams) != len(team_channels):
            logger.error("Mismatch between number of teams and channels")
            return False, 0, []
        
        moved_count = 0
        failed_players = []
        
        try:
            for team_idx, (team, channel) in enumerate(zip(teams, team_channels)):
                logger.info(f"Processing Team {team_idx + 1} with {len(team)} players")
                
                # Set permissions for team members
                for member in team:
                    try:
                        await channel.set_permissions(
                            member,
                            connect=True,
                            speak=True,
                            reason=f"Team {team_idx + 1} member"
                        )
                        logger.debug(f"Set permissions for {member.display_name} on {channel.name}")
                    except Exception as e:
                        logger.warning(f"Could not set permissions for {member.display_name}: {e}")
                
                # Move members to team channel
                for member in team:
                    try:
                        if member.voice and member.voice.channel:
                            logger.info(f"Attempting to move {member.display_name} from {member.voice.channel.name} to {channel.name}")
                            await member.move_to(channel, reason=f"Team {team_idx + 1} assignment")
                            moved_count += 1
                            logger.info(f"✅ Successfully moved {member.display_name} to Team {team_idx + 1}")
                        else:
                            logger.warning(f"❌ {member.display_name} is not in a voice channel")
                            failed_players.append(f"{member.display_name} (not in voice)")
                    except discord.Forbidden as e:
                        logger.error(f"❌ Permission denied moving {member.display_name}: {e}")
                        failed_players.append(f"{member.display_name} (permission denied)")
                    except discord.HTTPException as e:
                        logger.error(f"❌ HTTP error moving {member.display_name}: {e}")
                        failed_players.append(f"{member.display_name} (connection error)")
                    except Exception as e:
                        logger.error(f"❌ Unexpected error moving {member.display_name}: {e}")
                        failed_players.append(f"{member.display_name} (error: {str(e)[:50]})")
                    
                    # Small delay to avoid rate limits
                    await asyncio.sleep(0.3)
        
        except Exception as e:
            logger.error(f"Critical error during player movement: {e}")
            return False, moved_count, failed_players
        
        logger.info(f"Movement complete: {moved_count} moved, {len(failed_players)} failed")
        return moved_count > 0, moved_count, failed_players

class MatchResultView(discord.ui.View):
    """Interactive dialogue for recording match results with dropdowns for each team"""
    
    def __init__(self, teams: List[List[Dict]], match_id: str):
        super().__init__(timeout=300)  # 5 minute timeout for result recording
        self.teams = teams
        self.match_id = match_id
        self.team_results = {}  # Store each team's result
        self.result_sent = False
        
        # Create dropdown for each team
        for i, team in enumerate(teams):
            team_names = [player['username'] for player in team]
            team_display = f"Team {i+1}: {', '.join(team_names[:3])}"  # Show first 3 names
            if len(team_names) > 3:
                team_display += f" (+{len(team_names)-3} more)"
            
            dropdown = TeamResultSelect(
                team_number=i+1,
                team_display=team_display,
                parent_view=self
            )
            self.add_item(dropdown)
        
        # Add submit button
        self.add_item(SubmitResultsButton())
    
    def update_team_result(self, team_number: int, result: str):
        """Update a team's result"""
        self.team_results[team_number] = result
        
        # Check if all teams have results
        if len(self.team_results) == len(self.teams):
            # Enable submit button
            for item in self.children:
                if isinstance(item, SubmitResultsButton):
                    item.disabled = False
                    break
    
    def validate_results(self) -> tuple[bool, str]:
        """Validate that the results make sense"""
        if len(self.team_results) != len(self.teams):
            return False, "Please select a result for all teams."
        
        wins = sum(1 for result in self.team_results.values() if result == "win")
        losses = sum(1 for result in self.team_results.values() if result == "loss")
        draws = sum(1 for result in self.team_results.values() if result == "draw")
        
        # Validation rules
        if draws > 0:
            # If any team has draw, all teams must have draw
            if draws != len(self.teams):
                return False, "If it's a draw, all teams must be marked as 'Draw'."
        else:
            # For win/loss, exactly one team should win, others should lose
            if wins != 1:
                return False, "Exactly one team must be marked as 'Win' (others as 'Loss')."
            if losses != len(self.teams) - 1:
                return False, "All non-winning teams must be marked as 'Loss'."
        
        return True, ""
    
    async def submit_results(self, interaction: discord.Interaction):
        """Submit the match results"""
        if self.result_sent:
            await interaction.response.send_message("Results have already been submitted!", ephemeral=True)
            return
        
        # Validate results
        is_valid, error_msg = self.validate_results()
        if not is_valid:
            await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
            return
        
        self.result_sent = True
        await interaction.response.defer()
        
        try:
            # Import here to avoid circular imports
            from services.api_client import api_client
            
            # Determine result type and winning team
            if "draw" in self.team_results.values():
                result_type = "draw"
                winning_team = None
            else:
                result_type = "win_loss"
                winning_team = None
                for team_num, result in self.team_results.items():
                    if result == "win":
                        winning_team = team_num
                        break
            
            # Record result in database
            result_data = await api_client.record_match_result(
                match_id=self.match_id,
                result_type=result_type,
                winning_team=winning_team
            )
            
            if not result_data:
                embed = discord.Embed(
                    title="❌ Database Error",
                    description="Failed to record match result. Please try again.",
                    color=Config.ERROR_COLOR
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create result embed
            if result_type == "win_loss" and winning_team:
                title = f"🏆 Team {winning_team} Wins!"
                description = f"Congratulations to Team {winning_team}! Ratings have been updated."
                color = Config.SUCCESS_COLOR
            else:
                title = "🤝 Match Draw"
                description = "The match ended in a draw. Ratings have been updated."
                color = Config.WARNING_COLOR
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=color
            )
            
            # Add team information with results
            for i, team in enumerate(self.teams):
                team_names = [player['username'] for player in team]
                team_result = self.team_results.get(i+1, "unknown")
                
                if team_result == "win":
                    team_emoji = " 🏆"
                elif team_result == "loss":
                    team_emoji = " 💔"
                else:  # draw
                    team_emoji = " 🤝"
                
                embed.add_field(
                    name=f"Team {i+1}{team_emoji}",
                    value="\n".join([f"• {name}" for name in team_names]),
                    inline=True
                )
            
            embed.set_footer(text="Match completed! Players will be returned to the waiting room.")
            
            await interaction.followup.send(embed=embed)
            
            # Import voice manager and cleanup
            # We'll need to get this from the parent command
            logger.info(f"Match {self.match_id} completed with result: {result_type}, winner: {winning_team}")
            
        except Exception as e:
            logger.error(f"Error submitting match results: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred while recording results: {str(e)[:200]}",
                color=Config.ERROR_COLOR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Disable all items
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(view=self)

class TeamResultSelect(discord.ui.Select):
    """Dropdown for selecting a team's result"""
    
    def __init__(self, team_number: int, team_display: str, parent_view):
        self.team_number = team_number
        self.parent_view = parent_view
        
        options = [
            discord.SelectOption(
                label="Win",
                value="win",
                description=f"Team {team_number} won the match",
                emoji="🏆"
            ),
            discord.SelectOption(
                label="Loss",
                value="loss", 
                description=f"Team {team_number} lost the match",
                emoji="💔"
            ),
            discord.SelectOption(
                label="Draw",
                value="draw",
                description=f"Team {team_number} drew the match",
                emoji="🤝"
            )
        ]
        
        super().__init__(
            placeholder=f"Select result for {team_display}",
            options=options,
            min_values=1,
            max_values=1
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle team result selection"""
        selected_result = self.values[0]
        self.parent_view.update_team_result(self.team_number, selected_result)
        
        # Update placeholder to show selection
        result_emoji = {"win": "🏆", "loss": "💔", "draw": "🤝"}[selected_result]
        self.placeholder = f"Team {self.team_number}: {selected_result.title()} {result_emoji}"
        
        await interaction.response.edit_message(view=self.parent_view)

class SubmitResultsButton(discord.ui.Button):
    """Button to submit the match results"""
    
    def __init__(self):
        super().__init__(
            label="Submit Results",
            style=discord.ButtonStyle.success,
            emoji="📝",
            disabled=True  # Disabled until all teams have results
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle result submission"""
        await self.view.submit_results(interaction)

class PaginatedView(discord.ui.View):
    """Pagination for leaderboards and match history"""
    
    def __init__(self, pages: List[discord.Embed], timeout: float = 300):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.current_page = 0
        
        # Disable buttons if only one page
        if len(pages) <= 1:
            self.previous_page.disabled = True
            self.next_page.disabled = True
        else:
            self.previous_page.disabled = True  # Start with previous disabled
    
    def update_buttons(self):
        """Update button states based on current page"""
        self.previous_page.disabled = (self.current_page == 0)
        self.next_page.disabled = (self.current_page == len(self.pages) - 1)
    
    @discord.ui.button(label='◀️ Previous', style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            
            await interaction.response.edit_message(
                embed=self.pages[self.current_page],
                view=self
            )
    
    @discord.ui.button(label='▶️ Next', style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Go to next page"""
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.update_buttons()
            
            await interaction.response.edit_message(
                embed=self.pages[self.current_page],
                view=self
            )
    
    async def on_timeout(self):
        """Handle timeout"""
        # Disable all buttons
        for item in self.children:
            item.disabled = True

class ConfirmationView(discord.ui.View):
    """Generic confirmation dialog"""
    
    def __init__(self, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.result = None
    
    @discord.ui.button(label='✅ Confirm', style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle confirmation"""
        self.result = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        self.stop()
    
    @discord.ui.button(label='❌ Cancel', style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle cancellation"""
        self.result = False
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        self.stop()
    
    async def on_timeout(self):
        """Handle timeout"""
        self.result = False
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        self.stop()