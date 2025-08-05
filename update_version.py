#!/usr/bin/env python3
"""
Version update script for HP2BR Discord Bot
Usage: python update_version.py [type] [description]
"""

import sys
import os
from version import VersionManager

def main():
    if len(sys.argv) < 2:
        print("Usage: python update_version.py [type] [description]")
        print("Types: major, minor, patch, build")
        print("Example: python update_version.py minor 'Added voice channel exact matching'")
        sys.exit(1)
    
    version_type = sys.argv[1]
    description = sys.argv[2] if len(sys.argv) > 2 else "Version update"
    
    if version_type not in ["major", "minor", "patch", "build"]:
        print("Error: Version type must be one of: major, minor, patch, build")
        sys.exit(1)
    
    vm = VersionManager()
    
    print(f"Current version: {vm.get_version_string()}")
    print(f"Updating {version_type} version...")
    print(f"Description: {description}")
    print()
    
    new_version = vm.increment_version(version_type, description)
    
    print(f"✅ Successfully updated to {new_version}")
    print("📝 Updated CHANGES.md with new entry")
    print("🔄 Both bot and API will display the new version on next startup")

if __name__ == "__main__":
    main()
