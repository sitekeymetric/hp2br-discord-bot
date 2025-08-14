#!/bin/bash

# Deploy Advanced Rating System v3.0.0 Migration
# This script safely applies the database migration for the new rating system

set -e  # Exit on any error

echo "🚀 Deploying Advanced Rating System v3.0.0 Migration"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "team_balance.db" ]; then
    echo "❌ Error: team_balance.db not found in current directory"
    echo "Please run this script from the project root directory"
    exit 1
fi

# Backup the database
echo "📦 Creating database backup..."
BACKUP_FILE="team_balance_backup_$(date +%Y%m%d_%H%M%S).db"
cp team_balance.db "$BACKUP_FILE"
echo "✅ Database backed up to: $BACKUP_FILE"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is required but not installed"
    exit 1
fi

# Run the migration
echo "🔄 Running Advanced Rating System migration..."
cd api
python3 database/migrations/add_advanced_rating_tracking.py

if [ $? -eq 0 ]; then
    echo "✅ Migration completed successfully!"
    echo ""
    echo "📊 Advanced Rating System v3.0.0 is now active with:"
    echo "   • Opponent strength consideration"
    echo "   • Curved scaling for elite players"
    echo "   • Enhanced penalty tiers (up to -345 for 30th place)"
    echo "   • Detailed rating change breakdowns"
    echo ""
    echo "🔄 Please restart your API server and Discord bot to use the new system"
    echo ""
    echo "Commands to restart:"
    echo "   API: cd api && uvicorn main:app --reload"
    echo "   Bot: cd bot && python main.py"
else
    echo "❌ Migration failed!"
    echo "🔄 Restoring database from backup..."
    cd ..
    cp "$BACKUP_FILE" team_balance.db
    echo "✅ Database restored from backup"
    exit 1
fi

cd ..
echo "🎉 Advanced Rating System v3.0.0 deployment complete!"
