"""
Advanced Rating System UI Components
Provides rich Discord embeds and views for the new rating system
"""

import discord
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class AdvancedRatingEmbeds:
    """Rich embeds for advanced rating system"""
    
    # Color scheme for different rating tiers
    TIER_COLORS = {
        "Legendary": 0xFFD700,  # Gold
        "Elite": 0xFF6B6B,      # Red
        "Expert": 0x4ECDC4,     # Teal
        "Advanced": 0x45B7D1,   # Blue
        "Intermediate": 0x96CEB4, # Green
        "Beginner": 0xFECA57,   # Yellow
        "Novice": 0xFD79A8,     # Pink
        "Learning": 0xA0A0A0    # Gray
    }
    
    @classmethod
    def get_tier_color(cls, tier: str) -> int:
        """Get color for rating tier"""
        return cls.TIER_COLORS.get(tier, 0x2B5CE6)
    
    @classmethod
    def get_tier_emoji(cls, tier: str) -> str:
        """Get emoji for rating tier"""
        tier_emojis = {
            "Legendary": "🏆",
            "Elite": "💎",
            "Expert": "🥇",
            "Advanced": "🥈",
            "Intermediate": "🥉",
            "Beginner": "📊",
            "Novice": "📈",
            "Learning": "🌱"
        }
        return tier_emojis.get(tier, "⭐")
    
    @classmethod
    def create_rating_preview_embed(cls, player_rating: float, team_avg: float, 
                                  opponent_teams: List[Dict], previews: Dict[int, float],
                                  username: str) -> discord.Embed:
        """Create rating change preview embed"""
        
        # Calculate opponent strength
        if opponent_teams:
            avg_opponent = sum(team['avg_rating'] for team in opponent_teams) / len(opponent_teams)
            strength_diff = avg_opponent - team_avg
        else:
            avg_opponent = team_avg
            strength_diff = 0
        
        # Determine strength assessment
        if strength_diff > 200:
            strength_text = f"💪 **Much Stronger** (+{strength_diff:.0f})"
            strength_color = 0xFF6B6B
        elif strength_diff > 50:
            strength_text = f"💪 **Stronger** (+{strength_diff:.0f})"
            strength_color = 0xFECA57
        elif strength_diff > -50:
            strength_text = f"⚖️ **Similar** ({strength_diff:+.0f})"
            strength_color = 0x4ECDC4
        elif strength_diff > -200:
            strength_text = f"📉 **Weaker** ({strength_diff:.0f})"
            strength_color = 0x96CEB4
        else:
            strength_text = f"📉 **Much Weaker** ({strength_diff:.0f})"
            strength_color = 0xA0A0A0
        
        # Get player tier info
        player_tier = cls._get_tier_name(player_rating)
        player_emoji = cls.get_tier_emoji(player_tier)
        
        embed = discord.Embed(
            title="🎯 Advanced Rating Change Preview",
            description=f"**{username}** - {player_emoji} {player_tier} ({player_rating:.0f})",
            color=strength_color,
            timestamp=datetime.utcnow()
        )
        
        # Team composition
        embed.add_field(
            name="👥 Team Composition",
            value=f"**Your Rating:** {player_rating:.0f}\n"
                  f"**Team Average:** {team_avg:.0f}\n"
                  f"**Individual Factor:** {'+' if player_rating > team_avg else ''}{player_rating - team_avg:.0f}",
            inline=True
        )
        
        # Opponent strength
        embed.add_field(
            name="⚔️ Opponent Strength",
            value=f"**Opponent Average:** {avg_opponent:.0f}\n"
                  f"**Strength Difference:** {strength_text}",
            inline=True
        )
        
        # Rating previews
        preview_text = ""
        key_placements = [1, 3, 5, 10, 15, 20, 25, 30]
        
        for placement in key_placements:
            if placement in previews:
                change = previews[placement]
                new_rating = player_rating + change
                
                if change > 0:
                    change_text = f"+{change:.0f}"
                    emoji = "📈"
                else:
                    change_text = f"{change:.0f}"
                    emoji = "📉"
                
                if placement <= 3:
                    rank_emoji = ["🥇", "🥈", "🥉"][placement - 1]
                elif placement <= 10:
                    rank_emoji = "🏆"
                elif placement <= 20:
                    rank_emoji = "📊"
                else:
                    rank_emoji = "💀"
                
                preview_text += f"{rank_emoji} **{placement}{'st' if placement == 1 else 'nd' if placement == 2 else 'rd' if placement == 3 else 'th'}:** {change_text} → {new_rating:.0f}\n"
        
        embed.add_field(
            name="📊 Rating Change Previews",
            value=preview_text,
            inline=False
        )
        
        # Tips based on opponent strength
        if strength_diff > 100:
            tip = "💡 **Tip:** You're facing stronger opponents - big rewards for good performance!"
        elif strength_diff < -100:
            tip = "⚠️ **Warning:** You're facing weaker opponents - reduced rewards and harsher penalties!"
        else:
            tip = "⚖️ **Info:** Balanced match - standard rating changes apply."
        
        embed.add_field(
            name="💭 Match Assessment",
            value=tip,
            inline=False
        )
        
        embed.set_footer(text="Advanced Rating System v3.0.0 • Opponent strength matters!")
        
        return embed
    
    @classmethod
    def create_rating_change_breakdown_embed(cls, username: str, breakdown: Dict, 
                                           rating_before: float, rating_after: float,
                                           tier_before: str, tier_after: str) -> discord.Embed:
        """Create detailed rating change breakdown embed"""
        
        rating_change = breakdown['final_change']
        
        # Determine embed color based on change
        if rating_change > 50:
            color = 0x00FF00  # Bright green for big gains
        elif rating_change > 0:
            color = 0x96CEB4  # Light green for gains
        elif rating_change > -50:
            color = 0xFECA57  # Yellow for small losses
        else:
            color = 0xFF6B6B  # Red for big losses
        
        # Get tier emojis
        tier_before_emoji = cls.get_tier_emoji(tier_before)
        tier_after_emoji = cls.get_tier_emoji(tier_after)
        
        embed = discord.Embed(
            title="📊 Rating Change Breakdown",
            description=f"**{username}**",
            color=color,
            timestamp=datetime.utcnow()
        )
        
        # Rating change summary
        change_text = f"+{rating_change:.1f}" if rating_change > 0 else f"{rating_change:.1f}"
        embed.add_field(
            name="🎯 Rating Change",
            value=f"**{rating_before:.0f}** → **{rating_after:.0f}** ({change_text})",
            inline=True
        )
        
        # Tier change
        if tier_before != tier_after:
            tier_text = f"{tier_before_emoji} {tier_before} → {tier_after_emoji} {tier_after}"
            if cls._get_tier_rank(tier_after) > cls._get_tier_rank(tier_before):
                tier_text += " 🎉"
            else:
                tier_text += " 📉"
        else:
            tier_text = f"{tier_before_emoji} {tier_before}"
        
        embed.add_field(
            name="🏆 Tier",
            value=tier_text,
            inline=True
        )
        
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer
        
        # Detailed breakdown
        breakdown_text = (
            f"**Base Score:** {breakdown['base_score']:+.1f}\n"
            f"**Opponent Multiplier:** ×{breakdown['opponent_multiplier']:.2f}\n"
            f"**Individual Factor:** ×{breakdown['individual_adjustment']:.2f}\n"
            f"**Rating Curve:** ×{breakdown['curve_multiplier']:.2f}\n"
            f"**Preliminary:** {breakdown['preliminary_change']:+.1f}\n"
            f"**Final Change:** {breakdown['final_change']:+.1f}"
        )
        
        embed.add_field(
            name="🧮 Calculation Details",
            value=breakdown_text,
            inline=True
        )
        
        # Explanation
        explanation = cls._get_breakdown_explanation(breakdown)
        embed.add_field(
            name="💡 What This Means",
            value=explanation,
            inline=True
        )
        
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer
        
        embed.set_footer(text="Advanced Rating System v3.0.0 • Detailed calculation breakdown")
        
        return embed
    
    @classmethod
    def create_advanced_rating_scale_embed(cls) -> discord.Embed:
        """Create comprehensive rating scale embed"""
        
        embed = discord.Embed(
            title="🏆 Advanced Rating System v3.0.0",
            description="**Complete rating scale with opponent strength consideration**",
            color=0x2B5CE6,
            timestamp=datetime.utcnow()
        )
        
        # Placement scores (top section)
        winning_scores = (
            "🥇 **1st Place:** +50 base\n"
            "🥈 **2nd Place:** +35 base\n"
            "🥉 **3rd Place:** +25 base\n"
            "🏆 **4th Place:** +18 base\n"
            "🏆 **5th Place:** +12 base\n"
            "📊 **6th-8th:** +8 to ±0 base"
        )
        
        embed.add_field(
            name="🎯 Winning Tiers",
            value=winning_scores,
            inline=True
        )
        
        # Penalty scores
        penalty_scores = (
            "📉 **9th-15th:** -5 to -50 base\n"
            "🔻 **16th-20th:** -62 to -120 base\n"
            "💀 **21st-25th:** -138 to -220 base\n"
            "💀 **26th-30th:** -243 to -345 base"
        )
        
        embed.add_field(
            name="📉 Penalty Tiers",
            value=penalty_scores,
            inline=True
        )
        
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Spacer
        
        # Rating tiers
        tier_info = (
            "🏆 **Legendary (2200+):** Top 0.1%\n"
            "💎 **Elite (2000+):** Top 1%\n"
            "🥇 **Expert (1800+):** Top 5%\n"
            "🥈 **Advanced (1600+):** Top 15%\n"
            "🥉 **Intermediate (1400+):** Middle 40%\n"
            "📊 **Beginner (1200+):** Bottom 30%\n"
            "📈 **Novice (1000+):** Bottom 10%\n"
            "🌱 **Learning (<1000):** Bottom 4%"
        )
        
        embed.add_field(
            name="🏆 Rating Tiers",
            value=tier_info,
            inline=True
        )
        
        # Opponent strength multipliers
        strength_info = (
            "💪 **Much Stronger (+500):** ×2.2\n"
            "💪 **Stronger (+150):** ×1.4\n"
            "⚖️ **Similar (±50):** ×1.0\n"
            "📉 **Weaker (-150):** ×0.6\n"
            "📉 **Much Weaker (-500):** ×0.2"
        )
        
        embed.add_field(
            name="⚔️ Opponent Strength",
            value=strength_info,
            inline=True
        )
        
        # Climbing penalties
        curve_info = (
            "🏆 **Elite (2000+):** ×0.3 climbing\n"
            "🥇 **Expert (1800+):** ×0.5 climbing\n"
            "🥈 **Advanced (1600+):** ×0.7 climbing\n"
            "📊 **Lower Tiers:** ×1.0 climbing\n\n"
            "💀 **Elite drops:** ×1.5 faster\n"
            "📉 **Expert drops:** ×1.3 faster"
        )
        
        embed.add_field(
            name="📈 Rating Curve",
            value=curve_info,
            inline=True
        )
        
        # Key features
        features = (
            "• **Opponent strength matters** - bigger rewards vs stronger teams\n"
            "• **Curved scaling** - harder to climb at higher ratings\n"
            "• **Enhanced penalties** - up to -345 for 30th place\n"
            "• **Individual recognition** - your skill vs team average\n"
            "• **Anti-inflation** - elite players drop faster"
        )
        
        embed.add_field(
            name="✨ Key Features",
            value=features,
            inline=False
        )
        
        embed.set_footer(text="Use /rating_preview to see your potential changes!")
        
        return embed
    
    @classmethod
    def _get_tier_name(cls, rating: float) -> str:
        """Get tier name for rating"""
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
    def _get_tier_rank(cls, tier: str) -> int:
        """Get numeric rank for tier (higher = better)"""
        tier_ranks = {
            "Legendary": 8,
            "Elite": 7,
            "Expert": 6,
            "Advanced": 5,
            "Intermediate": 4,
            "Beginner": 3,
            "Novice": 2,
            "Learning": 1
        }
        return tier_ranks.get(tier, 0)
    
    @classmethod
    def _get_breakdown_explanation(cls, breakdown: Dict) -> str:
        """Generate explanation for rating breakdown"""
        explanations = []
        
        # Opponent strength
        opponent_mult = breakdown['opponent_multiplier']
        if opponent_mult > 1.5:
            explanations.append("💪 Huge underdog bonus")
        elif opponent_mult > 1.1:
            explanations.append("💪 Underdog bonus")
        elif opponent_mult < 0.5:
            explanations.append("📉 Heavy favorite penalty")
        elif opponent_mult < 0.9:
            explanations.append("📉 Favorite penalty")
        
        # Individual factor
        individual = breakdown['individual_adjustment']
        if individual > 1.05:
            explanations.append("🎯 Being carried bonus")
        elif individual < 0.95:
            explanations.append("🎯 Carrying team penalty")
        
        # Rating curve
        curve = breakdown['curve_multiplier']
        if curve < 0.8:
            explanations.append("📈 Elite climbing penalty")
        elif curve > 1.2:
            explanations.append("📉 Elite dropping bonus")
        
        return "\n".join(explanations) if explanations else "⚖️ Standard calculation"


