"""
OpenSkill Rating Service
Parallel rating system using OpenSkill library for team-based matches
Handles multi-team competitions including external opponents
"""

from typing import List, Dict, Tuple, Optional
from openskill.models import PlackettLuce, PlackettLuceRating
from dataclasses import dataclass
import logging
import math

logger = logging.getLogger(__name__)

@dataclass
class OpenSkillRating:
    """OpenSkill rating representation"""
    mu: float
    sigma: float
    
    def __post_init__(self):
        """Ensure valid rating values"""
        self.mu = max(0.0, self.mu)
        self.sigma = max(0.1, self.sigma)
    
    @property
    def ordinal(self) -> float:
        """Conservative skill estimate (mu - 3*sigma)"""
        return self.mu - (3 * self.sigma)
    
    @property
    def display_rating(self) -> float:
        """Display rating scaled to familiar range (similar to 1500 baseline)"""
        # Scale OpenSkill (25±8.33) to familiar range (1500±500)
        return (self.mu * 60)  # 25*60 = 1500 baseline

class OpenSkillService:
    """Service for calculating OpenSkill ratings for multi-team competitions"""
    
    # OpenSkill default parameters
    DEFAULT_MU = 25.0
    DEFAULT_SIGMA = 8.333
    
    def __init__(self):
        """Initialize OpenSkill model"""
        # Use PlackettLuce model which is good for multi-team competitions
        self.model = PlackettLuce(mu=self.DEFAULT_MU, sigma=self.DEFAULT_SIGMA)
    
    def create_rating(self, mu: float = None, sigma: float = None) -> OpenSkillRating:
        """Create a new OpenSkill rating"""
        if mu is None:
            mu = self.DEFAULT_MU
        if sigma is None:
            sigma = self.DEFAULT_SIGMA
        
        return OpenSkillRating(mu=mu, sigma=sigma)
    
    def _to_openskill_rating(self, rating: OpenSkillRating) -> PlackettLuceRating:
        """Convert our rating to OpenSkill library rating"""
        return PlackettLuceRating(mu=rating.mu, sigma=rating.sigma)
    
    def _from_openskill_rating(self, rating: PlackettLuceRating) -> OpenSkillRating:
        """Convert OpenSkill library rating to our rating"""
        return OpenSkillRating(mu=rating.mu, sigma=rating.sigma)
    
    def detect_competition_type(self, team_placements: Dict[int, int]) -> Tuple[str, int, int, int]:
        """
        Detect competition type and calculate team counts
        
        Returns:
            (competition_type, total_competitors, guild_teams_count, external_teams_count)
        """
        guild_teams_count = len(team_placements)
        max_placement = max(team_placements.values())
        min_placement = min(team_placements.values())
        
        # Check if placements are consecutive starting from 1
        expected_placements = set(range(1, guild_teams_count + 1))
        actual_placements = set(team_placements.values())
        
        if actual_placements == expected_placements and min_placement == 1:
            # Guild-only match: consecutive placements 1, 2, 3, ...
            competition_type = "guild_only"
            total_competitors = guild_teams_count
            external_teams_count = 0
        else:
            # External competition: gaps in placements or doesn't start at 1
            competition_type = "external" if max_placement > guild_teams_count else "mixed"
            total_competitors = max_placement  # Assume placements go up to max
            external_teams_count = total_competitors - guild_teams_count
        
        return competition_type, total_competitors, guild_teams_count, external_teams_count
    
    def estimate_external_team_strength(self, 
                                      guild_teams: Dict[int, List[OpenSkillRating]], 
                                      team_placements: Dict[int, int]) -> OpenSkillRating:
        """
        Estimate the strength of external teams based on guild team performance
        """
        # Calculate average guild team strength
        guild_team_strengths = []
        for team_players in guild_teams.values():
            team_strength = sum(player.mu for player in team_players)
            guild_team_strengths.append(team_strength)
        
        if not guild_team_strengths:
            return self.create_rating()
        
        avg_guild_strength = sum(guild_team_strengths) / len(guild_team_strengths)
        avg_guild_uncertainty = 8.333  # Default uncertainty
        
        # Estimate external team strength based on guild performance
        # If guild teams placed poorly, external teams are likely stronger
        avg_guild_placement = sum(team_placements.values()) / len(team_placements)
        
        # Adjust external team strength based on guild placement performance
        if avg_guild_placement <= 3:
            # Guild did well, external teams slightly weaker
            external_mu = avg_guild_strength * 0.95
        elif avg_guild_placement <= 6:
            # Guild did average, external teams similar strength
            external_mu = avg_guild_strength
        else:
            # Guild did poorly, external teams likely stronger
            external_mu = avg_guild_strength * 1.1
        
        # Convert back to per-player rating (assuming 4 players per team)
        external_player_mu = external_mu / 4
        
        return OpenSkillRating(mu=external_player_mu, sigma=avg_guild_uncertainty)
    
    def calculate_guild_team_ratings(self, 
                                   guild_teams: Dict[int, List[OpenSkillRating]], 
                                   team_placements: Dict[int, int]) -> Dict[int, List[OpenSkillRating]]:
        """
        Calculate new OpenSkill ratings for guild teams in multi-team competition
        
        Args:
            guild_teams: {team_number: [player_ratings]} - Only guild teams
            team_placements: {team_number: final_placement} - Guild team results
        
        Returns:
            Updated ratings for guild players only
        """
        try:
            # Detect competition type and scale
            comp_type, total_competitors, guild_count, external_count = self.detect_competition_type(team_placements)
            
            logger.info(f"Processing {comp_type} competition: {guild_count} guild teams, {external_count} external teams")
            
            # Prepare all teams for OpenSkill calculation
            all_teams = []
            all_ranks = []
            guild_team_indices = {}  # Track which indices are guild teams
            
            # Add guild teams
            guild_index = 0
            for team_num in sorted(guild_teams.keys()):
                players = guild_teams[team_num]
                placement = team_placements[team_num]
                
                # Convert to OpenSkill Rating objects
                openskill_team = []
                for player_rating in players:
                    rating = self._to_openskill_rating(player_rating)
                    openskill_team.append(rating)
                
                all_teams.append(openskill_team)
                all_ranks.append(placement)
                guild_team_indices[len(all_teams) - 1] = team_num
                guild_index += 1
            
            # Add estimated external teams if needed
            if external_count > 0:
                external_team_strength = self.estimate_external_team_strength(guild_teams, team_placements)
                
                for placement in range(1, total_competitors + 1):
                    if placement not in team_placements.values():
                        # This placement belongs to an external team
                        external_team = []
                        for _ in range(4):  # Assume 4 players per external team
                            rating = self._to_openskill_rating(external_team_strength)
                            external_team.append(rating)
                        
                        all_teams.append(external_team)
                        all_ranks.append(placement)
            
            # Calculate new ratings using OpenSkill
            updated_teams = self.model.rate(all_teams, ranks=all_ranks)
            
            # Extract only guild team updates
            updated_guild_teams = {}
            for team_index, guild_team_num in guild_team_indices.items():
                updated_team = []
                for player_rating in updated_teams[team_index]:
                    updated_rating = self._from_openskill_rating(player_rating)
                    updated_team.append(updated_rating)
                updated_guild_teams[guild_team_num] = updated_team
            
            return updated_guild_teams
            
        except Exception as e:
            logger.error(f"Error calculating OpenSkill ratings: {e}")
            # Return original ratings if calculation fails
            return guild_teams
    
    def calculate_match_ratings(self, 
                              players_by_team: Dict[int, List[Dict]], 
                              team_placements: Dict[int, int]) -> Dict[int, List[Dict]]:
        """
        Calculate new OpenSkill ratings for a match
        
        Args:
            players_by_team: {team_number: [player_data_with_ratings]}
            team_placements: {team_number: placement_rank}
        
        Returns:
            Updated player data with new OpenSkill ratings and competition info
        """
        try:
            # Convert player data to OpenSkill ratings
            guild_teams = {}
            for team_num, players in players_by_team.items():
                team_ratings = []
                for player in players:
                    rating = OpenSkillRating(
                        mu=player.get('openskill_mu_before', self.DEFAULT_MU),
                        sigma=player.get('openskill_sigma_before', self.DEFAULT_SIGMA)
                    )
                    team_ratings.append(rating)
                guild_teams[team_num] = team_ratings
            
            # Calculate new ratings
            updated_team_ratings = self.calculate_guild_team_ratings(guild_teams, team_placements)
            
            # Detect competition info
            comp_type, total_competitors, guild_count, external_count = self.detect_competition_type(team_placements)
            
            # Apply updates back to player data
            updated_players_by_team = {}
            
            for team_num, players in players_by_team.items():
                updated_players_by_team[team_num] = []
                
                for player_idx, player in enumerate(players):
                    updated_player = player.copy()
                    
                    # Add competition context
                    updated_player['competition_type'] = comp_type
                    updated_player['total_competitors'] = total_competitors
                    updated_player['guild_teams_count'] = guild_count
                    updated_player['external_teams_count'] = external_count
                    
                    if team_num in updated_team_ratings and player_idx < len(updated_team_ratings[team_num]):
                        new_rating = updated_team_ratings[team_num][player_idx]
                        old_rating = OpenSkillRating(
                            mu=updated_player.get('openskill_mu_before', self.DEFAULT_MU),
                            sigma=updated_player.get('openskill_sigma_before', self.DEFAULT_SIGMA)
                        )
                        
                        updated_player['openskill_mu_after'] = new_rating.mu
                        updated_player['openskill_sigma_after'] = new_rating.sigma
                        updated_player['display_rating_before'] = old_rating.display_rating
                        updated_player['display_rating_after'] = new_rating.display_rating
                        updated_player['rating_change'] = new_rating.display_rating - old_rating.display_rating
                    else:
                        # Fallback: no change
                        mu_before = updated_player.get('openskill_mu_before', self.DEFAULT_MU)
                        sigma_before = updated_player.get('openskill_sigma_before', self.DEFAULT_SIGMA)
                        updated_player['openskill_mu_after'] = mu_before
                        updated_player['openskill_sigma_after'] = sigma_before
                        updated_player['display_rating_before'] = mu_before * 60
                        updated_player['display_rating_after'] = mu_before * 60
                        updated_player['rating_change'] = 0.0
                    
                    updated_players_by_team[team_num].append(updated_player)
            
            return updated_players_by_team
            
        except Exception as e:
            logger.error(f"Error in calculate_match_ratings: {e}")
            # Return original data if calculation fails
            return players_by_team
    
    def get_rating_change(self, old_rating: OpenSkillRating, new_rating: OpenSkillRating) -> float:
        """Calculate the rating change in display points"""
        old_display = old_rating.display_rating
        new_display = new_rating.display_rating
        return new_display - old_display
    
    def compare_players(self, rating1: OpenSkillRating, rating2: OpenSkillRating) -> float:
        """
        Compare two players and return probability that player1 beats player2
        
        Returns:
            Float between 0 and 1 (0.5 = equal skill)
        """
        try:
            r1 = self._to_openskill_rating(rating1)
            r2 = self._to_openskill_rating(rating2)
            
            # Use model's predict_win function for 1v1 comparison (6.1.3 feature)
            teams = [[r1], [r2]]
            probabilities = self.model.predict_win(teams)
            return probabilities[0]
            
        except Exception as e:
            logger.error(f"Error comparing players: {e}")
            return 0.5  # Default to equal skill
    
    def predict_match_outcome(self, teams: List[List[OpenSkillRating]]) -> List[float]:
        """
        Predict win probabilities for each team in a match
        
        Args:
            teams: List of teams, each team is a list of player ratings
            
        Returns:
            List of win probabilities for each team
        """
        try:
            # Convert to OpenSkill ratings
            openskill_teams = []
            for team in teams:
                openskill_team = []
                for player_rating in team:
                    rating = self._to_openskill_rating(player_rating)
                    openskill_team.append(rating)
                openskill_teams.append(openskill_team)
            
            # Use predict_win to get probabilities
            probabilities = self.model.predict_win(openskill_teams)
            return probabilities
            
        except Exception as e:
            logger.error(f"Error predicting match outcome: {e}")
            # Return equal probabilities as fallback
            return [1.0 / len(teams)] * len(teams)
    
    def calculate_team_balance_score(self, teams: List[List[OpenSkillRating]]) -> float:
        """
        Calculate how balanced the teams are (lower = more balanced)
        
        Args:
            teams: List of teams, each team is a list of player ratings
            
        Returns:
            Balance score (0 = perfectly balanced)
        """
        try:
            # Get win probabilities
            probabilities = self.predict_match_outcome(teams)
            
            # Calculate variance in win probabilities
            # Perfectly balanced teams would have equal probabilities
            expected_prob = 1.0 / len(teams)
            variance = sum((p - expected_prob) ** 2 for p in probabilities)
            
            # Scale to a more intuitive range (0-100)
            balance_score = variance * 100 * len(teams)
            
            return balance_score
            
        except Exception as e:
            logger.error(f"Error calculating team balance: {e}")
            return 50.0  # Default moderate balance score
    
    def get_team_strength(self, team_ratings: List[OpenSkillRating]) -> OpenSkillRating:
        """
        Calculate combined team strength from individual player ratings
        
        Args:
            team_ratings: List of player ratings on the team
            
        Returns:
            Combined team rating
        """
        if not team_ratings:
            return self.create_rating()
        
        try:
            # Calculate team strength (sum of individual strengths)
            total_mu = sum(r.mu for r in team_ratings)
            total_sigma_squared = sum(r.sigma ** 2 for r in team_ratings)
            team_sigma = math.sqrt(total_sigma_squared)
            
            return OpenSkillRating(mu=total_mu, sigma=team_sigma)
            
        except Exception as e:
            logger.error(f"Error calculating team strength: {e}")
            return self.create_rating()

# Global service instance
openskill_service = OpenSkillService()
