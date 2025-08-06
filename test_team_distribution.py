#!/usr/bin/env python3
"""
Test script to verify team distribution logic
Tests various player counts to ensure optimal team size distribution
"""

def calculate_team_sizes(total_players, num_teams):
    """Calculate optimal team sizes for even distribution"""
    base_size = total_players // num_teams
    extra_players = total_players % num_teams
    
    # Create target sizes: some teams get base_size+1, others get base_size
    target_sizes = []
    for i in range(num_teams):
        if i < extra_players:
            target_sizes.append(base_size + 1)
        else:
            target_sizes.append(base_size)
    
    return target_sizes

def test_distributions():
    """Test various player/team combinations"""
    test_cases = [
        # (players, teams, expected_distribution)
        (9, 3, [3, 3, 3]),
        (10, 3, [4, 3, 3]),
        (11, 3, [4, 4, 3]),
        (12, 3, [4, 4, 4]),
        (13, 3, [5, 4, 4]),
        (14, 3, [5, 5, 4]),
        (15, 3, [5, 5, 5]),
        (8, 2, [4, 4]),
        (9, 2, [5, 4]),
        (10, 2, [5, 5]),
        (16, 4, [4, 4, 4, 4]),
        (17, 4, [5, 4, 4, 4]),
        (18, 4, [5, 5, 4, 4]),
        (19, 4, [5, 5, 5, 4]),
        (20, 4, [5, 5, 5, 5]),
        (21, 5, [5, 4, 4, 4, 4]),
        (22, 5, [5, 5, 4, 4, 4]),
        (24, 6, [4, 4, 4, 4, 4, 4]),
    ]
    
    print("🧪 Testing Team Distribution Logic")
    print("=" * 50)
    
    all_passed = True
    
    for players, teams, expected in test_cases:
        actual = calculate_team_sizes(players, teams)
        passed = actual == expected
        all_passed = all_passed and passed
        
        status = "✅" if passed else "❌"
        print(f"{status} {players} players, {teams} teams: {actual} {'✓' if passed else f'(expected {expected})'}")
    
    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed! Team distribution logic is working correctly.")
    else:
        print("❌ Some tests failed. Check the logic above.")
    
    print("\n📊 Key Examples:")
    print("  9 players, 3 teams → 3:3:3 (perfectly even)")
    print(" 10 players, 3 teams → 4:3:3 (one team gets +1)")
    print(" 11 players, 3 teams → 4:4:3 (two teams get +1)")
    print(" 12 players, 3 teams → 4:4:4 (perfectly even)")

if __name__ == "__main__":
    test_distributions()
