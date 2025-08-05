import discord
import asyncio
import logging
from typing import Dict, List, Any
from utils.constants import Config

logger = logging.getLogger(__name__)

class TeamProposalView(discord.ui.View):
    """Interactive buttons for team proposals"""
    
    def __init__(self, teams: List[List[Dict]], team_channels: List[discord.VoiceChannel], 
                 match_id: str, voice_manager, timeout: float = Config.TEAM_PROPOSAL_TIMEOUT):
        super().__init__(timeout=timeout)
        self.teams = teams
        self.team_channels = team_channels
        self.match_id = match_id
        self.voice_manager = voice_manager
        
        # Track votes
        self.accept_votes: set = set()
        self.decline_votes: set = set()
        self.all_players: set = set()
        
        # Get all player IDs
        for team in teams:
            for player in team:
                if 'discord_member' in player:
                    self.all_players.add(player['discord_member'].id)
        
        self.votes_needed = max(1, len(self.all_players) // 2)  # Simple majority
        self.result_sent = False
    
    @discord.ui.button(label='✅ Accept Teams', style=discord.ButtonStyle.success)
    async def accept_teams(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle accept vote"""
        user_id = interaction.user.id
        
        # Check if user is in the match
        if user_id not in self.all_players:
            await interaction.response.send_message(
                "❌ You're not part of this match!", 
                ephemeral=True
            )
            return
        
        # Remove from decline votes if present
        self.decline_votes.discard(user_id)
        
        # Add to accept votes
        if user_id in self.accept_votes:
            await interaction.response.send_message(
                "✅ You've already voted to accept!", 
                ephemeral=True
            )
            return
        
        self.accept_votes.add(user_id)
        
        accept_count = len(self.accept_votes)
        total_players = len(self.all_players)
        
        await interaction.response.send_message(
            f"✅ Vote recorded! ({accept_count}/{total_players} players voted to accept)", 
            ephemeral=True
        )
        
        # Check if we have enough votes to proceed
        if accept_count >= self.votes_needed and not self.result_sent:
            await self._handle_accepted(interaction)
    
    @discord.ui.button(label='❌ Decline Teams', style=discord.ButtonStyle.danger)
    async def decline_teams(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle decline vote"""
        user_id = interaction.user.id
        
        # Check if user is in the match
        if user_id not in self.all_players:
            await interaction.response.send_message(
                "❌ You're not part of this match!", 
                ephemeral=True
            )
            return
        
        # Remove from accept votes if present
        self.accept_votes.discard(user_id)
        
        # Add to decline votes
        if user_id in self.decline_votes:
            await interaction.response.send_message(
                "❌ You've already voted to decline!", 
                ephemeral=True
            )
            return
        
        self.decline_votes.add(user_id)
        
        decline_count = len(self.decline_votes)
        total_players = len(self.all_players)
        
        await interaction.response.send_message(
            f"❌ Vote recorded! ({decline_count}/{total_players} players voted to decline)", 
            ephemeral=True
        )
        
        # Check if we have enough votes to decline
        if decline_count >= self.votes_needed and not self.result_sent:
            await self._handle_declined(interaction)
    
    async def _handle_accepted(self, interaction: discord.Interaction):
        """Handle when teams are accepted"""
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
            
            success = await self.voice_manager.move_players_to_teams(discord_teams, self.team_channels)
            
            if success:
                # Store active match info
                self.voice_manager.set_active_match(interaction.guild.id, {
                    'match_id': self.match_id,
                    'teams': self.teams,
                    'team_channels': self.team_channels,
                    'status': 'active'
                })
                
                embed = discord.Embed(
                    title="🎮 Teams Accepted!",
                    description="Players have been moved to their team channels. Good luck!",
                    color=Config.SUCCESS_COLOR
                )
                embed.add_field(
                    name="📝 After Your Match",
                    value="Use `/record_result <winning_team>` to record the outcome and update ratings.",
                    inline=False
                )
                
                await interaction.followup.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="⚠️ Teams Accepted",
                    description="Teams were accepted but there was an issue moving players. Please move manually to team channels.",
                    color=Config.WARNING_COLOR
                )
                await interaction.followup.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error handling accepted teams: {e}")
            embed = discord.Embed(
                title="❌ Error",
                description="Teams were accepted but an error occurred. Please try manually moving to team channels.",
                color=Config.ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(view=self)
    
    async def _handle_declined(self, interaction: discord.Interaction):
        """Handle when teams are declined"""
        self.result_sent = True
        
        try:
            # Clean up team channels
            await self.voice_manager.cleanup_team_channels(
                interaction.guild, 
                return_to_waiting=False  # Players are already in waiting room
            )
            
            # Clear active match
            self.voice_manager.clear_active_match(interaction.guild.id)
            
            embed = discord.Embed(
                title="❌ Teams Declined",
                description="The team proposal was declined. Use `/create_teams` to generate new teams.",
                color=Config.ERROR_COLOR
            )
            
            await interaction.followup.send(embed=embed)
        
        except Exception as e:
            logger.error(f"Error handling declined teams: {e}")
            embed = discord.Embed(
                title="❌ Teams Declined",
                description="The team proposal was declined, but there was an error during cleanup.",
                color=Config.ERROR_COLOR
            )
            await interaction.followup.send(embed=embed)
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.edit_original_response(view=self)
    
    async def on_timeout(self):
        """Handle timeout"""
        if not self.result_sent:
            logger.info(f"Team proposal timed out for match {self.match_id}")
            
            # Disable all buttons
            for item in self.children:
                item.disabled = True
            
            # Note: We can't send new messages on timeout, but we can edit the original
            # The timeout message will be handled by the command that created this view

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