#!/bin/bash

# Database Migration Deployment Script
# This script initializes the database and applies the soft-delete migration
# Safe to run multiple times - will not overwrite existing data

echo "🚀 Starting database migration deployment..."

# Navigate to API directory
cd "$(dirname "$0")/api" || {
    echo "❌ Error: Could not find API directory"
    exit 1
}

echo "📍 Current directory: $(pwd)"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed or not in PATH"
    exit 1
fi

# Check if virtual environment exists and activate it
if [ -d ".venv" ]; then
    echo "🔧 Activating virtual environment..."
    source .venv/bin/activate || {
        echo "❌ Error: Could not activate virtual environment"
        exit 1
    }
else
    echo "⚠️  Warning: No virtual environment found at .venv"
    echo "   Proceeding with system Python..."
fi

# Run the database initialization and migration
echo "🗄️  Initializing database and applying migrations..."
python3 init_database_with_soft_delete.py || {
    echo "❌ Error: Database initialization failed"
    exit 1
}

echo "✅ Database migration deployment completed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Start/restart the API server"
echo "   2. Start/restart the Discord bot"
echo "   3. Test with /leaderboard and /stats commands"
echo ""
echo "🎉 Deployment complete!"
