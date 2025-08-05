import math
from typing import List, Tuple
from dataclasses import dataclass

@dataclass
class Rating:
    mu: float      # Skill estimate
    sigma: float   # Uncertainty
    
class GlickoRatingService:
    # Glicko-2 Constants
    TAU = 0.5      # System volatility
    EPSILON = 0.000001  # Convergence tolerance
    
    @staticmethod
    def calculate_team_rating(player_ratings: List[Rating]) -> Rating:
        """Calculate team rating from individual players"""
        if not player_ratings:
            return Rating(1500.0, 350.0)
        
        # Team mu = average of player mus
        team_mu = sum(r.mu for r in player_ratings) / len(player_ratings)
        
        # Team sigma = combined uncertainty
        combined_variance = sum(r.sigma ** 2 for r in player_ratings)
        team_sigma = math.sqrt(combined_variance) / len(player_ratings)
        
        return Rating(team_mu, team_sigma)
    
    @staticmethod
    def update_ratings(player_ratings: List[Rating], team_results: List[float]) -> List[Rating]:
        """
        Update player ratings based on team performance
        team_results: 1.0 for win, 0.0 for loss, 0.5 for draw
        """
        # Simplified Glicko-2 implementation for MVP
        updated_ratings = []
        
        for rating, result in zip(player_ratings, team_results):
            # Basic rating change calculation
            rating_change = 32 * (result - 0.5) * (rating.sigma / 350.0)
            
            new_mu = rating.mu + rating_change
            new_sigma = max(rating.sigma * 0.99, 50.0)  # Gradual sigma reduction
            
            updated_ratings.append(Rating(new_mu, new_sigma))
        
        return updated_ratings
    
    @staticmethod
    def update_team_ratings(team1_ratings: List[Rating], team2_ratings: List[Rating], 
                           team1_score: float) -> Tuple[List[Rating], List[Rating]]:
        """
        Update ratings for two teams based on match result
        team1_score: 1.0 if team1 wins, 0.0 if team2 wins, 0.5 for draw
        """
        # Calculate team ratings
        team1_rating = GlickoRatingService.calculate_team_rating(team1_ratings)
        team2_rating = GlickoRatingService.calculate_team_rating(team2_ratings)
        
        # Expected score for team1
        rating_diff = team1_rating.mu - team2_rating.mu
        expected_score = 1 / (1 + math.pow(10, -rating_diff / 400))
        
        # Calculate K-factor based on uncertainty
        k_factor = 32 * (team1_rating.sigma / 350.0)
        
        # Rating change
        rating_change = k_factor * (team1_score - expected_score)
        
        # Update team 1 players
        team1_updated = []
        for rating in team1_ratings:
            new_mu = rating.mu + rating_change
            new_sigma = max(rating.sigma * 0.99, 50.0)
            team1_updated.append(Rating(new_mu, new_sigma))
        
        # Update team 2 players (opposite result)
        team2_updated = []
        for rating in team2_ratings:
            new_mu = rating.mu - rating_change
            new_sigma = max(rating.sigma * 0.99, 50.0)
            team2_updated.append(Rating(new_mu, new_sigma))
        
        return team1_updated, team2_updated
    
    @staticmethod
    def update_multi_team_ratings(teams_ratings: List[List[Rating]], team_positions: List[int]) -> List[List[Rating]]:
        """
        Update ratings for multiple teams based on their final positions
        team_positions: list of positions (1 for winner, 2 for second, etc.)
        """
        num_teams = len(teams_ratings)
        updated_teams = []
        
        for i, team_ratings in enumerate(teams_ratings):
            team_position = team_positions[i]
            
            # Calculate score based on position (1st place gets 1.0, last place gets 0.0)
            score = (num_teams - team_position) / (num_teams - 1) if num_teams > 1 else 0.5
            
            # Simple rating update for multi-team scenario
            updated_players = []
            for rating in team_ratings:
                rating_change = 20 * (score - 0.5) * (rating.sigma / 350.0)
                new_mu = rating.mu + rating_change
                new_sigma = max(rating.sigma * 0.99, 50.0)
                updated_players.append(Rating(new_mu, new_sigma))
            
            updated_teams.append(updated_players)
        
        return updated_teams