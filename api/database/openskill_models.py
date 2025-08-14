"""
OpenSkill Database Models
SQLAlchemy models for OpenSkill parallel rating system
"""

from sqlalchemy import Column, BigInteger, String, Float, Integer, DateTime, ForeignKey, Text, ForeignKeyConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class OpenSkillRating(Base):
    """OpenSkill ratings for users - parallel to main rating system"""
    __tablename__ = "openskill_ratings"
    
    # Primary Key
    guild_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, primary_key=True)
    
    # OpenSkill Rating Values
    mu = Column(Float, default=25.0, nullable=False)        # Skill estimate
    sigma = Column(Float, default=8.333, nullable=False)    # Uncertainty
    
    # Statistics
    games_played = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    @property
    def ordinal(self) -> float:
        """Conservative skill estimate (mu - 3*sigma)"""
        return self.mu - (3 * self.sigma)
    
    @property
    def display_rating(self) -> float:
        """Display rating scaled to familiar range (similar to 1500 baseline)"""
        # Scale OpenSkill (25±8.33) to familiar range (1500±500)
        return (self.mu * 60)  # 25*60 = 1500 baseline
    
    def __repr__(self):
        return f"<OpenSkillRating(guild={self.guild_id}, user={self.user_id}, mu={self.mu:.1f}, sigma={self.sigma:.1f})>"

class OpenSkillMatchHistory(Base):
    """OpenSkill match history - parallel to main match system"""
    __tablename__ = "openskill_match_history"
    
    # Primary Key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Match Reference
    match_id = Column(String(36), nullable=False)  # UUID as string
    guild_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    
    # Team Information
    team_number = Column(Integer, nullable=False)
    team_placement = Column(Integer, nullable=False)
    
    # Competition Context
    total_competitors = Column(Integer, nullable=False)
    guild_teams_count = Column(Integer, nullable=False)
    external_teams_count = Column(Integer, nullable=False)
    competition_type = Column(String(20), nullable=False)  # 'guild_only', 'mixed', 'external'
    
    # Rating Changes
    mu_before = Column(Float, nullable=False)
    sigma_before = Column(Float, nullable=False)
    mu_after = Column(Float, nullable=False)
    sigma_after = Column(Float, nullable=False)
    rating_change = Column(Float, nullable=False)  # Display rating change
    
    # Display Ratings (for easier querying)
    display_rating_before = Column(Float, nullable=False)
    display_rating_after = Column(Float, nullable=False)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    @property
    def rating_change_display(self) -> str:
        """Formatted rating change for display"""
        change = self.rating_change
        if change > 0:
            return f"+{change:.1f}"
        else:
            return f"{change:.1f}"
    
    def __repr__(self):
        return f"<OpenSkillMatchHistory(match={self.match_id}, user={self.user_id}, team={self.team_number}, placement={self.team_placement})>"
