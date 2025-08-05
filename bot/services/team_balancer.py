import discord
import random
import logging
from typing import List, Dict, Tuple, Any
from services.api_client import api_client
from utils.constants import Config

logger = logging.getLogger(__name__)

class TeamBalancer:
    """Team balancing algorithm with snake draft"""
    
    def __init__(self):
        pass
    
    async def create_balanced_teams(self, members: List[discord.Member], num_teams: int, guild_id: int) -> Tuple[List[List[Dict]], List[float], float]:
        """
        Main balancing algorithm with special cases for small player counts
        Returns: (teams_with_data, team_ratings, balance_score)
        """
        if len(members) < Config.MIN_PLAYERS_FOR_TEAMS:
            raise ValueError(f"Need at least {Config.MIN_PLAYERS_FOR_TEAMS} players")
        
        if len(members) > Config.MAX_PLAYERS_PER_MATCH:
            raise ValueError(f"Too many players (max {Config.MAX_PLAYERS_PER_MATCH})")
        
        # Get user ratings from database (auto-register if needed)
        players_with_ratings = await self._get_player_ratings(members, guild_id)
        
        # Handle special cases for small player counts
        if len(members) <= Config.SINGLE_TEAM_THRESHOLD:
            # 1-4 players: Create single team
            teams = [players_with_ratings]  # All players in one team
            num_teams = 1
            logger.info(f"Special case: {len(members)} players - creating single team")
        elif len(members) == Config.TWO_TEAM_THRESHOLD:
            # 5 players: Split 2:3
            teams = self._split_five_players(players_with_ratings)
            num_teams = 2
            logger.info(f"Special case: 5 players - splitting 2:3")
        else:
            # 6+ players: Use normal balancing algorithm
            teams = self._snake_draft_balance(players_with_ratings, num_teams)
        
        # Calculate team ratings and balance score
        team_ratings = [self._calculate_team_rating(team) for team in teams]
        balance_score = self._calculate_balance_score(team_ratings)
        
        logger.info(f"Created {num_teams} teams with balance score: {balance_score:.2f}")
        logger.info(f"Team ratings: {[f'{rating:.1f}' for rating in team_ratings]}")
        
        return teams, team_ratings, balance_score
    
    async def _get_player_ratings(self, members: List[discord.Member], guild_id: int) -> List[Dict]:
        """Get player ratings from database, auto-registering if needed"""
        players_with_ratings = []
        
        for member in members:
            try:
                # Try to get existing user
                user_data = await api_client.get_user(guild_id, member.id)
                
                if not user_data:
                    # Auto-register user with default rating
                    logger.info(f"Auto-registering user {member.display_name} ({member.id})")
                    user_data = await api_client.create_user(
                        guild_id=guild_id,
                        user_id=member.id,
                        username=member.display_name
                    )
                
                if user_data:
                    # Add Discord member reference for easier access
                    user_data['discord_member'] = member
                    players_with_ratings.append(user_data)
                else:
                    # Fallback: create default data
                    logger.warning(f"Failed to get/create user data for {member.display_name}, using defaults")
                    players_with_ratings.append({
                        'user_id': member.id,
                        'username': member.display_name,
                        'rating_mu': Config.DEFAULT_RATING_MU,
                        'rating_sigma': Config.DEFAULT_RATING_SIGMA,
                        'games_played': 0,
                        'discord_member': member
                    })
                    
            except Exception as e:
                logger.error(f"Error getting rating for {member.display_name}: {e}")
                # Fallback: use default rating
                players_with_ratings.append({
                    'user_id': member.id,
                    'username': member.display_name,
                    'rating_mu': Config.DEFAULT_RATING_MU,
                    'rating_sigma': Config.DEFAULT_RATING_SIGMA,
                    'games_played': 0,
                    'discord_member': member
                })
        
        return players_with_ratings
    
    def _split_five_players(self, players: List[Dict]) -> List[List[Dict]]:
        """
        Split 5 players into 2 teams (2:3 split)
        Put the 2 highest rated players on one team, 3 lowest on the other
        """
        # Sort players by effective rating (mu - sigma for conservative estimate)
        sorted_players = sorted(
            players,
            key=lambda p: p['rating_mu'] - (p['rating_sigma'] * 0.5),
            reverse=True
        )
        
        # Split: top 2 players vs bottom 3 players
        team1 = sorted_players[:2]  # Top 2 players
        team2 = sorted_players[2:]  # Bottom 3 players
        
        # Log team composition
        team1_names = [p['username'] for p in team1]
        team2_names = [p['username'] for p in team2]
        team1_avg = sum(p['rating_mu'] for p in team1) / len(team1)
        team2_avg = sum(p['rating_mu'] for p in team2) / len(team2)
        
        logger.info(f"Team 1 (2 players): {team1_names} (avg: {team1_avg:.1f})")
        logger.info(f"Team 2 (3 players): {team2_names} (avg: {team2_avg:.1f})")
        
        return [team1, team2]
    
    def _snake_draft_balance(self, players: List[Dict], num_teams: int) -> List[List[Dict]]:
        """
        Snake draft algorithm:
        - Sort players by rating (highest to lowest)
        - Distribute using snake pattern (1→2→3→3→2→1)
        """
        # Sort players by effective rating (mu - sigma for conservative estimate)
        sorted_players = sorted(
            players,
            key=lambda p: p['rating_mu'] - (p['rating_sigma'] * 0.5),
            reverse=True
        )
        
        # Initialize teams
        teams = [[] for _ in range(num_teams)]
        
        # Snake draft distribution
        team_index = 0
        direction = 1  # 1 for forward, -1 for backward
        
        for player in sorted_players:
            teams[team_index].append(player)
            
            # Move to next team
            team_index += direction
            
            # Reverse direction when reaching ends
            if team_index >= num_teams:
                team_index = num_teams - 1
                direction = -1
            elif team_index < 0:
                team_index = 0
                direction = 1
        
        # Log team composition
        for i, team in enumerate(teams):
            team_names = [p['username'] for p in team]
            team_ratings = [p['rating_mu'] for p in team]
            avg_rating = sum(team_ratings) / len(team_ratings) if team_ratings else 0
            logger.info(f"Team {i+1}: {team_names} (avg: {avg_rating:.1f})")
        
        return teams
    
    def _calculate_team_rating(self, team: List[Dict]) -> float:
        """Calculate average team rating"""
        if not team:
            return Config.DEFAULT_RATING_MU
        
        # Use mu (skill estimate) for team rating calculation
        ratings = [player['rating_mu'] for player in team]
        return sum(ratings) / len(ratings)
    
    def _calculate_balance_score(self, team_ratings: List[float]) -> float:
        """
        Calculate how balanced the teams are
        Lower score = better balance
        Based on variance between team average ratings
        """
        if len(team_ratings) < 2:
            return 0.0
        
        # Calculate variance of team ratings
        mean_rating = sum(team_ratings) / len(team_ratings)
        variance = sum((rating - mean_rating) ** 2 for rating in team_ratings) / len(team_ratings)
        
        # Return standard deviation as balance score
        return variance ** 0.5
    
    def _advanced_balance(self, players: List[Dict], num_teams: int, max_iterations: int = 1000) -> List[List[Dict]]:
        """
        Advanced balancing using iterative improvement
        (Optional enhancement - currently not used)
        """
        # Start with snake draft
        best_teams = self._snake_draft_balance(players, num_teams)
        best_score = self._calculate_balance_score([self._calculate_team_rating(team) for team in best_teams])
        
        # Try to improve through random swaps
        for _ in range(max_iterations):
            # Make a copy for testing
            test_teams = [team.copy() for team in best_teams]
            
            # Random swap between two teams
            team1_idx = random.randint(0, num_teams - 1)
            team2_idx = random.randint(0, num_teams - 1)
            
            while team1_idx == team2_idx or not test_teams[team1_idx] or not test_teams[team2_idx]:
                team1_idx = random.randint(0, num_teams - 1)
                team2_idx = random.randint(0, num_teams - 1)
            
            # Swap random players
            player1_idx = random.randint(0, len(test_teams[team1_idx]) - 1)
            player2_idx = random.randint(0, len(test_teams[team2_idx]) - 1)
            
            player1 = test_teams[team1_idx][player1_idx]
            player2 = test_teams[team2_idx][player2_idx]
            
            test_teams[team1_idx][player1_idx] = player2
            test_teams[team2_idx][player2_idx] = player1
            
            # Check if this improves balance
            test_ratings = [self._calculate_team_rating(team) for team in test_teams]
            test_score = self._calculate_balance_score(test_ratings)
            
            if test_score < best_score:
                best_teams = test_teams
                best_score = test_score
                logger.debug(f"Improved balance score to {best_score:.2f}")
        
        return best_teams
    
    def validate_teams(self, teams: List[List[Dict]], original_members: List[discord.Member]) -> bool:
        """Validate that teams contain all original members exactly once"""
        # Flatten teams to get all players
        all_team_players = []
        for team in teams:
            for player in team:
                all_team_players.append(player['user_id'])
        
        # Check that we have all original members
        original_ids = [member.id for member in original_members]
        
        if len(all_team_players) != len(original_ids):
            logger.error(f"Team player count mismatch: {len(all_team_players)} != {len(original_ids)}")
            return False
        
        if set(all_team_players) != set(original_ids):
            logger.error("Team players don't match original members")
            return False
        
        return True
    
    def get_team_composition_summary(self, teams: List[List[Dict]]) -> str:
        """Get a text summary of team composition"""
        summary_lines = []
        
        for i, team in enumerate(teams):
            if not team:
                continue
                
            team_rating = self._calculate_team_rating(team)
            player_names = [p['username'] for p in team]
            
            summary_lines.append(f"**Team {i+1}** (Avg: {team_rating:.0f}): {', '.join(player_names)}")
        
        return "\n".join(summary_lines)