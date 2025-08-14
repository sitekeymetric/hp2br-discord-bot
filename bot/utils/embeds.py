import discord
from datetime import datetime
from typing import List, Dict, Optional, Any
from utils.constants import Config, TEAM_EMOJIS
from utils.version import get_bot_footer_text

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
            color=Config.EMBED_COLOR
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
                    name="🤝 Most Frequent Teammates",
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
        
        # Add footer with version
        embed.set_footer(text=get_bot_footer_text())
        
        return embed
    
    @staticmethod
    def team_proposal_embed(teams: List[List[Dict]], team_ratings: List[float], balance_score: float = 0.0, region_requirement: str = None, rating_system: str = "traditional") -> discord.Embed:
        """Team proposal with ratings and balance info, optionally showing region requirement and rating system"""
        # Determine rating system display info
        rating_info = {
            "traditional": {"emoji": "🎯", "name": "Traditional (Placement-based)"},
            "openskill": {"emoji": "🧪", "name": "OpenSkill (Team-based) - Beta"}
        }
        
        rating_display = rating_info.get(rating_system, rating_info["traditional"])
        
        # Adjust title and description for single team
        if len(teams) == 1:
            title = "🎮 Single Team Setup"
            description = f"All players will be on the same team:\n{rating_display['emoji']} **Rating System:** {rating_display['name']}"
            if region_requirement:
                description += f"\n🌍 **Region Requirement:** {region_requirement}"
        else:
            title = "🎮 Team Proposal"
            description = f"Here are the balanced teams:\n{rating_display['emoji']} **Rating System:** {rating_display['name']}"
            if region_requirement:
                description += f"\n🌍 **Region Requirement:** Each team has at least one {region_requirement} player"
            
        embed = discord.Embed(
            title=title,
            description=description,
            color=Config.EMBED_COLOR
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
        
        # Add footer with version
        embed.set_footer(text=get_bot_footer_text())
        
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
            color=color
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
        
        embed.set_footer(text=get_bot_footer_text())
        
        return embed
    
    @staticmethod
    def leaderboard_embed(users: List[Dict], guild_name: str, page: int = 1, total_pages: int = 1) -> discord.Embed:
        """Guild leaderboard display"""
        embed = discord.Embed(
            title=f"🏆 {guild_name} Leaderboard",
            color=Config.EMBED_COLOR
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
            embed.set_footer(text=f"Page {page}/{total_pages} • {get_bot_footer_text()}")
        else:
            embed.set_footer(text=get_bot_footer_text())
        
        return embed
    
    @staticmethod
    def openskill_leaderboard_embed(users: List[Dict], guild_name: str, page: int = 1, total_pages: int = 1) -> discord.Embed:
        """OpenSkill leaderboard display"""
        embed = discord.Embed(
            title=f"🧪 {guild_name} OpenSkill Leaderboard (Beta)",
            description="Team-based skill assessment rankings",
            color=Config.EMBED_COLOR
        )
        
        if not users:
            embed.description = "No OpenSkill data found. Complete some matches to generate ratings!"
            return embed
        
        leaderboard_text = []
        start_rank = (page - 1) * 10 + 1
        
        for i, user in enumerate(users, start=start_rank):
            username = user.get("username", "Unknown")
            display_rating = user.get("rating_mu", 1500)  # Using rating_mu as display_rating
            sigma = user.get("rating_sigma", 8.333)
            games = user.get("games_played", 0)
            
            # Convert display rating back to mu for proper display
            mu = display_rating / 60 if display_rating > 100 else display_rating
            
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
                f"{rank_emoji} **{username}** - {display_rating:.0f} ({mu:.1f}μ ± {sigma:.1f}σ, {games} games)"
            )
        
        embed.description = "\n".join(leaderboard_text)
        
        # Add explanation
        embed.add_field(
            name="🧪 About OpenSkill (Beta)",
            value="Team-based skill assessment that considers team composition and synergy.\n"
                  "Higher μ (mu) = higher skill, lower σ (sigma) = more confident rating.",
            inline=False
        )
        
        if total_pages > 1:
            embed.set_footer(text=f"Page {page}/{total_pages} • {get_bot_footer_text()}")
        else:
            embed.set_footer(text=get_bot_footer_text())
        
        return embed
    
    @staticmethod
    def match_history_embed(matches: List[Dict], username: str = None, current_rank: int = 0, current_rating: float = 0) -> discord.Embed:
        """Match history display with rank and enhanced skill change information"""
        title = f"📋 Match History"
        if username:
            title += f" - {username}"
        
        embed = discord.Embed(
            title=title,
            color=Config.EMBED_COLOR
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
            team_num = match.get("team_number", 1)  # Default to team 1 instead of "?"
            team_placement = match.get("team_placement")
            total_teams = match.get("total_teams", 2)
            result_type = match.get("result_type")
            
            # Use end_time (when match was completed) instead of created_at
            end_time = match.get("end_time")
            start_time = match.get("start_time")
            
            # Format date - prefer end_time, fallback to start_time
            date_str = "??/??"
            try:
                if end_time:
                    if isinstance(end_time, str):
                        # Handle ISO format string
                        match_date = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                    else:
                        match_date = end_time
                    date_str = match_date.strftime("%m/%d/%y")
                elif start_time:
                    if isinstance(start_time, str):
                        # Handle ISO format string  
                        match_date = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    else:
                        match_date = start_time
                    date_str = match_date.strftime("%m/%d/%y")
            except (ValueError, AttributeError, TypeError):
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
            
            # Enhanced team display with placement information
            team_display = f"Team {team_num}"
            
            # Add placement info for placement-based results
            if team_placement and result_type == "placement":
                if team_placement == 1:
                    team_display += " 🥇"
                elif team_placement == 2:
                    team_display += " 🥈"
                elif team_placement == 3:
                    team_display += " 🥉"
                else:
                    team_display += f" (#{team_placement})"
                    
                # Show placement context for external competitions
                if total_teams > 6:
                    team_display += f"/{total_teams}"
            
            # Teammate information with better formatting
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
                    # Show first 2 names and count of remaining for long teams
                    remaining = len(teammate_names) - 2
                    teammate_str = f" + {teammate_names[0]}, {teammate_names[1]} (+{remaining})"
                else:
                    teammate_str = ""
            else:
                teammate_str = " (solo)"
            
            history_text.append(f"{result_emoji} **{team_display}** - {date_str}{change_str}{teammate_str}")
        
        embed.description = "\n".join(history_text)
        
        # Add footer with version
        embed.set_footer(text=get_bot_footer_text())
        
        return embed
    
    @staticmethod
    def teammate_stats_embed(teammate_stats: Dict, username: str = None) -> discord.Embed:
        """Teammate statistics display showing most frequent teammates and win rates"""
        title = f"🤝 Teammate Statistics"
        if username:
            title += f" - {username}"
        
        embed = discord.Embed(
            title=title,
            color=Config.EMBED_COLOR
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
                name="🤝 Most Frequent Teammates",
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
                value=f"**{len(frequent_partners)}** frequent teammates\n"
                      f"**{total_games}** total games together\n"
                      f"**{avg_skill_overall:+.1f}** overall avg skill with teammates",
                inline=False
            )
        
        # Add footer with version
        embed.set_footer(text=get_bot_footer_text())
        
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
            embed.set_footer(text=f"This message is only visible to you • {get_bot_footer_text()}")
        else:
            embed.set_footer(text=get_bot_footer_text())
        
        return embed
    
    @staticmethod
    def success_embed(title: str, description: str) -> discord.Embed:
        """Standardized success messages"""
        embed = discord.Embed(
            title=f"✅ {title}",
            description=description,
            color=Config.SUCCESS_COLOR
        )
        embed.set_footer(text=get_bot_footer_text())
        return embed
    
    @staticmethod
    def warning_embed(title: str, description: str) -> discord.Embed:
        """Standardized warning messages"""
        embed = discord.Embed(
            title=f"⚠️ {title}",
            description=description,
            color=Config.WARNING_COLOR
        )
        embed.set_footer(text=get_bot_footer_text())
        return embed
    @staticmethod
    def team_composition_leaderboard_embed(composition_stats: Dict, guild_name: str) -> discord.Embed:
        """Team composition statistics leaderboard"""
        embed = discord.Embed(
            title=f"🏆 {guild_name} Team Composition Leaderboard",
            description=f"Most successful team combinations from {composition_stats.get('total_matches', 0)} completed matches",
            color=Config.EMBED_COLOR
        )
        
        # Top Partnerships (2-player)
        partnerships = composition_stats.get('top_partnerships', [])
        if partnerships:
            partnership_text = []
            for i, partnership in enumerate(partnerships, 1):
                wins = partnership['wins']
                names = partnership['partnership']
                partnership_text.append(f"{i}. **{names}** - {wins} wins")
            
            embed.add_field(
                name="👥 Top 5 Partnerships (2-Player)",
                value="\n".join(partnership_text) if partnership_text else "No data available",
                inline=False
            )
        
        # Top Trios (3-player)
        trios = composition_stats.get('top_trios', [])
        if trios:
            trio_text = []
            for i, trio in enumerate(trios, 1):
                wins = trio['wins']
                names = trio['composition']
                # Truncate long names for display
                if len(names) > 45:
                    names = names[:42] + "..."
                trio_text.append(f"{i}. **{names}** - {wins} wins")
            
            embed.add_field(
                name="🔺 Top 5 Trios (3-Player)",
                value="\n".join(trio_text) if trio_text else "No data available",
                inline=False
            )
        
        # Top Squads (4-player)
        squads = composition_stats.get('top_squads', [])
        if squads:
            squad_text = []
            for i, squad in enumerate(squads, 1):
                wins = squad['wins']
                names = squad['composition']
                # Truncate long names for display
                if len(names) > 45:
                    names = names[:42] + "..."
                squad_text.append(f"{i}. **{names}** - {wins} wins")
            
            embed.add_field(
                name="🔷 Top 5 Squads (4-Player)",
                value="\n".join(squad_text) if squad_text else "No data available",
                inline=False
            )
        
        # Add explanation about the data patterns
        embed.add_field(
            name="📊 Why Most Teams Have 1 Win?",
            value="• **Team Variety**: Different players join each match\n"
                  "• **Balanced Matchmaking**: System creates varied compositions\n"
                  "• **Player Availability**: Not everyone plays every match\n"
                  "• **Partnerships**: 2-player combos appear more frequently",
            inline=False
        )
        
        embed.set_footer(text=get_bot_footer_text())
        
        return embed
    
    @staticmethod
    def enhanced_team_composition_leaderboard_embed(composition_stats: Dict, guild_name: str) -> discord.Embed:
        """Enhanced team composition statistics leaderboard based on performance metrics"""
        embed = discord.Embed(
            title=f"🏆 {guild_name} Performance-Based Team Leaderboard",
            description=f"Best performing team combinations from {composition_stats.get('total_matches', 0)} completed matches\n"
                       f"📊 **Ranked by**: Placement + Rating Changes + Consistency",
            color=Config.EMBED_COLOR
        )
        
        # Top Partnerships (2-player)
        partnerships = composition_stats.get('top_partnerships', [])
        if partnerships:
            partnership_text = []
            for i, partnership in enumerate(partnerships, 1):
                name = partnership['partnership']
                matches = partnership['matches_played']
                placement = partnership['avg_placement']
                rating_change = partnership['avg_rating_change']
                score = partnership['performance_score']
                top3 = partnership['top3_finishes']
                
                # Create performance summary
                performance_line = f"{i}. **{name}** (Score: {score})"
                details_line = f"   📊 {matches} matches • Avg: {placement} place • Rating: {rating_change:+.1f} • Top 3: {top3}x"
                partnership_text.append(f"{performance_line}\n{details_line}")
            
            embed.add_field(
                name="👥 Top 15 Partnerships (2-Player)",
                value="\n".join(partnership_text) if partnership_text else "No data available",
                inline=False
            )
        
        # Top Trios (3-player)
        trios = composition_stats.get('top_trios', [])
        if trios:
            trio_text = []
            for i, trio in enumerate(trios, 1):
                name = trio['composition']
                if len(name) > 40:
                    name = name[:37] + "..."
                matches = trio['matches_played']
                placement = trio['avg_placement']
                rating_change = trio['avg_rating_change']
                score = trio['performance_score']
                top3 = trio['top3_finishes']
                
                performance_line = f"{i}. **{name}** (Score: {score})"
                details_line = f"   📊 {matches} matches • Avg: {placement} place • Rating: {rating_change:+.1f} • Top 3: {top3}x"
                trio_text.append(f"{performance_line}\n{details_line}")
            
            embed.add_field(
                name="🔺 Top 15 Trios (3-Player)",
                value="\n".join(trio_text) if trio_text else "No data available",
                inline=False
            )
        
        # Top Squads (4-player)
        squads = composition_stats.get('top_squads', [])
        if squads:
            squad_text = []
            for i, squad in enumerate(squads, 1):
                name = squad['composition']
                if len(name) > 40:
                    name = name[:37] + "..."
                matches = squad['matches_played']
                placement = squad['avg_placement']
                rating_change = squad['avg_rating_change']
                score = squad['performance_score']
                top3 = squad['top3_finishes']
                
                performance_line = f"{i}. **{name}** (Score: {score})"
                details_line = f"   📊 {matches} matches • Avg: {placement} place • Rating: {rating_change:+.1f} • Top 3: {top3}x"
                squad_text.append(f"{performance_line}\n{details_line}")
            
            embed.add_field(
                name="🔷 Top 15 Squads (4-Player)",
                value="\n".join(squad_text) if squad_text else "No data available",
                inline=False
            )
        
        # Add explanation about performance scoring
        embed.add_field(
            name="📈 Performance Scoring",
            value="• **Better Placement**: Lower average placement = higher score\n"
                  "• **Rating Growth**: Positive rating changes boost score\n"
                  "• **Consistency**: Multiple matches together show reliability\n"
                  "• **Top 3 Finishes**: Frequent podium finishes indicate strong performance",
            inline=False
        )
        
        embed.set_footer(text=get_bot_footer_text())
        
        return embed
