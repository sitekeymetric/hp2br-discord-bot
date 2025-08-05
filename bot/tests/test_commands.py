import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from discord.ext import commands

# Mock Discord objects for testing
class MockInteraction:
    def __init__(self, guild_id=123456789, user_id=987654321, user_name="TestUser"):
        self.guild = MagicMock()
        self.guild.id = guild_id
        self.guild.name = "Test Guild"
        
        self.user = MagicMock()
        self.user.id = user_id
        self.user.display_name = user_name
        
        self.response = MagicMock()
        self.response.defer = AsyncMock()
        self.response.send_message = AsyncMock()
        
        self.followup = MagicMock()
        self.followup.send = AsyncMock()

class MockMember:
    def __init__(self, user_id=123, username="TestUser", bot=False):
        self.id = user_id
        self.display_name = username
        self.bot = bot
        self.voice = None

@pytest.fixture
def mock_bot():
    """Create a mock Discord bot"""
    bot = MagicMock()
    bot.user = MagicMock()
    bot.user.id = 987654321
    return bot

@pytest.fixture
def mock_api_client():
    """Create a mock API client"""
    with patch('commands.user_commands.api_client') as mock:
        yield mock

class TestUserCommands:
    """Test user management commands"""
    
    @pytest.mark.asyncio
    async def test_register_new_user(self, mock_bot, mock_api_client):
        """Test registering a new user"""
        from commands.user_commands import UserCommands
        
        # Setup mocks
        mock_api_client.get_user.return_value = None  # User doesn't exist
        mock_api_client.create_user.return_value = {
            'user_id': 987654321,
            'username': 'TestUser',
            'rating_mu': 1500.0,
            'rating_sigma': 350.0,
            'region_code': 'NA'
        }
        
        # Create command instance
        user_commands = UserCommands(mock_bot)
        
        # Create mock interaction
        interaction = MockInteraction()
        
        # Execute command
        await user_commands.register(interaction, region="NA")
        
        # Verify API calls
        mock_api_client.get_user.assert_called_once_with(123456789, 987654321)
        mock_api_client.create_user.assert_called_once_with(
            guild_id=123456789,
            user_id=987654321,
            username="TestUser",
            region="NA"
        )
        
        # Verify response
        interaction.response.defer.assert_called_once()
        interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_existing_user(self, mock_bot, mock_api_client):
        """Test registering an existing user"""
        from commands.user_commands import UserCommands
        
        # Setup mocks - user already exists
        mock_api_client.get_user.return_value = {
            'user_id': 987654321,
            'username': 'TestUser',
            'rating_mu': 1600.0,
            'rating_sigma': 300.0
        }
        
        user_commands = UserCommands(mock_bot)
        interaction = MockInteraction()
        
        await user_commands.register(interaction)
        
        # Should not create user
        mock_api_client.create_user.assert_not_called()
        
        # Should send warning
        interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stats_existing_user(self, mock_bot, mock_api_client):
        """Test getting stats for existing user"""
        from commands.user_commands import UserCommands
        
        # Setup mocks
        mock_api_client.get_user.return_value = {
            'user_id': 987654321,
            'username': 'TestUser',
            'rating_mu': 1600.0,
            'rating_sigma': 300.0,
            'games_played': 10,
            'wins': 6,
            'losses': 4,
            'draws': 0,
            'region_code': 'NA',
            'created_at': '2023-01-01T00:00:00Z'
        }
        
        user_commands = UserCommands(mock_bot)
        interaction = MockInteraction()
        
        await user_commands.stats(interaction)
        
        # Verify API call
        mock_api_client.get_user.assert_called_once_with(123456789, 987654321)
        
        # Verify response
        interaction.followup.send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_set_region_valid(self, mock_bot, mock_api_client):
        """Test setting a valid region"""
        from commands.user_commands import UserCommands
        
        # Setup mocks
        mock_api_client.get_user.return_value = {'user_id': 987654321}
        mock_api_client.update_user.return_value = {'region_code': 'EU'}
        
        user_commands = UserCommands(mock_bot)
        interaction = MockInteraction()
        
        await user_commands.set_region(interaction, region="EU")
        
        # Verify API calls
        mock_api_client.update_user.assert_called_once_with(
            guild_id=123456789,
            user_id=987654321,
            region_code="EU"
        )

