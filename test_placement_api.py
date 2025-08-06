#!/usr/bin/env python3
"""
Test script for placement-based result recording API endpoint
"""

import requests
import json

def test_placement_endpoint():
    """Test the placement-based result recording endpoint"""
    
    # API base URL (adjust if needed)
    base_url = "http://localhost:8000"
    
    # Test data
    match_id = "test-match-123"
    team_placements = {
        "1": 2,  # Team 1 got 2nd place
        "2": 1,  # Team 2 got 1st place
        "3": 3   # Team 3 got 3rd place
    }
    
    # Make request
    url = f"{base_url}/matches/{match_id}/placement-result"
    
    try:
        response = requests.put(url, json=team_placements)
        
        print(f"🔗 Request URL: {url}")
        print(f"📤 Request Data: {json.dumps(team_placements, indent=2)}")
        print(f"📊 Response Status: {response.status_code}")
        print(f"📥 Response Data: {response.text}")
        
        if response.status_code == 200:
            print("✅ API endpoint is working!")
        else:
            print("❌ API endpoint returned an error")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API server")
        print("💡 Make sure the API server is running on http://localhost:8000")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    print("🧪 Testing Placement-Based Result Recording API")
    print("=" * 50)
    test_placement_endpoint()
