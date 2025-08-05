#!/usr/bin/env python3
"""
Test script to verify the match result validation logic
"""

def validate_results(team_results: dict, num_teams: int) -> tuple[bool, str]:
    """Test version of the validation logic"""
    if len(team_results) != num_teams:
        return False, "Please select a result for all teams."
    
    wins = sum(1 for result in team_results.values() if result == "win")
    losses = sum(1 for result in team_results.values() if result == "loss")
    draws = sum(1 for result in team_results.values() if result == "draw")
    
    # Validation rules
    if draws > 0:
        # If any team has draw, all teams must have draw
        if draws != num_teams:
            return False, "If it's a draw, all teams must be marked as 'Draw'."
    else:
        # For win/loss, exactly one team should win, others should lose
        if wins != 1:
            return False, "Exactly one team must be marked as 'Win' (others as 'Loss')."
        if losses != num_teams - 1:
            return False, "All non-winning teams must be marked as 'Loss'."
    
    return True, ""

def test_validation():
    """Test various result combinations"""
    print("Testing match result validation logic:")
    print("=" * 50)
    
    test_cases = [
        # Valid cases
        ({1: "win", 2: "loss", 3: "loss"}, 3, True, "Normal win/loss"),
        ({1: "draw", 2: "draw", 3: "draw"}, 3, True, "All draw"),
        ({1: "win", 2: "loss"}, 2, True, "Two team win/loss"),
        ({1: "draw", 2: "draw"}, 2, True, "Two team draw"),
        
        # Invalid cases
        ({1: "win", 2: "win", 3: "loss"}, 3, False, "Multiple winners"),
        ({1: "loss", 2: "loss", 3: "loss"}, 3, False, "No winner"),
        ({1: "draw", 2: "loss", 3: "loss"}, 3, False, "Mixed draw/loss"),
        ({1: "win", 2: "draw", 3: "loss"}, 3, False, "Mixed win/draw/loss"),
        ({1: "win", 2: "loss"}, 3, False, "Incomplete selection"),
        ({}, 3, False, "No selections"),
    ]
    
    for team_results, num_teams, expected_valid, description in test_cases:
        is_valid, error_msg = validate_results(team_results, num_teams)
        
        status = "✅ PASS" if is_valid == expected_valid else "❌ FAIL"
        print(f"{status} {description}")
        print(f"   Input: {team_results}")
        print(f"   Expected: {'Valid' if expected_valid else 'Invalid'}")
        print(f"   Got: {'Valid' if is_valid else f'Invalid - {error_msg}'}")
        print()

if __name__ == "__main__":
    test_validation()
