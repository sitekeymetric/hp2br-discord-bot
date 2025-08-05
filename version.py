#!/usr/bin/env python3
"""
Centralized version management for HP2BR Discord Bot
Handles version incrementing and changelog updates
"""

import os
import json
import datetime
from typing import Dict, Any

class VersionManager:
    def __init__(self, root_dir: str = None):
        self.root_dir = root_dir or os.path.dirname(os.path.abspath(__file__))
        self.version_file = os.path.join(self.root_dir, "VERSION.json")
        self.changes_file = os.path.join(self.root_dir, "CHANGES.md")
        
    def get_version_info(self) -> Dict[str, Any]:
        """Get current version information"""
        if os.path.exists(self.version_file):
            with open(self.version_file, 'r') as f:
                return json.load(f)
        else:
            # Initialize with default version
            return {
                "major": 1,
                "minor": 0,
                "patch": 0,
                "build": 1,
                "last_updated": datetime.datetime.now().isoformat(),
                "description": "Initial release"
            }
    
    def get_version_string(self) -> str:
        """Get formatted version string (e.g., 'v1.2.3-build.45')"""
        info = self.get_version_info()
        return f"v{info['major']}.{info['minor']}.{info['patch']}-build.{info['build']}"
    
    def increment_version(self, version_type: str = "minor", description: str = "Version update") -> str:
        """
        Increment version and update changelog
        
        Args:
            version_type: 'major', 'minor', 'patch', or 'build'
            description: Description of changes for changelog
            
        Returns:
            New version string
        """
        info = self.get_version_info()
        
        # Increment version based on type
        if version_type == "major":
            info["major"] += 1
            info["minor"] = 0
            info["patch"] = 0
            info["build"] = 1
        elif version_type == "minor":
            info["minor"] += 1
            info["patch"] = 0
            info["build"] = 1
        elif version_type == "patch":
            info["patch"] += 1
            info["build"] = 1
        elif version_type == "build":
            info["build"] += 1
        else:
            raise ValueError(f"Invalid version type: {version_type}")
        
        # Update metadata
        info["last_updated"] = datetime.datetime.now().isoformat()
        info["description"] = description
        
        # Save version file
        with open(self.version_file, 'w') as f:
            json.dump(info, f, indent=2)
        
        # Update changelog
        self._update_changelog(info, description)
        
        new_version = self.get_version_string()
        print(f"✅ Version updated to {new_version}")
        return new_version
    
    def _update_changelog(self, version_info: Dict[str, Any], description: str):
        """Update CHANGES.md with new version entry"""
        version_string = f"v{version_info['major']}.{version_info['minor']}.{version_info['patch']}-build.{version_info['build']}"
        date_string = datetime.datetime.now().strftime("%Y-%m-%d")
        
        # Create new entry
        new_entry = f"""## {version_string} - {date_string}

### Changes
- {description}

### Technical Details
- Build: {version_info['build']}
- Updated: {version_info['last_updated']}

---

"""
        
        # Read existing changelog or create new one
        if os.path.exists(self.changes_file):
            with open(self.changes_file, 'r') as f:
                existing_content = f.read()
        else:
            existing_content = """# HP2BR Discord Bot - Change Log

This file tracks all changes and version updates for the HP2BR Discord Bot system.

---

"""
        
        # Insert new entry after the header
        lines = existing_content.split('\n')
        header_end = 0
        for i, line in enumerate(lines):
            if line.strip() == "---" and i > 0:
                header_end = i + 1
                break
        
        if header_end == 0:
            # No existing entries, add after header
            new_content = existing_content + new_entry
        else:
            # Insert new entry
            new_content = '\n'.join(lines[:header_end]) + '\n' + new_entry + '\n'.join(lines[header_end:])
        
        # Write updated changelog
        with open(self.changes_file, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Updated {self.changes_file}")

def main():
    """Command line interface for version management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="HP2BR Discord Bot Version Manager")
    parser.add_argument("action", choices=["show", "increment"], help="Action to perform")
    parser.add_argument("--type", choices=["major", "minor", "patch", "build"], 
                       default="minor", help="Version increment type")
    parser.add_argument("--description", "-d", default="Version update", 
                       help="Description of changes")
    
    args = parser.parse_args()
    
    vm = VersionManager()
    
    if args.action == "show":
        info = vm.get_version_info()
        version = vm.get_version_string()
        print(f"Current Version: {version}")
        print(f"Last Updated: {info.get('last_updated', 'Unknown')}")
        print(f"Description: {info.get('description', 'No description')}")
    
    elif args.action == "increment":
        new_version = vm.increment_version(args.type, args.description)
        print(f"New Version: {new_version}")

if __name__ == "__main__":
    main()
