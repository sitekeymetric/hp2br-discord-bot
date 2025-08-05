#!/bin/bash

# Exit on any error
set -e

# Function to display usage
usage() {
    echo "Usage: $0 [api|bot|both]"
    echo "  api  - Start only the FastAPI server"
    echo "  bot  - Start only the Discord bot"
    echo "  both - Start both API and bot (default)"
    exit 1
}

# Function to start API
start_api() {
    echo "Starting API server..."
    cd api
    ./run.sh &
    API_PID=$!
    cd ..
    echo "API started with PID: $API_PID"
}

# Function to start bot
start_bot() {
    echo "Starting Discord bot..."
    cd bot
    ./run.sh &
    BOT_PID=$!
    cd ..
    echo "Bot started with PID: $BOT_PID"
}

# Function to cleanup processes on exit
cleanup() {
    echo "Shutting down..."
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null || true
        echo "API server stopped"
    fi
    if [ ! -z "$BOT_PID" ]; then
        kill $BOT_PID 2>/dev/null || true
        echo "Discord bot stopped"
    fi
    exit 0
}

# Set up signal handlers
trap cleanup SIGINT SIGTERM

# Parse command line arguments
MODE=${1:-both}

case $MODE in
    api)
        start_api
        wait $API_PID
        ;;
    bot)
        start_bot
        wait $BOT_PID
        ;;
    both)
        start_api
        sleep 2  # Give API time to start
        start_bot
        
        # Wait for both processes
        wait $API_PID $BOT_PID
        ;;
    *)
        usage
        ;;
esac
