"""
Advanced Skill-Based Rating System v3.0.0
Implements opponent strength consideration, curved scaling, and enhanced penalty tiers
"""

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from database.models import User, Match, MatchPlayer, PlayerResult


@dataclass
class TeamData:
    """Team data for rating calculations"""
    team_number: int
    placement: int
    avg_rating: float
    players: List[Dict]


@dataclass
class RatingChangeBreakdown:
    """Detailed breakdown of rating change calculation"""
    base_score: float
    opponent_multiplier: float
    individual_adjustment: float
    curve_multiplier: float
    preliminary_change: float
    final_change: float
    max_change_limit: float


class AdvancedRatingService:
    """Advanced rating service with opponent strength and curved scaling"""
    
    # Placement score tiers with enhanced penalties
    PLACEMENT_SCORES = {
        # Winning tiers (diminishing returns)
        1: 50,    # 1st place
        2: 35,    # 2nd place  
        3: 25,    # 3rd place
        4: 18,    # 4th place
        5: 12,    # 5th place
        
        # Neutral zone
        6: 8,     # 6th place
        7: 4,     # 7th place
        8: 0,     # 8th place (true neutral)
        
        # Penalty tiers (escalating drops)
        9: -5,    # 9th place
        10: -10,  # 10th place
        11: -16,  # 11th place
        12: -23,  # 12th place
        13: -31,  # 13th place
        14: -40,  # 14th place
        15: -50,  # 15th place
        
        # Severe penalty zone
        16: -62,  # 16th place
        17: -75,  # 17th place
        18: -89,  # 18th place
        19: -104, # 19th place
        20: -120, # 20th place
        
        # Bottom tier (harsh penalties)
        21: -138, # 21st place
        22: -157, # 22nd place
        23: -177, # 23rd place
        24: -198, # 24th place
        25: -220, # 25th place
        26: -243, # 26th place
        27: -267, # 27th place
        28: -292, # 28th place
        29: -318, # 29th place
        30: -345  # 30th place (maximum penalty)
    }
    
    @classmethod
    def calculate_base_placement_score(cls, placement: int) -> float:
        """Get base score for placement with interpolation for missing ranks"""
        if placement in cls.PLACEMENT_SCORES:
            return cls.PLACEMENT_SCORES[placement]
        
        # Interpolate for ranks not explicitly defined
        return cls._interpolate_placement_score(placement)
    
    @classmethod
    def _interpolate_placement_score(cls, placement: int) -> float:
        """Interpolate placement score for ranks not in the table"""
        if placement < 1:
            return cls.PLACEMENT_SCORES[1]
        if placement > 30:
            return cls.PLACEMENT_SCORES[30]
        
        # Find surrounding values for interpolation
        lower_rank = max([rank for rank in cls.PLACEMENT_SCORES.keys() if rank < placement], default=1)
        upper_rank = min([rank for rank in cls.PLACEMENT_SCORES.keys() if rank > placement], default=30)
        
        if lower_rank == upper_rank:
            return cls.PLACEMENT_SCORES[lower_rank]
        
        # Linear interpolation
        lower_score = cls.PLACEMENT_SCORES[lower_rank]
        upper_score = cls.PLACEMENT_SCORES[upper_rank]
        
        ratio = (placement - lower_rank) / (upper_rank - lower_rank)
        return lower_score + (upper_score - lower_score) * ratio
    
    @classmethod
    def calculate_opponent_strength_multiplier(cls, team_avg_rating: float, 
                                             opponent_teams: List[TeamData], 
                                             placement: int) -> float:
        """Calculate multiplier based on opponent strength"""
        if not opponent_teams:
            return 1.0
        
        # Calculate average opponent strength
        opponent_ratings = [team.avg_rating for team in opponent_teams]
        avg_opponent_rating = sum(opponent_ratings) / len(opponent_ratings)
        
        # Strength difference (positive = facing stronger opponents)
        strength_diff = avg_opponent_rating - team_avg_rating
        
        # Base multiplier from strength difference
        if strength_diff > 500:      # Much stronger opponents
            base_multiplier = 2.2
        elif strength_diff > 300:    # Very strong opponents
            base_multiplier = 1.8
        elif strength_diff > 150:    # Strong opponents
            base_multiplier = 1.4
        elif strength_diff > 50:     # Slightly stronger
            base_multiplier = 1.2
        elif strength_diff > -50:    # Similar strength
            base_multiplier = 1.0
        elif strength_diff > -150:   # Slightly weaker
            base_multiplier = 0.8
        elif strength_diff > -300:   # Weaker opponents
            base_multiplier = 0.6
        elif strength_diff > -500:   # Much weaker opponents
            base_multiplier = 0.4
        else:                        # Extremely weak opponents
            base_multiplier = 0.2
        
        # Additional placement-based adjustment
        if placement <= 3 and strength_diff < -200:  # Won against much weaker
            base_multiplier *= 0.7  # Further reduce rewards
        elif placement >= 15 and strength_diff > 200:  # Lost badly to stronger
            base_multiplier *= 1.3  # Increase penalty protection
            
        return base_multiplier
    
    @classmethod
    def calculate_individual_adjustment(cls, player_rating: float, team_avg_rating: float) -> float:
        """Adjust based on individual player vs team average"""
        individual_diff = player_rating - team_avg_rating
        
        if individual_diff > 200:      # Much stronger than team
            return 0.8  # Reduced impact (carrying team)
        elif individual_diff > 100:    # Stronger than team
            return 0.9
        elif individual_diff > -100:   # Similar to team
            return 1.0
        elif individual_diff > -200:   # Weaker than team  
            return 1.1  # Slightly increased impact (being carried)
        else:                          # Much weaker than team
            return 1.2  # Higher impact (significant skill gap)
    
    @classmethod
    def calculate_rating_curve_multiplier(cls, current_rating: float, rating_change: float) -> float:
        """Apply diminishing returns for climbing and faster drops for elite players"""
        if rating_change > 0:  # Positive changes (climbing)
            if current_rating >= 2000:      # Elite tier
                return 0.3  # Very slow climbing
            elif current_rating >= 1800:    # Expert tier  
                return 0.5  # Slow climbing
            elif current_rating >= 1600:    # Advanced tier
                return 0.7  # Moderate climbing
            elif current_rating >= 1400:    # Intermediate tier
                return 0.85 # Slightly reduced climbing
            else:                           # Below average
                return 1.0  # Normal climbing
                
        else:  # Negative changes (dropping)
            if current_rating >= 2000:      # Elite tier
                return 1.5  # Faster drops from elite
            elif current_rating >= 1800:    # Expert tier
                return 1.3  # Faster drops from expert
            elif current_rating >= 1600:    # Advanced tier  
                return 1.1  # Slightly faster drops
            else:                           # Lower tiers
                return 1.0  # Normal drop rate
    
    @classmethod
    def calculate_advanced_rating_change(cls, player_rating: float, team_avg_rating: float, 
                                       placement: int, opponent_teams: List[TeamData]) -> RatingChangeBreakdown:
        """Calculate complete rating change with detailed breakdown"""
        
        # Step 1: Base placement score
        base_score = cls.calculate_base_placement_score(placement)
        
        # Step 2: Opponent strength multiplier
        opponent_multiplier = cls.calculate_opponent_strength_multiplier(
            team_avg_rating, opponent_teams, placement
        )
        
        # Step 3: Individual skill adjustment
        individual_adjustment = cls.calculate_individual_adjustment(
            player_rating, team_avg_rating
        )
        
        # Step 4: Calculate preliminary change
        preliminary_change = base_score * opponent_multiplier * individual_adjustment
        
        # Step 5: Apply rating curve
        curve_multiplier = cls.calculate_rating_curve_multiplier(
            player_rating, preliminary_change
        )
        
        # Step 6: Final rating change
        final_change = preliminary_change * curve_multiplier
        
        # Step 7: Apply maximum change limits
        max_change = min(150, player_rating * 0.15)  # Max 15% or 150 points
        final_change = max(-max_change, min(max_change, final_change))
        
        return RatingChangeBreakdown(
            base_score=base_score,
            opponent_multiplier=opponent_multiplier,
            individual_adjustment=individual_adjustment,
            curve_multiplier=curve_multiplier,
            preliminary_change=preliminary_change,
            final_change=final_change,
            max_change_limit=max_change
        )
    
    @classmethod
    def get_rating_tier_name(cls, rating: float) -> str:
        """Get tier name for a rating"""
        if rating >= 2200:
            return "Legendary"
        elif rating >= 2000:
            return "Elite"
        elif rating >= 1800:
            return "Expert"
        elif rating >= 1600:
            return "Advanced"
        elif rating >= 1400:
            return "Intermediate"
        elif rating >= 1200:
            return "Beginner"
        elif rating >= 1000:
            return "Novice"
        else:
            return "Learning"
    
    @classmethod
    def get_expected_team_rating_for_rank(cls, rank: int) -> float:
        """Convert placement rank to expected team rating"""
        if rank <= 1:
            return 2200
        elif rank <= 5:
            # Linear interpolation from 2200 to 1500
            return 2200 - (rank - 1) * (700 / 4)  # 175 points per rank
        elif rank <= 15:
            # Linear interpolation from 1500 to 1000  
            return 1500 - (rank - 5) * (500 / 10)  # 50 points per rank
        elif rank <= 30:
            # Linear interpolation from 1000 to 800
            return 1000 - (rank - 15) * (200 / 15)  # 13.33 points per rank
        else:
            return 800  # Minimum rating
    
    @classmethod
    def preview_rating_changes(cls, player_rating: float, team_avg_rating: float, 
                             opponent_teams: List[TeamData]) -> Dict[int, float]:
        """Preview rating changes for different placements"""
        previews = {}
        
        for placement in [1, 3, 5, 10, 15, 20, 25, 30]:
            breakdown = cls.calculate_advanced_rating_change(
                player_rating, team_avg_rating, placement, opponent_teams
            )
            previews[placement] = breakdown.final_change
        
        return previews
    
    @classmethod
    def calculate_team_average_rating(cls, db: Session, guild_id: int, user_ids: List[int]) -> float:
        """Calculate average rating for a team"""
        users = db.query(User).filter(
            User.guild_id == guild_id,
            User.user_id.in_(user_ids)
        ).all()
        
        if not users:
            return 1500.0  # Default rating
        
        total_rating = sum(user.rating_mu for user in users)
        return total_rating / len(users)
    
    @classmethod
    def apply_advanced_rating_changes(cls, db: Session, match_id: str, 
                                    team_placements: Dict[int, Dict]) -> Dict[str, RatingChangeBreakdown]:
        """Apply advanced rating changes to all players in a match"""
        
        # Get match and players
        match = db.query(Match).filter(Match.match_id == match_id).first()
        if not match:
            raise ValueError(f"Match {match_id} not found")
        
        match_players = db.query(MatchPlayer).filter(MatchPlayer.match_id == match_id).all()
        if not match_players:
            raise ValueError(f"No players found for match {match_id}")
        
        # Organize players by team
        teams_data = {}
        for team_num, team_info in team_placements.items():
            team_players = [mp for mp in match_players if mp.team_number == team_num]
            if team_players:
                avg_rating = sum(mp.rating_mu_before for mp in team_players) / len(team_players)
                teams_data[team_num] = TeamData(
                    team_number=team_num,
                    placement=team_info['placement'],
                    avg_rating=avg_rating,
                    players=[{
                        'user_id': mp.user_id,
                        'rating_before': mp.rating_mu_before,
                        'sigma_before': mp.rating_sigma_before
                    } for mp in team_players]
                )
        
        # Calculate rating changes for each player
        rating_changes = {}
        
        for team_num, team_data in teams_data.items():
            # Get opponent teams
            opponent_teams = [t for t in teams_data.values() if t.team_number != team_num]
            
            # Calculate changes for each player in this team
            team_players = [mp for mp in match_players if mp.team_number == team_num]
            
            for match_player in team_players:
                breakdown = cls.calculate_advanced_rating_change(
                    player_rating=match_player.rating_mu_before,
                    team_avg_rating=team_data.avg_rating,
                    placement=team_data.placement,
                    opponent_teams=opponent_teams
                )
                
                # Apply rating change
                new_rating = match_player.rating_mu_before + breakdown.final_change
                new_sigma = max(match_player.rating_sigma_before * 0.99, 50.0)  # Gradual sigma reduction
                
                # Update match player record
                match_player.rating_mu_after = new_rating
                match_player.rating_sigma_after = new_sigma
                match_player.result = PlayerResult.WIN if team_data.placement == 1 else PlayerResult.LOSS
                
                # Store breakdown for response
                rating_changes[f"{match_player.user_id}"] = breakdown
                
                # Update user's main rating
                user = db.query(User).filter(
                    User.guild_id == match_player.guild_id,
                    User.user_id == match_player.user_id
                ).first()
                
                if user:
                    user.rating_mu = new_rating
                    user.rating_sigma = new_sigma
                    
                    # Update statistics
                    if team_data.placement == 1:
                        user.wins += 1
                    else:
                        user.losses += 1
                    
                    user.games_played += 1
        
        # Update match status
        match.status = "completed"
        match.result_type = "placement"
        
        db.commit()
        return rating_changes
