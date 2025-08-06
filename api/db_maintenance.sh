#!/bin/bash

# Exit on any error
set -e

DB_FILE="team_balance.db"

# Check if the database file exists
if [ ! -f "$DB_FILE" ]; then
    echo "Error: Database file '$DB_FILE' not found in the current directory."
    exit 1
fi

echo "Connecting to database: $DB_FILE"

echo "Deleting PENDING records from 'match_players' table..."
sqlite3 "$DB_FILE" "DELETE FROM match_players WHERE result = 'PENDING';"

echo "Deleting PENDING records from 'matches' table..."
sqlite3 "$DB_FILE" "DELETE FROM matches WHERE status = 'PENDING';"

echo "Cleanup of PENDING records complete."
