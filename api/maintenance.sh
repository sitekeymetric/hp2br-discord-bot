#!/bin/bash
# HP2BR Discord Bot - Database Maintenance Script
# Regular cleanup of old pending matches

echo "🧹 HP2BR Bot Database Maintenance"
echo "=================================="

# Change to API directory
cd "$(dirname "$0")"

# Show current status
echo "📊 Current Database Status:"
python3 cleanup_pending_matches.py --status
echo

# Run cleanup with default 1-day setting
echo "🔄 Running automated cleanup (1 day old matches)..."
python3 cleanup_pending_matches.py --live

echo
echo "✅ Maintenance completed!"
echo "📊 Final Status:"
python3 cleanup_pending_matches.py --status
