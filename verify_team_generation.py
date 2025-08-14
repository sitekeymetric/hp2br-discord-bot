#!/usr/bin/env python3
"""
Team Generation Logic Verification
Test the team count determination logic against requirements
"""

def calculate_team_count_and_sizes(player_count):
    """Calculate team count and expected sizes based on the new logic"""
    
    # Constants
    SINGLE_TEAM_THRESHOLD = 4
    TWO_TEAM_THRESHOLD = 5
    
    if player_count <= SINGLE_TEAM_THRESHOLD:
        # 1-4 players: Single team
        actual_num_teams = 1
        case = "Single team"
    elif player_count == TWO_TEAM_THRESHOLD:
        # 5 players: 2 teams (2:3 split)
        actual_num_teams = 2
        case = "2:3 split"
    elif player_count == 6:
        actual_num_teams = 2  # 6 players: 3:3 split
        case = "3:3 split"
    elif player_count == 7:
        actual_num_teams = 2  # 7 players: 3:4 split
        case = "3:4 split"
    elif player_count == 8:
        actual_num_teams = 2  # 8 players: 4:4 split
        case = "4:4 split"
    else:
        # 9+ players: Aim for 3-4 players per team (min 3, max 4)
        actual_num_teams = max(3, (player_count + 3) // 4)  # Round up, minimum 3 teams
        
        # Ensure we don't exceed maximum reasonable teams
        max_reasonable_teams = min(6, player_count // 3)  # Max 6 teams, min 3 per team
        actual_num_teams = min(actual_num_teams, max_reasonable_teams)
        case = "3-4 per team"
    
    # Calculate expected team sizes
    base_size = player_count // actual_num_teams
    extra_players = player_count % actual_num_teams
    expected_sizes = []
    for i in range(actual_num_teams):
        if i < extra_players:
            expected_sizes.append(base_size + 1)
        else:
            expected_sizes.append(base_size)
    
    return actual_num_teams, expected_sizes, case

def verify_requirements():
    """Verify the logic meets all requirements"""
    
    print("🔍 Team Generation Logic Verification")
    print("=" * 50)
    
    # Test cases based on requirements
    test_cases = [
        # (player_count, expected_description)
        (1, "Single team"),
        (2, "Single team"), 
        (3, "Single team"),
        (4, "Single team"),
        (5, "2:3 split"),
        (6, "3:3 split"),
        (7, "3:4 split"),
        (8, "4:4 split"),
        (9, "3-4 per team"),
        (10, "3-4 per team"),
        (11, "3-4 per team"),
        (12, "3-4 per team"),
        (15, "3-4 per team"),
        (18, "3-4 per team"),
        (20, "3-4 per team"),
        (24, "3-4 per team"),
    ]
    
    all_passed = True
    
    for player_count, expected_desc in test_cases:
        num_teams, sizes, case = calculate_team_count_and_sizes(player_count)
        
        # Check if team sizes are within 3-4 range (except special cases)
        min_size = min(sizes)
        max_size = max(sizes)
        
        # Validation rules
        valid = True
        issues = []
        
        if player_count <= 4:
            # Should be single team
            if num_teams != 1:
                valid = False
                issues.append(f"Expected 1 team, got {num_teams}")
        elif player_count == 5:
            # Should be 2:3
            if sizes != [3, 2] and sizes != [2, 3]:
                valid = False
                issues.append(f"Expected 2:3 split, got {sizes}")
        elif player_count == 6:
            # Should be 3:3
            if sizes != [3, 3]:
                valid = False
                issues.append(f"Expected 3:3 split, got {sizes}")
        elif player_count == 7:
            # Should be 3:4 or 4:3
            if sizes != [4, 3] and sizes != [3, 4]:
                valid = False
                issues.append(f"Expected 3:4 split, got {sizes}")
        elif player_count == 8:
            # Should be 4:4
            if sizes != [4, 4]:
                valid = False
                issues.append(f"Expected 4:4 split, got {sizes}")
        else:
            # 9+ players: should be 3-4 per team
            if min_size < 3:
                valid = False
                issues.append(f"Team too small: {min_size} < 3")
            if max_size > 4:
                valid = False
                issues.append(f"Team too large: {max_size} > 4")
        
        # Display result
        status = "✅" if valid else "❌"
        sizes_str = ":".join(map(str, sizes))
        
        print(f"{status} {player_count:2d} players → {num_teams} teams ({sizes_str}) - {case}")
        
        if not valid:
            all_passed = False
            for issue in issues:
                print(f"    ⚠️  {issue}")
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All test cases passed! Team generation logic is correct.")
    else:
        print("❌ Some test cases failed. Logic needs adjustment.")
    
    return all_passed

def show_detailed_examples():
    """Show detailed examples for key player counts"""
    
    print("\n📊 Detailed Examples:")
    print("-" * 30)
    
    examples = [4, 5, 6, 7, 8, 9, 10, 12, 15, 18, 20, 24]
    
    for player_count in examples:
        num_teams, sizes, case = calculate_team_count_and_sizes(player_count)
        sizes_str = ":".join(map(str, sizes))
        
        print(f"{player_count:2d} players → {num_teams} teams ({sizes_str})")
        
        # Show team assignments
        team_assignments = []
        player_num = 1
        for i, size in enumerate(sizes):
            team_players = list(range(player_num, player_num + size))
            team_assignments.append(f"Team {i+1}: {team_players}")
            player_num += size
        
        for assignment in team_assignments:
            print(f"    {assignment}")
        print()

if __name__ == "__main__":
    # Run verification
    passed = verify_requirements()
    
    # Show detailed examples
    show_detailed_examples()
    
    if passed:
        print("✅ Team generation logic verification completed successfully!")
    else:
        print("❌ Team generation logic needs fixes!")
        exit(1)
