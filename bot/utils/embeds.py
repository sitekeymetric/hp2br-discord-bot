import discord
from datetime import datetime
from typing import List, Dict, Optional, Any
from utils.constants import Config, TEAM_EMOJIS

class EmbedTemplates:
    """Discord embed templates for consistent UI"""
    
    @staticmethod
    def user_stats_embed(user_data: Dict[str, Any]) -> discord.Embed:
        """Rich embed showing user statistics"""
        username = user_data.get("username", "Unknown User")
        rating_mu = user_data.get("rating_mu", 1500.0)
        rating_sigma = user_data.get("rating_sigma", 350.0)
        games_played = user_data.get("games_played", 0)
        wins = user_data.get("wins", 0)
        losses = user_data.get("losses", 0)
        draws = user_data.get("draws", 0)
        region = user_data.get("region_code", "Not Set")
        created_at = user_data.get("created_at")
        
        # Calculate win rate
        win_rate = (wins / games_played * 100) if games_played > 0 else 0
        
        # Calculate confidence interval (rough estimate)
        confidence_lower = max(0, rating_mu - 2 * rating_sigma)
        confidence_upper = rating_mu + 2 * rating_sigma
        
        embed = discord.Embed(
            title=f"📊 Stats for {username}",
            color=Config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        
        # Rating information
        embed.add_field(
            name="🎯 Rating",
            value=f"**{rating_mu:.0f}** ± {rating_sigma:.0f}\n"
                  f"Range: {confidence_lower:.0f} - {confidence_upper:.0f}",
            inline=True
        )
        
        # Region
        embed.add_field(
            name="🌍 Region",
            value=region,
            inline=True
        )
        
        # Games played
        embed.add_field(
            name="🎮 Games",
            value=str(games_played),
            inline=True
        )
        
        # Win/Loss record
        embed.add_field(
            name="📈 Record",
            value=f"**W:** {wins} | **L:** {losses} | **D:** {draws}",
            inline=True
        )
        
        # Win rate
        embed.add_field(
            name="📊 Win Rate",
            value=f"{win_rate:.1f}%",
            inline=True
        )
        
        # Account age
        if created_at:
            try:
                created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                days_since = (datetime.utcnow() - created_date.replace(tzinfo=None)).days
                embed.add_field(
                    name="📅 Member Since",
                    value=f"{days_since} days ago",
                    inline=True
                )
            except:
                pass
        
        # Add footer with rating explanation
        embed.set_footer(text="Rating shows skill level ± uncertainty. Lower uncertainty = more accurate rating.")
        
        return embed
    
    @staticmethod
    def team_proposal_embed(teams: List[List[Dict]], team_ratings: List[float], balance_score: float = 0.0, region_requirement: str = None) -> discord.Embed:
        """Team proposal with ratings and balance info, optionally showing region requirement"""
        # Adjust title and description for single team
        if len(teams) == 1:
            title = "🎮 Single Team Setup"
            description = "All players will be on the same team:"
            if region_requirement:
                description += f"\n🌍 **Region Requirement:** {region_requirement}"
        else:
            title = "🎮 Team Proposal"
            description = "Here are the balanced teams:"
            if region_requirement:
                description += f"\n🌍 **Region Requirement:** Each team has at least one {region_requirement} player"
            
        embed = discord.Embed(
            title=title,
            description=description,
            color=Config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        
        for i, (team, avg_rating) in enumerate(zip(teams, team_ratings)):
            emoji = TEAM_EMOJIS[i] if i < len(TEAM_EMOJIS) else f"Team {i+1}"
            team_members = []
            
            for player in team:
                username = player.get("username", "Unknown")
                rating = player.get("rating_mu", 1500)
                player_line = f"• {username} ({rating:.0f})"
                
                # Add region indicator if requirement is set
                if region_requirement and player.get('region_code'):
                    region_indicator = " 🌍" if player.get('region_code') == region_requirement else ""
                    player_line += f" [{player['region_code']}]{region_indicator}"
                elif player.get('region_code'):
                    player_line += f" [{player['region_code']}]"
                
                team_members.append(player_line)
            
            # Adjust field name for single team
            if len(teams) == 1:
                field_name = f"{emoji} **Practice Team** (Avg: {avg_rating:.0f})"
            else:
                field_name = f"{emoji} **Team {i+1}** (Avg: {avg_rating:.0f})"
            
            embed.add_field(
                name=field_name,
                value="\n".join(team_members),
                inline=True
            )
        
        # Add balance information (skip for single team)
        if len(teams) > 1 and balance_score > 0:
            balance_text = "Excellent" if balance_score < 50 else "Good" if balance_score < 100 else "Fair"
            embed.add_field(
                name="⚖️ Balance",
                value=f"{balance_text} (Score: {balance_score:.1f})",
                inline=False
            )
        
        # Add region requirement explanation if set
        if region_requirement:
            embed.add_field(
                name="🌍 Region Info",
                value=f"Players marked with 🌍 are from region **{region_requirement}**.\nEach team is guaranteed to have at least one {region_requirement} player.",
                inline=False
            )
        
        # Adjust footer for different team configurations
        if len(teams) == 1:
            embed.set_footer(text="Click 'Create Team' to proceed.")
        else:
            embed.set_footer(text="Click 'Create Team' to proceed.")
        
        return embed
    
    @staticmethod
    def match_result_embed(match_data: Dict, rating_changes: Dict[int, Dict] = None) -> discord.Embed:
        """Match result with rating changes"""
        result_type = match_data.get("result_type", "unknown")
        winning_team = match_data.get("winning_team")
        
        if result_type == "win_loss" and winning_team:
            title = f"🏆 Team {winning_team} Wins!"
            color = Config.SUCCESS_COLOR
        elif result_type == "draw":
            title = "🤝 Match Draw"
            color = Config.WARNING_COLOR
        else:
            title = "❌ Match Cancelled"
            color = Config.ERROR_COLOR
        
        embed = discord.Embed(
            title=title,
            color=color,
            timestamp=datetime.utcnow()
        )
        
        if rating_changes:
            changes_text = []
            for user_id, changes in rating_changes.items():
                username = changes.get("username", f"User {user_id}")
                old_rating = changes.get("old_rating", 0)
                new_rating = changes.get("new_rating", 0)
                change = new_rating - old_rating
                
                if change > 0:
                    changes_text.append(f"📈 {username}: {old_rating:.0f} → {new_rating:.0f} (+{change:.0f})")
                elif change < 0:
                    changes_text.append(f"📉 {username}: {old_rating:.0f} → {new_rating:.0f} ({change:.0f})")
                else:
                    changes_text.append(f"➡️ {username}: {old_rating:.0f} (no change)")
            
            if changes_text:
                embed.add_field(
                    name="📊 Rating Changes",
                    value="\n".join(changes_text[:10]),  # Limit to 10 players
                    inline=False
                )
        
        embed.set_footer(text="Ratings updated successfully!")
        
        return embed
    
    @staticmethod
    def leaderboard_embed(users: List[Dict], guild_name: str, page: int = 1, total_pages: int = 1) -> discord.Embed:
        """Guild leaderboard display"""
        embed = discord.Embed(
            title=f"🏆 {guild_name} Leaderboard",
            color=Config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        
        if not users:
            embed.description = "No players found. Use `/register` to join!"
            return embed
        
        leaderboard_text = []
        start_rank = (page - 1) * 10 + 1
        
        for i, user in enumerate(users, start=start_rank):
            username = user.get("username", "Unknown")
            rating = user.get("rating_mu", 1500)
            games = user.get("games_played", 0)
            wins = user.get("wins", 0)
            win_rate = (wins / games * 100) if games > 0 else 0
            
            # Medal emojis for top 3
            if i == 1:
                rank_emoji = "🥇"
            elif i == 2:
                rank_emoji = "🥈"
            elif i == 3:
                rank_emoji = "🥉"
            else:
                rank_emoji = f"{i}."
            
            leaderboard_text.append(
                f"{rank_emoji} **{username}** - {rating:.0f} ({games} games, {win_rate:.1f}% WR)"
            )
        
        embed.description = "\n".join(leaderboard_text)
        
        if total_pages > 1:
            embed.set_footer(text=f"Page {page}/{total_pages}")
        
        return embed
    
    @staticmethod
    def match_history_embed(matches: List[Dict], username: str = None) -> discord.Embed:
        """Match history display with enhanced date formatting"""
        title = f"📋 Match History"
        if username:
            title += f" - {username}"
        
        embed = discord.Embed(
            title=title,
            color=Config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        
        if not matches:
            embed.description = "No completed match history found."
            embed.add_field(
                name="ℹ️ Note",
                value="Statistics are based on completed matches only.",
                inline=False
            )
            return embed
        
        history_text = []
        for match in matches[:10]:  # Show last 10 matches
            result = match.get("result", "pending")
            team_num = match.get("team_number", "?")
            
            # Use end_time (when match was completed) instead of created_at
            end_time = match.get("end_time")
            start_time = match.get("start_time")
            
            # Format date - prefer end_time, fallback to start_time
            date_str = "??/??"
            try:
                if end_time:
                    match_date = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    date_str = match_date.strftime("%m/%d/%y")
                elif start_time:
                    match_date = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    date_str = match_date.strftime("%m/%d/%y")
            except (ValueError, AttributeError):
                # Handle both string and datetime objects
                try:
                    if end_time:
                        if isinstance(end_time, str):
                            match_date = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                        else:
                            match_date = end_time
                        date_str = match_date.strftime("%m/%d/%y")
                    elif start_time:
                        if isinstance(start_time, str):
                            match_date = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                        else:
                            match_date = start_time
                        date_str = match_date.strftime("%m/%d/%y")
                except:
                    date_str = "??/??"
            
            # Result emoji
            if result == "win":
                result_emoji = "🟢"
            elif result == "loss":
                result_emoji = "🔴"
            elif result == "draw":
                result_emoji = "🟡"
            else:
                result_emoji = "⚪"
            
            # Rating change information
            rating_before = match.get("rating_mu_before", 0)
            rating_after = match.get("rating_mu_after", 0)
            
            if rating_after and rating_before:
                rating_change = rating_after - rating_before
                if rating_change > 0:
                    change_str = f" (+{rating_change:.0f})"
                elif rating_change < 0:
                    change_str = f" ({rating_change:.0f})"
                else:
                    change_str = " (±0)"
            else:
                change_str = ""
            
            history_text.append(f"{result_emoji} **Team {team_num}** - {date_str}{change_str}")
        
        embed.description = "\n".join(history_text)
        
        # Add footer with explanation
        embed.set_footer(text="🟢 Win | 🔴 Loss | 🟡 Draw | Numbers show rating change")
        
        return embed
    
    @staticmethod
    def teammate_stats_embed(teammate_stats: List[Dict], username: str = None) -> discord.Embed:
        """Teammate statistics display showing most frequent teammates and win rates"""
        title = f"🤝 Teammate Statistics"
        if username:
            title += f" - {username}"
        
        embed = discord.Embed(
            title=title,
            color=Config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        
        if not teammate_stats:
            embed.description = "No teammate data found. Play some matches with other players to see statistics!"
            embed.add_field(
                name="ℹ️ Note",
                value="Teammate statistics are based on completed matches only.",
                inline=False
            )
            return embed
        
        # Create teammate list
        teammate_text = []
        for i, teammate in enumerate(teammate_stats, 1):
            teammate_name = teammate['teammate_username']
            games_together = teammate['games_together']
            wins_together = teammate['wins_together']
            win_rate = teammate['win_rate']
            
            # Win rate emoji
            if win_rate >= 70:
                rate_emoji = "🔥"  # Hot streak
            elif win_rate >= 60:
                rate_emoji = "✅"  # Good
            elif win_rate >= 50:
                rate_emoji = "⚖️"  # Balanced
            elif win_rate >= 40:
                rate_emoji = "⚠️"  # Below average
            else:
                rate_emoji = "❌"  # Poor
            
            teammate_text.append(
                f"**{i}.** {teammate_name} {rate_emoji}\n"
                f"   📊 {games_together} games • {win_rate:.1f}% win rate • {wins_together} wins"
            )
        
        embed.description = "\n\n".join(teammate_text)
        
        # Add summary statistics
        if teammate_stats:
            total_games_with_teammates = sum(t['games_together'] for t in teammate_stats)
            total_wins_with_teammates = sum(t['wins_together'] for t in teammate_stats)
            overall_teammate_win_rate = (total_wins_with_teammates / total_games_with_teammates * 100) if total_games_with_teammates > 0 else 0
            
            embed.add_field(
                name="📈 Summary",
                value=f"**{len(teammate_stats)}** frequent teammates\n"
                      f"**{total_games_with_teammates}** total games together\n"
                      f"**{overall_teammate_win_rate:.1f}%** overall win rate with teammates",
                inline=False
            )
        
        # Add footer with explanation
        embed.set_footer(text="🔥 70%+ | ✅ 60%+ | ⚖️ 50%+ | ⚠️ 40%+ | ❌ <40% win rate")
        
        return embed
    
    @staticmethod
    def error_embed(title: str, description: str, ephemeral_hint: bool = True) -> discord.Embed:
        """Standardized error messages"""
        embed = discord.Embed(
            title=f"❌ {title}",
            description=description,
            color=Config.ERROR_COLOR
        )
        
        if ephemeral_hint:
            embed.set_footer(text="This message is only visible to you.")
        
        return embed
    
    @staticmethod
    def success_embed(title: str, description: str) -> discord.Embed:
        """Standardized success messages"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=Config.SUCCESS_COLOR
        )
        return embed
    
    @staticmethod
    def warning_embed(title: str, description: str) -> discord.Embed:
        """Standardized warning messages"""
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=description,
            color=Config.WARNING_COLOR
        )
        return embed