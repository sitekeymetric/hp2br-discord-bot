#!/usr/bin/env python3
"""
Command Cleanup Script for HP2BR Discord Bot
This script helps clean up unused global commands from Discord.
"""

import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    
    # Get current global commands
    print("\n📋 Current Global Commands:")
    global_commands = await bot.tree.fetch_commands()
    
    if not global_commands:
        print("No global commands found.")
    else:
        for i, cmd in enumerate(global_commands, 1):
            print(f"{i:2d}. /{cmd.name} - {cmd.description}")
    
    print(f"\nTotal: {len(global_commands)} global commands")
    
    # Ask user what to do
    print("\n🔧 Cleanup Options:")
    print("1. Clear ALL global commands (removes everything)")
    print("2. Re-sync current commands (removes unused, adds current)")
    print("3. Just show commands (no changes)")
    
    try:
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            print("\n⚠️  WARNING: This will remove ALL global commands!")
            confirm = input("Type 'YES' to confirm: ").strip()
            
            if confirm == "YES":
                print("🧹 Clearing all global commands...")
                bot.tree.clear_commands(guild=None)  # Clear global commands
                await bot.tree.sync()
                print("✅ All global commands cleared!")
            else:
                print("❌ Cancelled.")
        
        elif choice == "2":
            print("🔄 Re-syncing commands...")
            # This will sync current commands and remove unused ones
            synced = await bot.tree.sync()
            print(f"✅ Synced {len(synced)} commands. Unused commands removed.")
            
            print("\n📋 New Command List:")
            for i, cmd in enumerate(synced, 1):
                print(f"{i:2d}. /{cmd.name}")
        
        elif choice == "3":
            print("👀 No changes made.")
        
        else:
            print("❌ Invalid choice.")
    
    except KeyboardInterrupt:
        print("\n❌ Cancelled by user.")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await bot.close()

async def main():
    """Main function"""
    token = os.getenv('DISCORD_TOKEN')
    if not token:
        print("❌ Error: DISCORD_TOKEN not found in environment variables")
        print("Make sure you have a .env file with DISCORD_TOKEN=your_token_here")
        return
    
    try:
        await bot.start(token)
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")

if __name__ == '__main__':
    print("🤖 HP2BR Discord Bot - Command Cleanup Tool")
    print("=" * 50)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