class TestTeamBalancer:
    """Test team balancing functionality"""
    
    @pytest.mark.asyncio
    async def test_snake_draft_balance(self):
        """Test snake draft balancing algorithm"""
        from services.team_balancer import TeamBalancer
        
        # Create test players with different ratings
        players = [
            {'user_id': 1, 'username': 'Player1', 'rating_mu': 1800, 'rating_sigma': 200},
            {'user_id': 2, 'username': 'Player2', 'rating_mu': 1600, 'rating_sigma': 250},
            {'user_id': 3, 'username': 'Player3', 'rating_mu': 1500, 'rating_sigma': 300},
            {'user_id': 4, 'username': 'Player4', 'rating_mu': 1400, 'rating_sigma': 350},
            {'user_id': 5, 'username': 'Player5', 'rating_mu': 1300, 'rating_sigma': 300},
            {'user_id': 6, 'username': 'Player6', 'rating_mu': 1200, 'rating_sigma': 400},
        ]
        
        balancer = TeamBalancer()
        teams = balancer._snake_draft_balance(players, 3)
        
        # Should have 3 teams
        assert len(teams) == 3
        
        # Should have all players distributed
        total_players = sum(len(team) for team in teams)
        assert total_players == 6
        
        # Check that highest rated player is in first team
        team1_ratings = [p['rating_mu'] for p in teams[0]]
        assert 1800 in team1_ratings  # Highest rating should be in team 1
    
    def test_calculate_balance_score(self):
        """Test balance score calculation"""
        from services.team_balancer import TeamBalancer
        
        balancer = TeamBalancer()
        
        # Perfect balance
        perfect_ratings = [1500.0, 1500.0, 1500.0]
        perfect_score = balancer._calculate_balance_score(perfect_ratings)
        assert perfect_score == 0.0
        
        # Unbalanced teams
        unbalanced_ratings = [1800.0, 1500.0, 1200.0]
        unbalanced_score = balancer._calculate_balance_score(unbalanced_ratings)
        assert unbalanced_score > 0.0

class TestVoiceManager:
    """Test voice channel management"""
    
    @pytest.mark.asyncio
    async def test_get_waiting_room_members(self, mock_bot):
        """Test getting members from waiting room"""
        from services.voice_manager import VoiceManager
        
        # Create mock guild and voice channel
        mock_guild = MagicMock()
        
        # Mock waiting room with members
        waiting_room = MagicMock()
        waiting_room.name = "Waiting Room"
        waiting_room.members = [
            MockMember(1, "Player1"),
            MockMember(2, "Player2"),
            MockMember(999, "BotUser", bot=True),  # Should be filtered out
        ]
        
        mock_guild.voice_channels = [waiting_room]
        
        voice_manager = VoiceManager(mock_bot)
        members = await voice_manager.get_waiting_room_members(mock_guild)
        
        # Should return 2 human members (bot filtered out)
        assert len(members) == 2
        assert all(not member.bot for member in members)
    
    @pytest.mark.asyncio 
    async def test_validate_voice_setup(self, mock_bot):
        """Test voice setup validation"""
        from services.voice_manager import VoiceManager
        
        # Mock guild with proper setup
        mock_guild = MagicMock()
        
        # Mock waiting room
        waiting_room = MagicMock()
        waiting_room.name = "Waiting Room"
        
        # Mock bot permissions
        permissions = MagicMock()
        permissions.move_members = True
        permissions.manage_channels = True
        waiting_room.permissions_for.return_value = permissions
        
        mock_guild.voice_channels = [waiting_room]
        mock_guild.me = MagicMock()
        
        voice_manager = VoiceManager(mock_bot)
        
        with patch('discord.utils.get', return_value=waiting_room):
            is_valid, message = await voice_manager.validate_voice_setup(mock_guild)
        
        assert is_valid
        assert "valid" in message.lower()

class TestAPIClient:
    """Test API client functionality"""
    
    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test creating a user via API"""
        from services.api_client import APIClient
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            # Mock response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {
                'user_id': 123,
                'username': 'TestUser',
                'rating_mu': 1500.0
            }
            
            mock_session = AsyncMock()
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            api_client = APIClient()
            await api_client._ensure_session()
            
            result = await api_client.create_user(
                guild_id=123456789,
                user_id=123,
                username="TestUser",
                region="NA"
            )
            
            assert result is not None
            assert result['user_id'] == 123
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test API health check"""
        from services.api_client import APIClient
        
        with patch('aiohttp.ClientSession') as mock_session_class:
            # Mock healthy response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = {'status': 'healthy'}
            
            mock_session = AsyncMock()
            mock_session.request.return_value.__aenter__.return_value = mock_response
            mock_session_class.return_value = mock_session
            
            api_client = APIClient()
            await api_client._ensure_session()
            
            is_healthy = await api_client.health_check()
            assert is_healthy is True

if __name__ == '__main__':
    pytest.main([__file__])