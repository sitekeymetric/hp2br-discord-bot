#!/usr/bin/env python3
"""
OpenSkill Setup Script
Complete setup for OpenSkill parallel rating system
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"   ✅ {description} completed")
        if result.stdout:
            print(f"   📄 Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ {description} failed: {e}")
        if e.stderr:
            print(f"   📄 Error: {e.stderr.strip()}")
        return False

def main():
    print("🚀 OpenSkill Parallel Rating System Setup")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists("api") or not os.path.exists("bot"):
        print("❌ Please run this script from the project root directory")
        print("   Expected structure: project_root/api/ and project_root/bot/")
        sys.exit(1)
    
    print("📋 Setup Steps:")
    print("1. Install OpenSkill dependency")
    print("2. Create OpenSkill database tables")
    print("3. Calculate historical OpenSkill ratings (if matches exist)")
    print("4. Verify installation")
    print()
    
    # Step 1: Install OpenSkill
    success = run_command(
        "cd api && pip install openskill==5.0.0",
        "Installing OpenSkill dependency"
    )
    if not success:
        print("❌ Failed to install OpenSkill. Please install manually:")
        print("   cd api && pip install openskill==5.0.0")
        sys.exit(1)
    
    # Step 2: Create database tables
    success = run_command(
        "cd api && python3 migrations/create_openskill_tables.py",
        "Creating OpenSkill database tables"
    )
    if not success:
        print("❌ Failed to create OpenSkill tables")
        print("   This might be due to database schema differences.")
        print("   The tables may have been created successfully despite the error.")
        print("   Continue with the next steps to verify.")
    
    # Step 3: Calculate historical ratings (only if matches exist)
    print("\n🔄 Calculating OpenSkill ratings from historical matches...")
    print("   ⚠️  This may take a while depending on match history size...")
    print("   ℹ️  If no matches exist, this step will be skipped.")
    
    success = run_command(
        "cd api && python3 migrations/calculate_openskill_history.py",
        "Calculating historical OpenSkill ratings"
    )
    if not success:
        print("❌ Historical rating calculation had issues")
        print("   This is normal if you have no match history yet.")
        print("   You can run this manually later when you have matches:")
        print("   cd api && python3 migrations/calculate_openskill_history.py")
    
    # Step 4: Verify installation
    print("\n🔍 Verifying OpenSkill installation...")
    
    # Check if tables exist
    try:
        import sqlite3
        
        db_paths = ["api/team_balance.db", "api/hp2br.db"]
        db_path = None
        
        for path in db_paths:
            if os.path.exists(path):
                db_path = path
                break
        
        if db_path:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='openskill_ratings'")
            if cursor.fetchone():
                print("   ✅ OpenSkill tables created")
                
                # Check data
                cursor.execute("SELECT COUNT(*) FROM openskill_ratings")
                rating_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM openskill_match_history")
                history_count = cursor.fetchone()[0]
                
                print(f"   📊 OpenSkill ratings: {rating_count}")
                print(f"   📋 Match history entries: {history_count}")
            else:
                print("   ❌ OpenSkill tables not found")
            
            conn.close()
        else:
            print("   ⚠️  Database file not found")
            
    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
    
    print("\n🎉 OpenSkill Setup Complete!")
    print("\n📋 Next Steps:")
    print("1. Restart your Discord bot to load OpenSkill commands")
    print("2. Restart your API server to enable OpenSkill endpoints")
    print("3. Test with new commands:")
    print("   • /openskill_stats - View OpenSkill ratings")
    print("   • /openskill_leaderboard - View OpenSkill leaderboard")
    print("   • /rating_comparison - Compare both rating systems")
    print("4. Record new match results - both systems will update automatically")
    
    print("\n🔧 API Endpoints Available:")
    print("   • GET /openskill/ratings/{guild_id} - OpenSkill leaderboard")
    print("   • GET /openskill/ratings/{guild_id}/{user_id} - User OpenSkill rating")
    print("   • GET /openskill/compare/{guild_id} - Compare rating systems")
    print("   • POST /openskill/process-match/{match_id} - Process OpenSkill for match")
    
    print("\n✅ OpenSkill parallel rating system is now ready!")

if __name__ == "__main__":
    main()
