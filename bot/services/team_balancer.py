import discord
import random
import logging
import time
from typing import List, Dict, Tuple, Any
from services.api_client import api_client
from utils.constants import Config

logger = logging.getLogger(__name__)

class TeamBalancer:
    """Team balancing algorithm with snake draft"""
    
    def __init__(self):
        # Seed random number generator with current time to ensure different results
        random.seed(int(time.time() * 1000000) % 2147483647)
        logger.debug(f"TeamBalancer initialized with random seed based on time")
    
    async def create_teams_with_custom_sizes(self, members: List[discord.Member], team_sizes: List[int], guild_id: int, required_region: str = None) -> Tuple[List[List[Dict]], List[float], float]:
        """
        Create teams with custom specified sizes (e.g., [3, 3, 4] for 3:3:4 format)
        """
        # Get player ratings
        players_with_ratings = await self._get_player_ratings(members, guild_id)
        
        # Validate total players match team sizes
        total_required = sum(team_sizes)
        if len(players_with_ratings) != total_required:
            raise ValueError(f"Player count ({len(players_with_ratings)}) doesn't match required total ({total_required})")
        
        # Create teams with custom sizes
        if required_region:
            teams = self._create_custom_teams_with_region(players_with_ratings, team_sizes, required_region)
        else:
            teams = self._create_custom_teams(players_with_ratings, team_sizes)
        
        # Calculate team ratings and balance score
        team_ratings = [self._calculate_team_rating(team) for team in teams]
        balance_score = self._calculate_balance_score(team_ratings)
        
        return teams, team_ratings, balance_score
    
    def _create_custom_teams(self, players: List[Dict], team_sizes: List[int]) -> List[List[Dict]]:
        """
        Create teams with custom sizes using snake draft for balance with randomization
        """
        # Sort players by rating
        sorted_players = sorted(
            players,
            key=lambda p: p['rating_mu'] - (p['rating_sigma'] * 0.5),
            reverse=True
        )
        
        # Apply controlled randomization for variety while maintaining balance
        sorted_players = self._shuffle_rating_bands(sorted_players)
        sorted_players = self._randomize_similar_ratings(sorted_players)
        
        # Initialize teams
        teams = [[] for _ in range(len(team_sizes))]
        
        # Snake draft with size constraints and random starting team
        team_index = self._get_random_starting_team(len(team_sizes))
        direction = 1
        
        logger.debug(f"Custom teams: Starting snake draft with team {team_index + 1} (randomized)")
        
        for player in sorted_players:
            # Find next available team that isn't full
            attempts = 0
            while len(teams[team_index]) >= team_sizes[team_index] and attempts < len(team_sizes):
                team_index += direction
                
                # Reverse direction when reaching ends
                if team_index >= len(team_sizes):
                    team_index = len(team_sizes) - 1
                    direction = -1
                elif team_index < 0:
                    team_index = 0
                    direction = 1
                
                attempts += 1
            
            # Add player to current team
            teams[team_index].append(player)
            
            # Move to next team
            team_index += direction
            
            # Reverse direction when reaching ends
            if team_index >= len(team_sizes):
                team_index = len(team_sizes) - 1
                direction = -1
            elif team_index < 0:
                team_index = 0
                direction = 1
        
        # Log team composition
        for i, team in enumerate(teams):
            team_names = [p['username'] for p in team]
            team_ratings = [p['rating_mu'] for p in team]
            avg_rating = sum(team_ratings) / len(team_ratings) if team_ratings else 0
            logger.info(f"Custom Team {i+1} ({len(team)}/{team_sizes[i]} players): {team_names} (avg: {avg_rating:.1f})")
        
        return teams
    
    def _create_custom_teams_with_region(self, players: List[Dict], team_sizes: List[int], required_region: str) -> List[List[Dict]]:
        """
        Create teams with custom sizes and region requirement
        """
        # Separate players by region
        region_players = [p for p in players if p.get('region_code') == required_region]
        non_region_players = [p for p in players if p.get('region_code') != required_region]
        
        # Sort both groups by rating
        region_players.sort(key=lambda p: p['rating_mu'] - (p['rating_sigma'] * 0.5), reverse=True)
        non_region_players.sort(key=lambda p: p['rating_mu'] - (p['rating_sigma'] * 0.5), reverse=True)
        
        # Initialize teams
        teams = [[] for _ in range(len(team_sizes))]
        
        # First, distribute regional players (one per team if possible)
        for i in range(min(len(region_players), len(team_sizes))):
            teams[i].append(region_players[i])
        
        # Add remaining regional players using custom distribution
        remaining_region_players = region_players[len(team_sizes):]
        if remaining_region_players:
            self._distribute_players_custom(remaining_region_players, teams, team_sizes)
        
        # Distribute non-regional players using custom distribution
        if non_region_players:
            self._distribute_players_custom(non_region_players, teams, team_sizes)
        
        return teams
    
    def _distribute_players_custom(self, players: List[Dict], teams: List[List[Dict]], team_sizes: List[int]):
        """
        Distribute players to teams with custom size constraints
        """
        team_index = 0
        direction = 1
        
        for player in players:
            # Find next available team that isn't full
            attempts = 0
            while len(teams[team_index]) >= team_sizes[team_index] and attempts < len(team_sizes):
                team_index += direction
                
                # Reverse direction when reaching ends
                if team_index >= len(team_sizes):
                    team_index = len(team_sizes) - 1
                    direction = -1
                elif team_index < 0:
                    team_index = 0
                    direction = 1
                
                attempts += 1
            
            # Add player to current team
            teams[team_index].append(player)
            
            # Move to next team
            team_index += direction
            
            # Reverse direction when reaching ends
            if team_index >= len(team_sizes):
                team_index = len(team_sizes) - 1
                direction = -1
            elif team_index < 0:
                team_index = 0
                direction = 1
    
    async def create_balanced_teams(self, members: List[discord.Member], num_teams: int, guild_id: int, required_region: str = None) -> Tuple[List[List[Dict]], List[float], float]:
        """
        Main balancing algorithm with special cases for small player counts and region requirements
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
            # 5 players: Split 2:3 with region consideration
            teams = self._split_five_players(players_with_ratings, required_region)
            num_teams = 2
            logger.info(f"Special case: 5 players - splitting 2:3")
        else:
            # 6+ players: Use normal balancing algorithm with region requirement
            teams = self._create_balanced_teams_with_region(players_with_ratings, num_teams, required_region)
        
        # Calculate team ratings and balance score
        team_ratings = [self._calculate_team_rating(team) for team in teams]
        balance_score = self._calculate_balance_score(team_ratings)
        
        logger.info(f"Created {num_teams} teams with balance score: {balance_score:.2f}")
        logger.info(f"Team ratings: {[f'{rating:.1f}' for rating in team_ratings]}")
        if required_region:
            logger.info(f"Region requirement: {required_region}")
        
        return teams, team_ratings, balance_score
    
    async def _get_player_ratings(self, members: List[discord.Member], guild_id: int) -> List[Dict]:
        """Get player ratings from database, auto-registering if needed"""
        players_with_ratings = []
        
        for member in members:
            try:
                # Try to get existing user with completed match statistics
                user_data = await api_client.get_user_completed_stats(guild_id, member.id)
                
                if not user_data:
                    # Auto-register user with default rating
                    logger.info(f"Auto-registering user {member.display_name} ({member.id})")
                    user_data = await api_client.create_user(
                        guild_id=guild_id,
                        user_id=member.id,
                        username=member.display_name
                    )
                    
                    # Convert to completed stats format for consistency
                    if user_data:
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
    
    def _split_five_players(self, players: List[Dict], required_region: str = None) -> List[List[Dict]]:
        """
        Split 5 players into 2 teams (2:3 split) with optional region requirement
        Put the 2 highest rated players on one team, 3 lowest on the other
        If region is required, ensure each team has at least one player from that region
        """
        # Sort players by effective rating (mu - sigma for conservative estimate)
        sorted_players = sorted(
            players,
            key=lambda p: p['rating_mu'] - (p['rating_sigma'] * 0.5),
            reverse=True
        )
        
        if not required_region:
            # Simple 2:3 split without region requirement
            team1 = sorted_players[:2]  # Top 2 players
            team2 = sorted_players[2:]  # Bottom 3 players
        else:
            # Region-based split
            region_players = [p for p in sorted_players if p.get('region_code') == required_region]
            non_region_players = [p for p in sorted_players if p.get('region_code') != required_region]
            
            if len(region_players) < 2:
                # Not enough regional players for both teams, use simple split
                logger.warning(f"Only {len(region_players)} players from region {required_region}, using simple split")
                team1 = sorted_players[:2]
                team2 = sorted_players[2:]
            else:
                # Distribute regional players: one per team
                team1 = [region_players[0]]  # Best regional player to team 1
                team2 = [region_players[1]]  # Second best regional player to team 2
                
                # Add remaining regional players to team 2 (the larger team)
                for i in range(2, len(region_players)):
                    team2.append(region_players[i])
                
                # Distribute non-regional players to balance teams
                # Team 1 needs 1 more player, Team 2 needs remaining players
                if non_region_players:
                    team1.append(non_region_players[0])  # Best non-regional to team 1
                    team2.extend(non_region_players[1:])  # Rest to team 2
        
        # Log team composition
        team1_names = [p['username'] for p in team1]
        team2_names = [p['username'] for p in team2]
        team1_avg = sum(p['rating_mu'] for p in team1) / len(team1)
        team2_avg = sum(p['rating_mu'] for p in team2) / len(team2)
        
        logger.info(f"Team 1 (2 players): {team1_names} (avg: {team1_avg:.1f})")
        logger.info(f"Team 2 (3 players): {team2_names} (avg: {team2_avg:.1f})")
        
        return [team1, team2]
    
    def _shuffle_rating_bands(self, players: List[Dict]) -> List[Dict]:
        """
        Group players by rating bands and shuffle within each band
        Preserves overall skill distribution while adding variety
        """
        if len(players) < 2:  # Lowered from Config.MIN_RANDOMIZATION_PLAYERS
            logger.debug(f"Skipping rating band shuffle - only {len(players)} players")
            return players  # Not enough players to benefit from randomization
        
        # Log player ratings for debugging
        player_ratings = [f"{p['username']}({p['rating_mu']:.0f})" for p in players]
        logger.debug(f"Players before band shuffle: {player_ratings}")
        
        # Group players into rating bands
        rating_bands = {}
        
        for player in players:
            rating = player['rating_mu']
            # Calculate band (e.g., 1500-1599, 1600-1699)
            band = int(rating // Config.RATING_BAND_SIZE) * Config.RATING_BAND_SIZE
            
            if band not in rating_bands:
                rating_bands[band] = []
            rating_bands[band].append(player)
        
        logger.debug(f"Rating bands: {list(rating_bands.keys())}")
        for band, band_players in rating_bands.items():
            ratings_in_band = [f"{p['username']}({p['rating_mu']:.0f})" for p in band_players]
            logger.debug(f"Band {band}: {ratings_in_band}")
        
        # Shuffle within each band (only if band has multiple players)
        shuffled_players = []
        for band in sorted(rating_bands.keys(), reverse=True):  # Process high to low rating bands
            band_players = rating_bands[band]
            if len(band_players) >= 2:  # Only shuffle if 2+ players in band
                before_shuffle = [p['username'] for p in band_players]
                random.shuffle(band_players)
                after_shuffle = [p['username'] for p in band_players]
                logger.info(f"Shuffled band {band}: {before_shuffle} → {after_shuffle}")
            else:
                logger.debug(f"Skipping shuffle for band {band} - only {len(band_players)} player(s)")
            shuffled_players.extend(band_players)
        
        # Log final order after band shuffling
        final_ratings = [f"{p['username']}({p['rating_mu']:.0f})" for p in shuffled_players]
        logger.debug(f"Players after band shuffle: {final_ratings}")
        
        return shuffled_players
    
    def _randomize_similar_ratings(self, players: List[Dict], threshold: float = None) -> List[Dict]:
        """
        When players have very similar ratings (within threshold), 
        randomly shuffle their order to break ties
        """
        if threshold is None:
            threshold = Config.SIMILAR_RATING_THRESHOLD
        
        if len(players) < 2:
            logger.debug(f"Skipping similar ratings shuffle - only {len(players)} players")
            return players
        
        # Log before similar ratings shuffle
        before_similar = [f"{p['username']}({p['rating_mu']:.0f})" for p in players]
        logger.debug(f"Players before similar ratings shuffle (threshold={threshold}): {before_similar}")
        
        randomized_players = []
        i = 0
        
        while i < len(players):
            # Find all players with similar rating to current player
            current_rating = players[i]['rating_mu']
            similar_group = [players[i]]
            j = i + 1
            
            # Group players with similar ratings
            while j < len(players) and abs(players[j]['rating_mu'] - current_rating) <= threshold:
                similar_group.append(players[j])
                j += 1
            
            # Shuffle the group if it has multiple players
            if len(similar_group) > 1:
                before_group = [p['username'] for p in similar_group]
                random.shuffle(similar_group)
                after_group = [p['username'] for p in similar_group]
                logger.info(f"Shuffled similar ratings around {current_rating:.0f}: {before_group} → {after_group}")
            else:
                logger.debug(f"Skipping shuffle for {similar_group[0]['username']} - no similar ratings")
            
            randomized_players.extend(similar_group)
            i = j
        
        # Log final order after similar ratings shuffle
        after_similar = [f"{p['username']}({p['rating_mu']:.0f})" for p in randomized_players]
        logger.debug(f"Players after similar ratings shuffle: {after_similar}")
        
        return randomized_players
    
    def _get_random_starting_team(self, num_teams: int) -> int:
        """
        Randomly select which team gets the first player in snake draft
        Prevents Team 1 from always getting the best player
        """
        starting_team = random.randint(0, num_teams - 1)
        logger.info(f"Random starting team selected: Team {starting_team + 1} (out of {num_teams} teams)")
        return starting_team
    
    def _snake_draft_balance(self, players: List[Dict], num_teams: int) -> List[List[Dict]]:
        """
        Snake draft algorithm with improved team size distribution:
        - Sort players by rating (highest to lowest)
        - Apply controlled randomization for variety
        - Calculate optimal team sizes for even distribution
        - Distribute using snake pattern within size constraints
        """
        # Log initial state
        initial_order = [f"{p['username']}({p['rating_mu']:.0f})" for p in players]
        logger.info(f"=== TEAM BALANCING DEBUG ===")
        logger.info(f"Initial player order: {initial_order}")
        
        # Sort players by effective rating (mu - sigma for conservative estimate)
        sorted_players = sorted(
            players,
            key=lambda p: p['rating_mu'] - (p['rating_sigma'] * 0.5),
            reverse=True
        )
        
        after_sort = [f"{p['username']}({p['rating_mu']:.0f})" for p in sorted_players]
        logger.info(f"After rating sort: {after_sort}")
        
        # Apply controlled randomization for variety while maintaining balance
        logger.info("Applying randomization...")
        sorted_players = self._shuffle_rating_bands(sorted_players)
        sorted_players = self._randomize_similar_ratings(sorted_players)
        
        final_draft_order = [f"{p['username']}({p['rating_mu']:.0f})" for p in sorted_players]
        logger.info(f"Final draft order: {final_draft_order}")
        
        # Fallback randomization if no shuffling occurred
        if final_draft_order == after_sort:
            logger.warning("No randomization occurred! Applying fallback shuffle...")
            # Create groups of 2-3 players and shuffle within each group
            fallback_players = []
            for i in range(0, len(sorted_players), 3):
                group = sorted_players[i:i+3]
                if len(group) > 1:
                    group_names = [p['username'] for p in group]
                    random.shuffle(group)
                    logger.info(f"Fallback shuffle group: {group_names} → {[p['username'] for p in group]}")
                fallback_players.extend(group)
            sorted_players = fallback_players
            
            final_after_fallback = [f"{p['username']}({p['rating_mu']:.0f})" for p in sorted_players]
            logger.info(f"Final order after fallback: {final_after_fallback}")
        
        # Calculate optimal team sizes for even distribution
        total_players = len(sorted_players)
        base_size = total_players // num_teams
        extra_players = total_players % num_teams
        
        # Create target sizes: some teams get base_size+1, others get base_size
        target_sizes = []
        for i in range(num_teams):
            if i < extra_players:
                target_sizes.append(base_size + 1)
            else:
                target_sizes.append(base_size)
        
        # Initialize teams
        teams = [[] for _ in range(num_teams)]
        
        # Snake draft distribution with size constraints and random starting team
        team_index = self._get_random_starting_team(num_teams)
        direction = 1  # 1 for forward, -1 for backward
        
        logger.debug(f"Starting snake draft with team {team_index + 1} (randomized)")
        
        for player in sorted_players:
            # Find next available team in snake order
            attempts = 0
            while len(teams[team_index]) >= target_sizes[team_index] and attempts < num_teams:
                # Move to next team in snake pattern
                team_index += direction
                
                # Reverse direction when reaching ends
                if team_index >= num_teams:
                    team_index = num_teams - 1
                    direction = -1
                elif team_index < 0:
                    team_index = 0
                    direction = 1
                
                attempts += 1
            
            # Add player to current team
            teams[team_index].append(player)
            
            # Move to next team for next iteration
            team_index += direction
            
            # Reverse direction when reaching ends
            if team_index >= num_teams:
                team_index = num_teams - 1
                direction = -1
            elif team_index < 0:
                team_index = 0
                direction = 1
        
        # Log team composition with sizes
        for i, team in enumerate(teams):
            team_names = [p['username'] for p in team]
            team_ratings = [p['rating_mu'] for p in team]
            avg_rating = sum(team_ratings) / len(team_ratings) if team_ratings else 0
            logger.info(f"Team {i+1} ({len(team)} players): {team_names} (avg: {avg_rating:.1f})")
        
        # Log distribution summary
        team_sizes = [len(team) for team in teams]
        logger.info(f"Team size distribution: {team_sizes} (total: {sum(team_sizes)} players)")
        
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
    
    def _create_balanced_teams_with_region(self, players: List[Dict], num_teams: int, required_region: str = None) -> List[List[Dict]]:
        """
        Create balanced teams with optional region requirement
        If region is specified, ensures each team has at least one player from that region
        """
        if not required_region:
            # Use standard snake draft if no region requirement
            return self._snake_draft_balance(players, num_teams)
        
        # Separate players by region
        region_players = [p for p in players if p.get('region_code') == required_region]
        non_region_players = [p for p in players if p.get('region_code') != required_region]
        
        # Sort both groups by rating
        region_players.sort(key=lambda p: p['rating_mu'] - (p['rating_sigma'] * 0.5), reverse=True)
        non_region_players.sort(key=lambda p: p['rating_mu'] - (p['rating_sigma'] * 0.5), reverse=True)
        
        # Initialize teams
        teams = [[] for _ in range(num_teams)]
        
        # First, distribute regional players (one per team)
        for i in range(min(len(region_players), num_teams)):
            teams[i].append(region_players[i])
        
        # Add remaining regional players using snake draft
        remaining_region_players = region_players[num_teams:]
        if remaining_region_players:
            self._distribute_players_snake_draft(remaining_region_players, teams)
        
        # Distribute non-regional players using snake draft
        if non_region_players:
            self._distribute_players_snake_draft(non_region_players, teams)
        
        return teams
    
    def _distribute_players_snake_draft(self, players: List[Dict], teams: List[List[Dict]]):
        """
        Distribute players to existing teams using snake draft pattern with size balancing
        Modifies teams in place
        """
        num_teams = len(teams)
        team_index = 0
        direction = 1  # 1 for forward, -1 for backward
        
        for player in players:
            # Find the team with the smallest size first (for better balance)
            current_sizes = [len(team) for team in teams]
            min_size = min(current_sizes)
            
            # If current team is already larger than minimum, find a smaller team
            if len(teams[team_index]) > min_size:
                # Find the first team with minimum size in snake order
                original_index = team_index
                attempts = 0
                
                while len(teams[team_index]) > min_size and attempts < num_teams:
                    team_index += direction
                    
                    # Reverse direction when reaching ends
                    if team_index >= num_teams:
                        team_index = num_teams - 1
                        direction = -1
                    elif team_index < 0:
                        team_index = 0
                        direction = 1
                    
                    attempts += 1
                
                # If we couldn't find a smaller team, use original index
                if attempts >= num_teams:
                    team_index = original_index
            
            teams[team_index].append(player)
            
            # Move to next team
            team_index += direction
            
            # Reverse direction when reaching ends
            if team_index >= num_teams:
                team_index = num_teams - 2 if num_teams > 1 else 0
                direction = -1
            elif team_index < 0:
                team_index = 1 if num_teams > 1 else 0
                direction = 1