#!/usr/bin/env python3
"""
Test script for custom team format functionality
"""

def parse_format(format_str):
    """Parse format string like "3:3:4" into list of team sizes"""
    try:
        team_sizes = [int(x.strip()) for x in format_str.split(':')]
        return team_sizes
    except ValueError:
        return None

def validate_format(team_sizes, max_teams=6, max_team_size=8):
    """Validate custom format"""
    if not team_sizes:
        return False, "Invalid format"
    
    if len(team_sizes) > max_teams:
        return False, f"Too many teams (max {max_teams})"
    
    if len(team_sizes) < 2:
        return False, "Need at least 2 teams"
    
    if any(size < 1 for size in team_sizes):
        return False, "All team sizes must be at least 1"
    
    if any(size > max_team_size for size in team_sizes):
        return False, f"Team too large (max {max_team_size})"
    
    return True, "Valid"

def test_formats():
    """Test various format strings"""
    test_cases = [
        # Valid formats
        ("3:3:4", True, [3, 3, 4]),
        ("4:4", True, [4, 4]),
        ("3:3:3", True, [3, 3, 3]),
        ("5:4:3", True, [5, 4, 3]),
        ("2:2:2:2", True, [2, 2, 2, 2]),
        ("6:6", True, [6, 6]),
        
        # Invalid formats
        ("3", False, None),  # Only one team
        ("3:3:3:3:3:3:3", False, None),  # Too many teams
        ("0:3:3", False, None),  # Zero players
        ("9:3:3", False, None),  # Team too large
        ("abc:def", False, None),  # Non-numeric
        ("3::4", False, None),  # Empty value
        ("", False, None),  # Empty string
    ]
    
    print("🧪 Testing Custom Format Parsing")
    print("=" * 50)
    
    all_passed = True
    
    for format_str, should_be_valid, expected_sizes in test_cases:
        team_sizes = parse_format(format_str)
        is_valid, message = validate_format(team_sizes)
        
        passed = (is_valid == should_be_valid)
        if should_be_valid and passed:
            passed = (team_sizes == expected_sizes)
        
        all_passed = all_passed and passed
        
        status = "✅" if passed else "❌"
        result = f"→ {team_sizes}" if team_sizes else f"→ {message}"
        print(f"{status} '{format_str}' {result}")
    
    print("=" * 50)
    if all_passed:
        print("🎉 All format tests passed!")
    else:
        print("❌ Some format tests failed.")
    
    print("\n📊 Valid Format Examples:")
    print("  3:3:4    → Teams of 3, 3, and 4 players (10 total)")
    print("  4:4      → Teams of 4 and 4 players (8 total)")
    print("  5:3:3:3  → Teams of 5, 3, 3, and 3 players (14 total)")
    print("  2:2:2:2:2:2 → Six teams of 2 players each (12 total)")

if __name__ == "__main__":
    test_formats()
