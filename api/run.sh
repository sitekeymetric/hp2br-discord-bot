#!/bin/bash

# Exit on any error
set -e

echo "Starting Discord Bot API..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "VENV does not exist. please go to api folder and run 'uv venv'"
    # python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
uv pip install --upgrade pip
uv pip install --requirements requirements.txt

# Set environment variables if .env file exists
if [ -f ".env" ]; then
    echo "Loading environment variables from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start the API server
echo "Starting FastAPI server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000
