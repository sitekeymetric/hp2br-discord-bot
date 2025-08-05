#!/usr/bin/env python3
"""
Version utilities for HP2BR Discord Bot API
"""

import os
import json
import sys
from typing import Dict, Any

def get_version_info() -> Dict[str, Any]:
    """Get version information from root VERSION.json"""
    # Get the root directory (parent of api directory)
    api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root_dir = os.path.dirname(api_dir)
    version_file = os.path.join(root_dir, "VERSION.json")
    
    try:
        with open(version_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "major": 1,
            "minor": 0,
            "patch": 0,
            "build": 1,
            "last_updated": "Unknown",
            "description": "Version file not found"
        }

def get_version_string() -> str:
    """Get formatted version string"""
    info = get_version_info()
    return f"v{info['major']}.{info['minor']}.{info['patch']}-build.{info['build']}"

def get_version_dict() -> Dict[str, Any]:
    """Get version information as dictionary for API responses"""
    info = get_version_info()
    return {
        "version": get_version_string(),
        "major": info["major"],
        "minor": info["minor"],
        "patch": info["patch"],
        "build": info["build"],
        "last_updated": info.get("last_updated", "Unknown"),
        "description": info.get("description", "No description")
    }

def print_startup_version():
    """Print version information at API startup"""
    info = get_version_info()
    version_string = get_version_string()
    
    print("=" * 60)
    print(f"🚀 HP2BR Discord Bot API {version_string}")
    print(f"📅 Last Updated: {info.get('last_updated', 'Unknown')[:19]}")
    print(f"📝 Description: {info.get('description', 'No description')}")
    print("=" * 60)
