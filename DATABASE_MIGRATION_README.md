# Database Migration Deployment Guide

This guide explains how to deploy the soft-delete database migration to fix `/leaderboard` and `/stats` command errors.

## Problem Fixed

- **Error**: `no such column: users.deleted_at`
- **Commands affected**: `/leaderboard`, `/stats`, `/delete_account`
- **Root cause**: Missing `deleted_at` column in production database

## Quick Deployment (Recommended)

Run the automated deployment script:

```bash
./deploy_database_migration.sh
```

This script will:
1. Navigate to the API directory
2. Activate the virtual environment (if present)
3. Create database tables (if missing)
4. Add the `deleted_at` column (if missing)
5. Verify the migration was successful

## Manual Deployment

If you prefer to run the migration manually:

```bash
cd api
source .venv/bin/activate  # If using virtual environment
python3 init_database_with_soft_delete.py
```

## Verification

After running the migration, verify it worked:

```bash
cd api
python3 -c "
import sqlite3
conn = sqlite3.connect('team_balance.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(users)')
columns = [row[1] for row in cursor.fetchall()]
print('✅ deleted_at column present:' if 'deleted_at' in columns else '❌ deleted_at column missing:', 'deleted_at' in columns)
conn.close()
"
```

## What the Migration Does

### Database Schema Changes

Adds a new column to the `users` table:

```sql
ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP NULL;
```

### Soft Delete System

- **Active users**: `deleted_at` is `NULL`
- **Deleted users**: `deleted_at` contains deletion timestamp
- **Match history**: Preserved for deleted users
- **Queries**: Automatically filter out deleted users

### Commands Fixed

- ✅ `/leaderboard` - Shows only active users
- ✅ `/stats` - Works with soft-delete filtering  
- ✅ `/delete_account` - Soft-deletes without foreign key errors
- ✅ `/register` - Creates users normally
- ✅ `/create_teams` - Auto-registration works

## Safety Notes

- **Safe to run multiple times**: Script checks if migration is already applied
- **No data loss**: Existing user data is preserved
- **Backward compatible**: Old functionality continues to work
- **Rollback not needed**: Migration only adds a column, doesn't modify existing data

## Troubleshooting

### Permission Errors
```bash
chmod +x deploy_database_migration.sh
```

### Python Not Found
```bash
# Install Python 3
sudo apt update && sudo apt install python3

# Or use different Python command
python init_database_with_soft_delete.py
```

### Virtual Environment Issues
```bash
# Skip virtual environment activation
cd api
python3 init_database_with_soft_delete.py
```

### Database File Not Found
The script will create the database file if it doesn't exist. Make sure you're in the correct directory.

## Post-Migration

After successful migration:

1. **Restart API server**: `systemctl restart hp2br-api` (or your restart method)
2. **Restart Discord bot**: `systemctl restart hp2br-bot` (or your restart method)
3. **Test commands**: Try `/leaderboard` and `/stats` in Discord
4. **Monitor logs**: Check for any remaining errors

## Support

If you encounter issues:

1. Check the migration logs for specific error messages
2. Verify database file permissions
3. Ensure Python dependencies are installed
4. Check that the API server is using the correct database file (`team_balance.db`)

The migration adds robust soft-delete functionality while preserving all existing data and functionality.
