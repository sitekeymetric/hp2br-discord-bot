#!/usr/bin/env python3
"""
Player OpenSkill Performance Analyzer
Creates comprehensive OpenSkill performance analysis for any player by user_id

Usage:
    python3 player_openskill_analyzer.py <user_id> [guild_id]
    python3 player_openskill_analyzer.py 746147492399284237  # paizen
    python3 player_openskill_analyzer.py 1095054798350454885 696226047229952110  # aKyle with specific guild
"""

import sys
import sqlite3
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import numpy as np
from datetime import datetime
import seaborn as sns
import argparse
import os

# Set style for better looking plots
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class PlayerOpenSkillAnalyzer:
    def __init__(self, db_path="api/team_balance.db", default_guild_id=696226047229952110):
        self.db_path = db_path
        self.default_guild_id = default_guild_id
        
    def get_player_info(self, user_id, guild_id):
        """Get basic player information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT 
            u.username,
            u.user_id,
            u.rating_mu as traditional_rating,
            u.games_played,
            u.wins,
            u.losses,
            ROUND(u.wins * 100.0 / NULLIF(u.games_played, 0), 1) as win_rate
        FROM users u 
        WHERE u.guild_id = ? AND u.user_id = ?
        """
        
        cursor.execute(query, (guild_id, user_id))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
            
        return {
            'username': result[0],
            'user_id': result[1],
            'traditional_rating': result[2],
            'games_played': result[3],
            'wins': result[4],
            'losses': result[5],
            'win_rate': result[6]
        }
    
    def get_openskill_rating(self, user_id, guild_id):
        """Get current OpenSkill rating"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT 
            osr.mu,
            osr.sigma,
            (osr.mu - 3 * osr.sigma) as conservative_rating,
            osr.games_played as openskill_games,
            osr.last_updated
        FROM openskill_ratings osr
        WHERE osr.guild_id = ? AND osr.user_id = ?
        """
        
        cursor.execute(query, (guild_id, user_id))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
            
        return {
            'mu': result[0],
            'sigma': result[1],
            'conservative': result[2],
            'games_played': result[3],
            'last_updated': result[4]
        }
    
    def get_openskill_match_history(self, user_id, guild_id):
        """Get OpenSkill match history"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT 
            omh.match_id,
            m.start_time,
            omh.team_placement,
            omh.mu_before,
            omh.sigma_before,
            omh.mu_after,
            omh.sigma_after,
            (omh.mu_before - 3 * omh.sigma_before) as conservative_before,
            (omh.mu_after - 3 * omh.sigma_after) as conservative_after
        FROM openskill_match_history omh
        JOIN matches m ON omh.match_id = m.match_id
        WHERE omh.guild_id = ? AND omh.user_id = ?
        ORDER BY m.start_time ASC
        """
        
        cursor.execute(query, (guild_id, user_id))
        results = cursor.fetchall()
        conn.close()
        
        return results
    
    def create_analysis(self, user_id, guild_id=None):
        """Create comprehensive OpenSkill analysis for a player"""
        if guild_id is None:
            guild_id = self.default_guild_id
            
        # Get player info
        player_info = self.get_player_info(user_id, guild_id)
        if not player_info:
            print(f"❌ Player with user_id {user_id} not found in guild {guild_id}")
            return None
            
        # Get OpenSkill rating
        openskill_rating = self.get_openskill_rating(user_id, guild_id)
        if not openskill_rating:
            print(f"❌ No OpenSkill rating found for {player_info['username']}")
            return None
            
        # Get match history
        match_history = self.get_openskill_match_history(user_id, guild_id)
        if not match_history:
            print(f"❌ No OpenSkill match history found for {player_info['username']}")
            return None
            
        print(f"✅ Found {len(match_history)} matches for {player_info['username']}")
        
        # Convert to DataFrame
        df = pd.DataFrame(match_history, columns=[
            'match_id', 'datetime', 'placement', 'mu_before', 'sigma_before', 
            'mu_after', 'sigma_after', 'conservative_before', 'conservative_after'
        ])
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['match_number'] = range(1, len(df) + 1)
        df['mu_change'] = df['mu_after'] - df['mu_before']
        df['conservative_change'] = df['conservative_after'] - df['conservative_before']
        df['result'] = df['placement'].apply(lambda x: 'WIN' if x == 1 else 'LOSS')
        
        # Create visualization
        self._create_visualization(df, player_info, openskill_rating)
        
        return {
            'player_info': player_info,
            'openskill_rating': openskill_rating,
            'match_data': df
        }
    
    def _create_visualization(self, df, player_info, openskill_rating):
        """Create the comprehensive visualization"""
        username = player_info['username']
        
        # Create comprehensive visualization
        fig = plt.figure(figsize=(20, 16))
        fig.suptitle(f'🎮 {username} OpenSkill Performance Analysis Dashboard', 
                     fontsize=24, fontweight='bold', y=0.98)

        # 1. OpenSkill Rating Progression (μ, σ, and Conservative)
        ax1 = plt.subplot(3, 3, (1, 2))
        ax1.plot(df['datetime'], df['mu_after'], linewidth=3, marker='o', markersize=6, 
                 alpha=0.8, label='μ (Skill)', color='blue')
        ax1.plot(df['datetime'], df['conservative_after'], linewidth=3, marker='s', markersize=4, 
                 alpha=0.8, label='Conservative Rating', color='red')

        # Fill confidence interval
        ax1.fill_between(df['datetime'], 
                        df['mu_after'] - 3*df['sigma_after'],
                        df['mu_after'] + 3*df['sigma_after'],
                        alpha=0.2, color='lightblue', label='99.7% Confidence')

        ax1.axhline(y=25, color='green', linestyle='--', alpha=0.7, label='Starting μ')
        ax1.axhline(y=0, color='black', linestyle='--', alpha=0.5, label='Baseline')
        ax1.set_title('OpenSkill Rating Progression Over Time', fontsize=16, fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('OpenSkill Rating')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(df)//10)))
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)

        # 2. Skill (μ) vs Uncertainty (σ) Evolution
        ax2 = plt.subplot(3, 3, 3)
        ax2.plot(df['match_number'], df['mu_after'], linewidth=3, marker='o', 
                 color='purple', label='μ (Skill)', alpha=0.8)
        ax2_twin = ax2.twinx()
        ax2_twin.plot(df['match_number'], df['sigma_after'], linewidth=3, marker='s', 
                      color='orange', label='σ (Uncertainty)', alpha=0.8)
        ax2.set_title('Skill vs Uncertainty Evolution', fontsize=14, fontweight='bold')
        ax2.set_xlabel('Match Number')
        ax2.set_ylabel('μ (Skill Level)', color='purple')
        ax2_twin.set_ylabel('σ (Uncertainty)', color='orange')
        ax2.legend(loc='upper left')
        ax2_twin.legend(loc='upper right')
        ax2.grid(True, alpha=0.3)

        # 3. Match Results Distribution
        ax3 = plt.subplot(3, 3, 4)
        result_counts = df['result'].value_counts()
        wins = result_counts.get('WIN', 0)
        losses = result_counts.get('LOSS', 0)
        colors = ['#4ecdc4', '#ff6b6b']
        wedges, texts, autotexts = ax3.pie([wins, losses], labels=['WINS', 'LOSSES'], 
                                           autopct='%1.1f%%', colors=colors, startangle=90)
        ax3.set_title(f'Match Results\n({wins} Wins, {losses} Losses)', fontsize=14, fontweight='bold')

        # 4. Placement Distribution with Win Highlights
        ax4 = plt.subplot(3, 3, 5)
        placement_counts = df['placement'].value_counts().sort_index()
        bars = ax4.bar(placement_counts.index, placement_counts.values, alpha=0.8, color='lightblue')

        # Highlight 1st place finishes (wins)
        first_place_count = placement_counts.get(1, 0)
        if first_place_count > 0:
            first_place_idx = list(placement_counts.index).index(1)
            bars[first_place_idx].set_color('gold')
            bars[first_place_idx].set_edgecolor('orange')
            bars[first_place_idx].set_linewidth(3)

        ax4.set_title('Placement Distribution', fontsize=14, fontweight='bold')
        ax4.set_xlabel('Placement')
        ax4.set_ylabel('Frequency')
        ax4.grid(True, alpha=0.3)

        for bar in bars:
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                     f'{int(height)}', ha='center', va='bottom')

        # 5. μ (Skill) Changes Per Match
        ax5 = plt.subplot(3, 3, 6)
        colors = ['green' if x > 0 else 'red' if x < 0 else 'gray' for x in df['mu_change']]
        bars = ax5.bar(df['match_number'], df['mu_change'], color=colors, alpha=0.7)
        ax5.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        ax5.set_title('Skill (μ) Changes Per Match', fontsize=14, fontweight='bold')
        ax5.set_xlabel('Match Number')
        ax5.set_ylabel('μ Change')
        ax5.grid(True, alpha=0.3)

        # Highlight biggest gains and losses
        if len(df) > 0:
            max_gain = df['mu_change'].max()
            max_loss = df['mu_change'].min()
            max_gain_match = df[df['mu_change'] == max_gain]['match_number'].iloc[0]
            max_loss_match = df[df['mu_change'] == max_loss]['match_number'].iloc[0]

            ax5.annotate(f'Best: +{max_gain:.1f}', xy=(max_gain_match, max_gain), 
                         xytext=(max_gain_match, max_gain + 0.5), ha='center',
                         arrowprops=dict(arrowstyle='->', color='green'))
            ax5.annotate(f'Worst: {max_loss:.1f}', xy=(max_loss_match, max_loss), 
                         xytext=(max_loss_match, max_loss - 0.5), ha='center',
                         arrowprops=dict(arrowstyle='->', color='red'))

        # 6. Conservative Rating Confidence Bands
        ax6 = plt.subplot(3, 3, 7)
        ax6.fill_between(df['match_number'], 
                        df['mu_after'] - 3*df['sigma_after'],
                        df['mu_after'] + 3*df['sigma_after'],
                        alpha=0.3, color='lightblue', label='99.7% Confidence')
        ax6.fill_between(df['match_number'], 
                        df['mu_after'] - 2*df['sigma_after'],
                        df['mu_after'] + 2*df['sigma_after'],
                        alpha=0.4, color='lightgreen', label='95.4% Confidence')
        ax6.fill_between(df['match_number'], 
                        df['mu_after'] - df['sigma_after'],
                        df['mu_after'] + df['sigma_after'],
                        alpha=0.5, color='lightyellow', label='68.2% Confidence')

        ax6.plot(df['match_number'], df['mu_after'], linewidth=3, 
                 color='blue', label='μ (Skill)', marker='o')
        ax6.plot(df['match_number'], df['conservative_after'], linewidth=2, 
                 color='red', label='Conservative Rating', marker='s')
        ax6.axhline(y=0, color='black', linestyle='--', alpha=0.5)
        ax6.set_title('OpenSkill Confidence Evolution', fontsize=14, fontweight='bold')
        ax6.set_xlabel('Match Number')
        ax6.set_ylabel('OpenSkill Rating')
        ax6.legend()
        ax6.grid(True, alpha=0.3)

        # 7. Performance Trends (Rolling Averages)
        ax7 = plt.subplot(3, 3, 8)
        window = min(5, len(df))
        df['mu_rolling'] = df['mu_after'].rolling(window=window, min_periods=1).mean()
        df['placement_rolling'] = df['placement'].rolling(window=window, min_periods=1).mean()

        ax7.plot(df['match_number'], df['mu_rolling'], linewidth=3, 
                 color='blue', label=f'μ ({window}-match avg)', marker='o')
        ax7_twin = ax7.twinx()
        ax7_twin.plot(df['match_number'], df['placement_rolling'], linewidth=3, 
                      color='red', label=f'Placement ({window}-match avg)', marker='s')

        ax7.set_title(f'Performance Trends ({window}-Match Rolling Average)', fontsize=14, fontweight='bold')
        ax7.set_xlabel('Match Number')
        ax7.set_ylabel('Average μ', color='blue')
        ax7_twin.set_ylabel('Average Placement', color='red')
        ax7.legend(loc='upper left')
        ax7_twin.legend(loc='upper right')
        ax7.grid(True, alpha=0.3)

        # 8. Key Statistics Summary
        ax8 = plt.subplot(3, 3, 9)
        ax8.axis('off')

        # Calculate key stats
        total_matches = len(df)
        wins = len(df[df['result'] == 'WIN'])
        win_rate = (wins / total_matches) * 100 if total_matches > 0 else 0
        avg_placement = df['placement'].mean() if total_matches > 0 else 0
        current_mu = df['mu_after'].iloc[-1] if total_matches > 0 else 0
        current_sigma = df['sigma_after'].iloc[-1] if total_matches > 0 else 0
        current_conservative = df['conservative_after'].iloc[-1] if total_matches > 0 else 0
        mu_change = current_mu - df['mu_before'].iloc[0] if total_matches > 0 else 0
        peak_mu = df['mu_after'].max() if total_matches > 0 else 0
        lowest_conservative = df['conservative_after'].min() if total_matches > 0 else 0

        # Performance phases
        early_avg = df['mu_after'][:min(10, len(df))].mean() if total_matches > 0 else 0
        recent_avg = df['mu_after'][-min(10, len(df)):].mean() if total_matches > 0 else 0
        starting_mu = df['mu_before'].iloc[0] if total_matches > 0 else 0

        stats_text = f"""
{username.upper()}'S OPENSKILL STATISTICS

Total Matches: {total_matches}
Wins: {wins} ({win_rate:.1f}%)
Average Placement: {avg_placement:.1f}

CURRENT OPENSKILL RATING
• μ (Skill): {current_mu:.1f}
• σ (Uncertainty): {current_sigma:.1f}
• Conservative: {current_conservative:.1f}

SKILL PROGRESSION
• Starting μ: {starting_mu:.1f}
• Current μ: {current_mu:.1f}
• Total μ Change: {mu_change:+.1f}
• Peak μ: {peak_mu:.1f}
• Lowest Conservative: {lowest_conservative:.1f}

PERFORMANCE INSIGHTS
• Early Average μ: {early_avg:.1f}
• Recent Average μ: {recent_avg:.1f}
• Trend: {"Improving" if recent_avg > early_avg else "Declining" if recent_avg < early_avg else "Stable"}
• Uncertainty: {"High" if current_sigma > 7 else "Medium" if current_sigma > 5 else "Low"}
"""

        ax8.text(0.05, 0.95, stats_text, transform=ax8.transAxes, fontsize=11,
                 verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.8))

        plt.tight_layout()
        plt.subplots_adjust(top=0.94)
        
        # Save the plot
        filename = f'{username}_openskill_analysis.png'
        plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
        print(f"✅ Analysis saved as: {filename}")
        
        plt.show()
        
        # Print summary
        print(f"\n📊 {username}'s OpenSkill Stats Summary:")
        print(f"   • Total Matches: {total_matches}")
        print(f"   • Win Rate: {win_rate:.1f}% ({wins} wins)")
        print(f"   • Current μ (Skill): {current_mu:.1f}")
        print(f"   • Current σ (Uncertainty): {current_sigma:.1f}")
        print(f"   • Conservative Rating: {current_conservative:.1f}")
        print(f"   • Skill Change: {mu_change:+.1f}")
        print(f"   • Peak Skill: {peak_mu:.1f}")
        print(f"   • Average Placement: {avg_placement:.1f}")
        print(f"   • Performance Trend: {'Improving' if recent_avg > early_avg else 'Declining' if recent_avg < early_avg else 'Stable'}")

def main():
    parser = argparse.ArgumentParser(description='Generate OpenSkill performance analysis for a player')
    parser.add_argument('user_id', type=int, help='User ID of the player to analyze')
    parser.add_argument('guild_id', type=int, nargs='?', default=696226047229952110, 
                       help='Guild ID (optional, defaults to 696226047229952110)')
    parser.add_argument('--db', type=str, default='api/team_balance.db', 
                       help='Path to database file (default: api/team_balance.db)')
    
    args = parser.parse_args()
    
    # Check if database exists
    if not os.path.exists(args.db):
        print(f"❌ Database file not found: {args.db}")
        print("Make sure you're running this from the correct directory or specify the correct path with --db")
        return
    
    analyzer = PlayerOpenSkillAnalyzer(db_path=args.db, default_guild_id=args.guild_id)
    result = analyzer.create_analysis(args.user_id, args.guild_id)
    
    if result:
        print(f"\n🎉 Analysis complete for {result['player_info']['username']}!")
    else:
        print("\n❌ Analysis failed. Please check the user_id and guild_id.")

if __name__ == "__main__":
    main()
