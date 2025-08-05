from sqlalchemy import Column, BigInteger, String, Float, Integer, DateTime, Enum, Boolean, ForeignKey, ForeignKeyConstraint, TypeDecorator, CHAR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
import enum
from datetime import datetime

# SQLite-compatible UUID type
class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses CHAR(32), storing as stringified hex values.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value).int
            else:
                # hexstring
                return "%.32x" % value.int

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value)
            else:
                return value

Base = declarative_base()

class MatchStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ResultType(enum.Enum):
    WIN_LOSS = "win_loss"
    DRAW = "draw"
    CANCELLED = "cancelled"

class PlayerResult(enum.Enum):
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    PENDING = "pending"

class User(Base):
    __tablename__ = "users"
    
    # Primary Key
    guild_id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, primary_key=True)
    
    # Profile Data
    username = Column(String(100), nullable=False)
    region_code = Column(String(10), nullable=True)  # NA, EU, AS, OCE, etc.
    
    # Rating System (Glicko-2)
    rating_mu = Column(Float, default=1500.0, nullable=False)
    rating_sigma = Column(Float, default=350.0, nullable=False)
    
    # Statistics
    games_played = Column(Integer, default=0, nullable=False)
    wins = Column(Integer, default=0, nullable=False)
    losses = Column(Integer, default=0, nullable=False)
    draws = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    match_participations = relationship("MatchPlayer", back_populates="user")

class Match(Base):
    __tablename__ = "matches"
    
    # Primary Key
    match_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Match Context
    guild_id = Column(BigInteger, nullable=False, index=True)
    created_by = Column(BigInteger, nullable=False)
    
    # Match Timing
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    
    # Match State
    status = Column(Enum(MatchStatus), default=MatchStatus.PENDING, nullable=False)
    result_type = Column(Enum(ResultType), nullable=True)
    winning_team = Column(Integer, nullable=True)
    total_teams = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    players = relationship("MatchPlayer", back_populates="match", cascade="all, delete-orphan")

class MatchPlayer(Base):
    __tablename__ = "match_players"
    
    # Composite Primary Key
    match_id = Column(GUID(), ForeignKey("matches.match_id"), primary_key=True)
    user_id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger, nullable=False)
    
    # Team Assignment
    team_number = Column(Integer, nullable=False)
    
    # Rating History
    rating_mu_before = Column(Float, nullable=False)
    rating_sigma_before = Column(Float, nullable=False)
    rating_mu_after = Column(Float, nullable=True)
    rating_sigma_after = Column(Float, nullable=True)
    
    # Match Result
    result = Column(Enum(PlayerResult), default=PlayerResult.PENDING, nullable=False)
    
    # Relationships
    match = relationship("Match", back_populates="players")
    user = relationship("User", back_populates="match_participations")
    
    # Foreign Key Constraint
    __table_args__ = (
        ForeignKeyConstraint(['guild_id', 'user_id'], ['users.guild_id', 'users.user_id']),
    )