class AdvancedRatingView(discord.ui.View):
    """Interactive view for advanced rating system"""
    
    def __init__(self, timeout: float = 300):
        super().__init__(timeout=timeout)
    
    @discord.ui.button(label="📊 Rating Preview", style=discord.ButtonStyle.primary)
    async def rating_preview(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show rating preview for current match"""
        await interaction.response.send_message(
            "Rating preview functionality will be implemented with match context.",
            ephemeral=True
        )
    
    @discord.ui.button(label="🏆 Rating Scale", style=discord.ButtonStyle.secondary)
    async def rating_scale(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Show complete rating scale"""
        embed = AdvancedRatingEmbeds.create_advanced_rating_scale_embed()
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @discord.ui.button(label="❓ How It Works", style=discord.ButtonStyle.secondary)
    async def how_it_works(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Explain how the advanced rating system works"""
        
        embed = discord.Embed(
            title="🧮 How Advanced Rating Works",
            description="**Step-by-step calculation process**",
            color=0x4ECDC4,
            timestamp=datetime.utcnow()
        )
        
        steps = (
            "**1. Base Score** - Your placement determines base points\n"
            "**2. Opponent Strength** - Multiplier based on enemy team ratings\n"
            "**3. Individual Factor** - Your skill vs your team average\n"
            "**4. Rating Curve** - Climbing penalty/dropping bonus by tier\n"
            "**5. Final Calculation** - All factors combined with limits"
        )
        
        embed.add_field(
            name="📊 Calculation Steps",
            value=steps,
            inline=False
        )
        
        examples = (
            "**Underdog Win:** 1200 player beats 1600 teams → +90 points\n"
            "**Expected Elite Win:** 2100 player beats 1800 teams → +9 points\n"
            "**Elite Disaster:** 2000 player gets 25th place → -330 points"
        )
        
        embed.add_field(
            name="💡 Examples",
            value=examples,
            inline=False
        )
        
        embed.set_footer(text="Advanced Rating System v3.0.0")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
