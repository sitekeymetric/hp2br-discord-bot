import discord
from datetime import datetime
from typing import List, Dict, Optional, Any
from utils.constants import Config, TEAM_EMOJIS

class EmbedTemplates:
    """Discord embed templates for consistent UI"""
    
    @staticmethod
    def user_stats_embed(user_data: Dict[str, Any], teammate_stats: List[Dict] = None) -> discord.Embed:
        """Rich embed showing user statistics with optional teammate information"""
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
                # Handle both datetime objects and ISO strings
                if isinstance(created_at, str):
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                else:
                    # created_at is already a datetime object
                    created_date = created_at
                
                # Calculate days since creation (remove timezone info for comparison)
                if created_date.tzinfo is not None:
                    created_date = created_date.replace(tzinfo=None)
                
                days_since = (datetime.utcnow() - created_date).days
                
                if days_since == 0:
                    value = "Today"
                elif days_since == 1:
                    value = "1 day ago"
                else:
                    value = f"{days_since} days ago"
                
                embed.add_field(
                    name="📅 Member Since",
                    value=value,
                    inline=True
                )
            except Exception as e:
                # If there's still an error, show a debug-friendly message
                embed.add_field(
                    name="📅 Member Since",
                    value="Unknown",
                    inline=True
                )
        
        # Add teammate information if available
        if teammate_stats:
            # Most Frequent Partners
            frequent_partners = teammate_stats.get('frequent_partners', [])
            if frequent_partners:
                frequent_text = []
                for i, partner in enumerate(frequent_partners, 1):
                    name = partner['teammate_username']
                    games = partner['games_together']
                    avg_skill = partner['avg_skill_change']
                    
                    # Skill change emoji
                    if avg_skill >= 10:
                        skill_emoji = "🔥"
                    elif avg_skill >= 5:
                        skill_emoji = "✅"
                    elif avg_skill >= 0:
                        skill_emoji = "⚖️"
                    else:
                        skill_emoji = "⚠️"
                    
                    frequent_text.append(f"{i}. **{name}** - {games} games ({avg_skill:+.1f} avg skill)")
                
                embed.add_field(
                    name="🤝 Most Frequent Partners",
                    value="\n".join(frequent_text),
                    inline=False
                )
            
            # Championship Partners
            championship_partners = teammate_stats.get('championship_partners', [])
            if championship_partners:
                championship_text = []
                for i, partner in enumerate(championship_partners, 1):
                    name = partner['teammate_username']
                    first_wins = partner['first_place_wins']
                    win_rate = partner['win_rate']
                    
                    championship_text.append(f"{i}. **{name}** - {first_wins} wins ({win_rate:.0f}% win rate)")
                
                embed.add_field(
                    name="🏆 Championship Partners",
                    value="\n".join(championship_text),
                    inline=False
                )
        
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
        elif result_type == "forfeit":
            title = "⚠️ Match Forfeit"
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
    def match_history_embed(matches: List[Dict], username: str = None, current_rank: int = 0, current_rating: float = 0) -> discord.Embed:
        """Match history display with rank and enhanced skill change information"""
        title = f"📋 Match History"
        if username:
            title += f" - {username}"
        
        embed = discord.Embed(
            title=title,
            color=Config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        
        # Add current rank and rating info
        if current_rank > 0:
            rank_emoji = "🥇" if current_rank == 1 else "🥈" if current_rank == 2 else "🥉" if current_rank == 3 else f"#{current_rank}"
            embed.add_field(
                name="📊 Current Status",
                value=f"**Rank:** {rank_emoji} | **Rating:** {current_rating:.0f}",
                inline=False
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
            
            # Enhanced rating change information with result context
            rating_before = match.get("rating_mu_before", 0)
            rating_after = match.get("rating_mu_after", 0)
            result = match.get("result", "pending")
            
            if rating_after and rating_before:
                rating_change = rating_after - rating_before
                
                # Result-based emoji with rating change context
                if result == "win":
                    if rating_change >= 15:
                        result_emoji = "🟢"  # Great win
                    elif rating_change >= 5:
                        result_emoji = "🔵"  # Good win
                    else:
                        result_emoji = "🟡"  # Small win gain
                elif result == "loss":
                    if rating_change <= -15:
                        result_emoji = "🔴"  # Bad loss
                    elif rating_change <= -5:
                        result_emoji = "🟠"  # Moderate loss
                    else:
                        result_emoji = "🟡"  # Small loss
                elif result == "draw":
                    result_emoji = "⚪"  # Draw
                else:
                    result_emoji = "⚫"  # Unknown
                
                # Enhanced rating change display with skill context
                if rating_change > 0:
                    change_str = f" (**+{rating_change:.0f}**)"
                elif rating_change < 0:
                    change_str = f" (**{rating_change:.0f}**)"
                else:
                    change_str = " (**±0**)"
            else:
                # Fallback to old result-based emoji if no rating data
                if result == "win":
                    result_emoji = "🟢"
                elif result == "loss":
                    result_emoji = "🔴"
                elif result == "draw":
                    result_emoji = "⚪"
                else:
                    result_emoji = "⚫"
                change_str = ""
            
            # Teammate information
            teammates = match.get("teammates", [])
            if teammates:
                teammate_names = [t['username'] for t in teammates]
                if len(teammate_names) == 1:
                    teammate_str = f" + {teammate_names[0]}"
                elif len(teammate_names) == 2:
                    teammate_str = f" + {teammate_names[0]}, {teammate_names[1]}"
                elif len(teammate_names) == 3:
                    teammate_str = f" + {teammate_names[0]}, {teammate_names[1]}, {teammate_names[2]}"
                elif len(teammate_names) == 4:
                    teammate_str = f" + {teammate_names[0]}, {teammate_names[1]}, {teammate_names[2]}, {teammate_names[3]}"
                elif len(teammate_names) > 4:
                    # Show first 3 names and count of remaining
                    remaining = len(teammate_names) - 3
                    teammate_str = f" + {teammate_names[0]}, {teammate_names[1]}, {teammate_names[2]} +{remaining}"
                else:
                    teammate_str = ""
            else:
                teammate_str = " (solo)"
            
            history_text.append(f"{result_emoji} **Team {team_num}** - {date_str}{change_str}{teammate_str}")
        
        embed.description = "\n".join(history_text)
        
        # Add enhanced footer with explanation of color coding
        embed.set_footer(text="🟢 Great Win | 🔵 Good Win | 🟠 Moderate Loss | 🔴 Bad Loss | ⚪ Draw | 🟡 Small Change")
        
        return embed
    
    @staticmethod
    def teammate_stats_embed(teammate_stats: Dict, username: str = None) -> discord.Embed:
        """Teammate statistics display showing most frequent teammates and win rates"""
        title = f"🤝 Teammate Statistics"
        if username:
            title += f" - {username}"
        
        embed = discord.Embed(
            title=title,
            color=Config.EMBED_COLOR,
            timestamp=datetime.utcnow()
        )
        
        # Check if we have any data
        frequent_partners = teammate_stats.get('frequent_partners', [])
        championship_partners = teammate_stats.get('championship_partners', [])
        
        if not frequent_partners and not championship_partners:
            embed.description = "No teammate data found. Play some matches with other players to see statistics!"
            embed.add_field(
                name="ℹ️ Note",
                value="Teammate statistics are based on completed matches only.",
                inline=False
            )
            return embed
        
        # Most Frequent Partners
        if frequent_partners:
            frequent_text = []
            for i, partner in enumerate(frequent_partners, 1):
                name = partner['teammate_username']
                games = partner['games_together']
                avg_skill = partner['avg_skill_change']
                
                # Skill change emoji
                if avg_skill >= 10:
                    skill_emoji = "🔥"
                elif avg_skill >= 5:
                    skill_emoji = "✅"
                elif avg_skill >= 0:
                    skill_emoji = "⚖️"
                else:
                    skill_emoji = "⚠️"
                
                frequent_text.append(f"**{i}.** {name} {skill_emoji} - {games} games ({avg_skill:+.1f} avg skill)")
            
            embed.add_field(
                name="🤝 Most Frequent Partners",
                value="\n".join(frequent_text),
                inline=False
            )
        
        # Championship Partners
        if championship_partners:
            championship_text = []
            for i, partner in enumerate(championship_partners, 1):
                name = partner['teammate_username']
                first_wins = partner['first_place_wins']
                win_rate = partner['win_rate']
                
                championship_text.append(f"**{i}.** {name} - {first_wins} wins ({win_rate:.0f}% win rate)")
            
            embed.add_field(
                name="🏆 Championship Partners",
                value="\n".join(championship_text),
                inline=False
            )
        
        # Add summary statistics
        if frequent_partners:
            total_games = sum(p['games_together'] for p in frequent_partners)
            avg_skill_overall = sum(p['avg_skill_change'] * p['games_together'] for p in frequent_partners) / total_games if total_games > 0 else 0
            
            embed.add_field(
                name="📈 Summary",
                value=f"**{len(frequent_partners)}** frequent partners\n"
                      f"**{total_games}** total games together\n"
                      f"**{avg_skill_overall:+.1f}** overall avg skill with partners",
                inline=False
            )
        
        # Add footer with explanation
        embed.set_footer(text="🔥 +10 skill | ✅ +5 skill | ⚖️ 0+ skill | ⚠️ negative skill")
        
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