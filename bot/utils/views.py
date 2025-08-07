import discord
import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime
from utils.constants import Config
from utils.version import get_bot_footer_text

logger = logging.getLogger(__name__)

class TeamProposalView(discord.ui.View):
    """Interactive button for team proposals - Create Team only"""
    
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
        
        # Log user action
        print(f"[USER ACTION] {interaction.user.display_name} ({user_id}) clicked 'Create Team' button in guild {interaction.guild.name} ({interaction.guild.id})")
        
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
        
        # Disable the clicked button immediately
        button.disabled = True
        await interaction.response.edit_message(view=self)
        
        await self._handle_create_team(interaction)
    
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
                    value="Use `/record_result` to record the outcome and update ratings.",
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
                    value="Use `/record_result` to record the outcome and update ratings.",
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
        
        # Disable all buttons after processing
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
    
    def __init__(self, teams: List[List[Dict]], match_id: str, voice_manager):
        super().__init__(timeout=300)  # 5 minute timeout for result recording
        self.teams = teams
        self.match_id = match_id
        self.voice_manager = voice_manager
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
        
        # Add end game button
        self.add_item(EndGameButton())
    
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
            # For teams < 3, allow flexibility: can have all losses (no winner)
            if len(self.teams) < 3:
                # Allow either:
                # 1. Exactly one winner, others lose
                # 2. All teams lose (forfeit/incomplete match)
                if wins == 0 and losses == len(self.teams):
                    # All losses - valid for < 3 teams (forfeit/incomplete)
                    return True, ""
                elif wins == 1 and losses == len(self.teams) - 1:
                    # One winner, others lose - standard case
                    return True, ""
                else:
                    return False, "For small matches: either one team wins (others lose) OR all teams lose (forfeit/incomplete)."
            else:
                # For 3+ teams, require exactly one winner
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
            wins = sum(1 for result in self.team_results.values() if result == "win")
            
            if "draw" in self.team_results.values():
                result_type = "draw"
                winning_team = None
            elif wins == 0:
                # All losses - forfeit/incomplete match (valid for < 3 teams)
                result_type = "forfeit"
                winning_team = None
            else:
                # Standard win/loss
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
            
            embed.add_field(
                name="🔄 Next Steps",
                value="Players will remain in team channels. Use the **End Game** button below to return everyone to the waiting room, or start a new match with `/create_teams`.",
                inline=False
            )
            
            # Create a new view with just the End Game button for post-match cleanup
            cleanup_view = PostMatchCleanupView(self.voice_manager)
            
            await interaction.followup.send(embed=embed, view=cleanup_view)
            
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
    
    async def end_game(self, interaction: discord.Interaction):
        """End the game without recording results"""
        if self.result_sent:
            await interaction.response.send_message("Match has already been processed!", ephemeral=True)
            return
        
        self.result_sent = True
        
        # Log user action
        print(f"[USER ACTION] {interaction.user.display_name} ({interaction.user.id}) clicked 'End Game' button in guild {interaction.guild.name} ({interaction.guild.id})")
        
        await interaction.response.defer()
        
        try:
            # Import here to avoid circular imports
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
                description="The game has been ended without recording results. All players have been returned to the waiting room.",
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
            label="Finalize Results",
            style=discord.ButtonStyle.success,
            emoji="📝",
            disabled=True  # Disabled until all teams have results
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle result submission"""
        # Log user action
        print(f"[USER ACTION] {interaction.user.display_name} ({interaction.user.id}) clicked 'Finalize Results' button in guild {interaction.guild.name} ({interaction.guild.id})")
        await self.view.submit_results(interaction)

class EndGameButton(discord.ui.Button):
    """Button to end the game without recording results"""
    
    def __init__(self):
        super().__init__(
            label="End Game",
            style=discord.ButtonStyle.danger,
            emoji="🛑"
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Handle ending the game"""
        await self.view.end_game(interaction)

