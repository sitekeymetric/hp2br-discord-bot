#!/bin/bash

# Exit on any error
set -e

echo "Starting Discord Bot..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Please copy .env.example to .env and configure your Discord bot token."
    echo "You can do this by running: cp .env.example .env"
    exit 1
fi

# Load environment variables
echo "Loading environment variables from .env file..."
export $(cat .env | grep -v '^#' | xargs)

# Start the Discord bot
echo "Starting Discord bot..."
python main.py