class PostMatchCleanupView(discord.ui.View):
    """View with End Game button for post-match cleanup"""
    
    def __init__(self, voice_manager):
        super().__init__(timeout=1800)  # 30 minute timeout
        self.voice_manager = voice_manager
    
    @discord.ui.button(label='🛑 End Game', style=discord.ButtonStyle.danger)
    async def end_game(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Return all players to waiting room"""
        # Log user action
        print(f"[USER ACTION] {interaction.user.display_name} ({interaction.user.id}) clicked 'End Game' button (post-match) in guild {interaction.guild.name} ({interaction.guild.id})")
        
        await interaction.response.defer()
        
        try:
            # Clean up team channels and return players to waiting room
            await self.voice_manager.cleanup_team_channels(
                interaction.guild, 
                return_to_waiting=True
            )
            
            # Clear active match
            self.voice_manager.clear_active_match(interaction.guild.id)
            
            embed = discord.Embed(
                title="🛑 Game Ended",
                description="All players have been returned to the waiting room.",
                color=Config.SUCCESS_COLOR
            )
            embed.add_field(
                name="🔄 What's Next",
                value="Use `/create_teams` to start a new match when ready.",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error in post-match cleanup: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description=f"An error occurred during cleanup: {str(e)[:200]}",
                color=Config.ERROR_COLOR
            )
            embed.add_field(
                name="🔧 Manual Cleanup",
                value="You may need to use `/cleanup` command to manually clean up channels.",
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Disable the button
        button.disabled = True
        await interaction.edit_original_response(view=self)

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
        self.value = None
    
    @discord.ui.button(label='✅ Confirm', style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle confirmation"""
        self.value = True
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        self.stop()
    
    @discord.ui.button(label='❌ Cancel', style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle cancellation"""
        self.value = False
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        self.stop()
    
    async def on_timeout(self):
        """Handle timeout"""
        self.value = None
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        self.stop()

class PlacementResultView(discord.ui.View):
    """Interactive dialogue for recording placement-based match results"""
    
    def __init__(self, teams: List[List[Dict]], match_id: str, voice_manager):
        super().__init__(timeout=300)  # 5 minute timeout for result recording
        self.teams = teams
        self.match_id = match_id
        self.voice_manager = voice_manager
        self.team_placements = {}  # team_number -> placement
        self.result_sent = False
        
        # Create placement input for each team
        for i, team in enumerate(teams):
            team_names = [player['username'] for player in team]
            
            # Truncate usernames to prevent long strings
            truncated_names = []
            for name in team_names[:3]:
                if len(name) > 12:  # Truncate long usernames
                    truncated_names.append(name[:9] + "...")
                else:
                    truncated_names.append(name)
            
            team_display = f"Team {i+1}: {', '.join(truncated_names)}"
            if len(team_names) > 3:
                team_display += f" (+{len(team_names)-3})"
            
            # Ensure team_display doesn't exceed reasonable length
            if len(team_display) > 35:
                team_display = team_display[:32] + "..."
            
            # Add team placement button
            button = TeamPlacementButton(
                team_number=i+1,
                team_display=team_display,
                parent_view=self
            )
            self.add_item(button)
        
        # Add submit and end game buttons
        self.add_item(SubmitPlacementResultsButton())
        self.add_item(EndGameButton())
    
    def update_team_placement(self, team_number: int, placement: int):
        """Update a team's placement"""
        self.team_placements[team_number] = placement
        
        # Check if all teams have placements
        if len(self.team_placements) == len(self.teams):
            # Enable submit button
            for item in self.children:
                if isinstance(item, SubmitPlacementResultsButton):
                    item.disabled = False
                    break
    
    def validate_placements(self) -> tuple[bool, str]:
        """Validate that placements make sense"""
        if len(self.team_placements) != len(self.teams):
            return False, "Please set placement for all teams."
        
        placements = list(self.team_placements.values())
        
        # Check for valid range (1 to 30, with 30+ treated as 30)
        if min(placements) < 1:
            return False, "Placements must be 1 or higher."
        
        if max(placements) > 30:
            return False, "Maximum supported placement is 30."
        
        # For guild-only matches (all teams within guild), check for duplicates
        max_placement = max(placements)
        if max_placement <= len(self.teams):
            # This appears to be a guild-only match, enforce unique consecutive placements
            if len(set(placements)) != len(placements):
                return False, "Each team must have a unique placement (no ties)."
            
            expected_placements = set(range(1, len(self.teams) + 1))
            if set(placements) != expected_placements:
                return False, f"For guild-only matches, must use placements 1 through {len(self.teams)} exactly once each."
        else:
            # This appears to be an external competition, allow any placements 1-30
            if len(set(placements)) != len(placements):
                return False, "Each team must have a unique placement (no ties)."
        
        return True, ""
    
    def calculate_rating_change(self, placement: int) -> float:
        """Calculate rating change based on placement (Rank 7 baseline system)"""
        baseline_rank = 7
        max_rank = 30
        
        if placement <= baseline_rank:
            # Above baseline: scale from 0 to +25
            if placement == baseline_rank:
                return 0.0
            performance_score = (baseline_rank - placement) / (baseline_rank - 1)
            rating_change = performance_score * 25
        else:
            # Below baseline: scale from 0 to -40
            if placement >= max_rank:
                return -40.0
            performance_score = (placement - baseline_rank) / (max_rank - baseline_rank)
            rating_change = -performance_score * 40
        
        return rating_change
    
    async def end_game(self, interaction: discord.Interaction):
        """End the game without recording results"""
        if self.result_sent:
            await interaction.response.send_message("Results have already been submitted!", ephemeral=True)
            return
        
        self.result_sent = True
        
        # Create confirmation embed
        embed = discord.Embed(
            title="🔚 Game Ended",
            description="The match has been ended without recording results.\nNo ratings were changed.",
            color=Config.WARNING_COLOR
        )
        embed.set_footer(text=get_bot_footer_text())
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)
        
        # Clean up voice channels (similar to /cleanup command)
        if self.voice_manager:
            try:
                # Pass the guild argument that cleanup_team_channels expects
                await self.voice_manager.cleanup_team_channels(interaction.guild, return_to_waiting=True)
                
                # Clear the active match
                self.voice_manager.clear_active_match(interaction.guild.id)
                
            except Exception as e:
                logger.error(f"Error cleaning up voice channels: {e}")
        
        self.stop()
    
    async def submit_results(self, interaction: discord.Interaction):
        """Submit the placement results"""
        if self.result_sent:
            await interaction.response.send_message("Results have already been submitted!", ephemeral=True)
            return
        
        # Validate placements
        is_valid, error_msg = self.validate_placements()
        if not is_valid:
            await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
            return
        
        self.result_sent = True
        await interaction.response.defer()
        
        try:
            # Import here to avoid circular imports
            from services.api_client import api_client
            
            # Record placement-based result in database
            result_data = await api_client.record_placement_result(
                match_id=self.match_id,
                team_placements=self.team_placements
            )
            
            if not result_data:
                embed = discord.Embed(
                    title="❌ Database Error",
                    description="Failed to record match result. Please try again.",
                    color=Config.ERROR_COLOR
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # Create success embed with rating changes
            embed = discord.Embed(
                title="✅ Placement Results Recorded",
                description="Match results have been successfully recorded!",
                color=Config.SUCCESS_COLOR
            )
            
            # Show placement results with rating changes
            results_text = []
            for team_num in sorted(self.team_placements.keys()):
                placement = self.team_placements[team_num]
                rating_change = self.calculate_rating_change(placement)
                
                # Get team names
                team = self.teams[team_num - 1]
                team_names = [player['username'] for player in team]
                team_display = ', '.join(team_names[:2])
                if len(team_names) > 2:
                    team_display += f" (+{len(team_names)-2} more)"
                
                # Add placement emoji
                if placement == 1:
                    emoji = "🥇"
                elif placement == 2:
                    emoji = "🥈"
                elif placement == 3:
                    emoji = "🥉"
                else:
                    emoji = f"{placement}."
                
                results_text.append(f"{emoji} **Team {team_num}**: {team_display} ({rating_change:+.1f} rating)")
            
            embed.add_field(
                name="🏆 Final Placements",
                value="\n".join(results_text),
                inline=False
            )
            
            embed.set_footer(text=get_bot_footer_text())
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            # Update the original message to show disabled buttons
            await interaction.edit_original_response(view=self)
            
            await interaction.followup.send(embed=embed)
            
            # Clean up voice channels (similar to /cleanup command)
            if self.voice_manager:
                try:
                    # Pass the guild argument that cleanup_team_channels expects
                    await self.voice_manager.cleanup_team_channels(interaction.guild, return_to_waiting=True)
                    
                    # Clear the active match
                    self.voice_manager.clear_active_match(interaction.guild.id)
                    
                except Exception as e:
                    logger.error(f"Error cleaning up voice channels: {e}")
            
        except Exception as e:
            logger.error(f"Error submitting placement results: {e}")
            embed = discord.Embed(
                title="❌ Submission Error",
                description="An error occurred while recording results. Please try again.",
                color=Config.ERROR_COLOR
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

class TeamPlacementButton(discord.ui.Button):
    """Button for setting team placement"""
    
    def __init__(self, team_number: int, team_display: str, parent_view):
        super().__init__(
            label=f"Set Team {team_number} Placement",
            style=discord.ButtonStyle.secondary,
            emoji="📊"
        )
        self.team_number = team_number
        self.team_display = team_display
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        """Show placement input modal"""
        modal = PlacementInputModal(self.team_number, self.team_display, self.parent_view)
        await interaction.response.send_modal(modal)

class PlacementInputModal(discord.ui.Modal):
    """Modal for entering team placement"""
    
    def __init__(self, team_number: int, team_display: str, parent_view):
        # Truncate title to Discord's 45 character limit
        title = f"Set Placement for Team {team_number}"
        if len(title) > 45:
            title = title[:42] + "..."
        
        super().__init__(title=title)
        self.team_number = team_number
        self.team_display = team_display
        self.parent_view = parent_view
        
        # Truncate label to Discord's 45 character limit
        label = f"Placement for Team {team_number}"
        if len(label) > 45:
            label = label[:42] + "..."
        
        # Truncate placeholder to Discord's 100 character limit
        placeholder = "Enter placement (1-30, where 1 = 1st place)"
        if len(placeholder) > 100:
            placeholder = placeholder[:97] + "..."
        
        self.placement_input = discord.ui.TextInput(
            label=label,
            placeholder=placeholder,
            min_length=1,
            max_length=2,
            required=True
        )
        self.add_item(self.placement_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle placement submission"""
        try:
            placement = int(self.placement_input.value)
            
            if placement < 1:
                await interaction.response.send_message(
                    "❌ Placement must be 1 or higher (1 = 1st place)",
                    ephemeral=True
                )
                return
            
            # Allow placements 1-30, anything over 30 is treated as 30
            if placement > 30:
                placement = 30
                await interaction.response.send_message(
                    f"ℹ️ Placement {self.placement_input.value} adjusted to 30 (maximum supported rank)",
                    ephemeral=True
                )
                # Continue with placement = 30
            
            # For guild matches, still check if placement exceeds team count
            # But allow higher placements for external competitions
            if placement <= len(self.parent_view.teams):
                # Check if placement is already taken (only for guild team placements)
                for team_num, existing_placement in self.parent_view.team_placements.items():
                    if existing_placement == placement and team_num != self.team_number:
                        await interaction.response.send_message(
                            f"❌ Placement {placement} is already assigned to Team {team_num}",
                            ephemeral=True
                        )
                        return
            
            # Update placement
            self.parent_view.update_team_placement(self.team_number, placement)
            
            # Calculate rating change for preview
            rating_change = self.parent_view.calculate_rating_change(placement)
            
            # Update button label to show current placement
            for item in self.parent_view.children:
                if isinstance(item, TeamPlacementButton) and item.team_number == self.team_number:
                    if placement == 1:
                        emoji = "🥇"
                    elif placement == 2:
                        emoji = "🥈"
                    elif placement == 3:
                        emoji = "🥉"
                    elif placement <= 10:
                        emoji = f"🏆"
                    elif placement <= 20:
                        emoji = f"📊"
                    else:
                        emoji = f"🔻"
                    
                    item.label = f"Team {self.team_number}: {placement}. ({rating_change:+.1f})"
                    item.style = discord.ButtonStyle.success
                    break
            
            await interaction.response.edit_message(view=self.parent_view)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number for placement",
                ephemeral=True
            )

class SubmitPlacementResultsButton(discord.ui.Button):
    """Button to submit all placement results"""
    
    def __init__(self):
        super().__init__(
            label="Finalize Results",
            style=discord.ButtonStyle.success,
            emoji="✅",
            disabled=True  # Disabled until all placements are set
        )
    
    async def callback(self, interaction: discord.Interaction):
        """Submit placement results"""
        await self.view.submit_results(interaction)