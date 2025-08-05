# HP2BR Discord Bot - Versioning System

This document explains the versioning system implemented for the HP2BR Discord Bot.

## Version Format

The bot uses semantic versioning with build numbers:
```
v{major}.{minor}.{patch}-build.{build}
```

Example: `v1.2.3-build.45`

## Version Components

- **Major**: Breaking changes, major feature additions
- **Minor**: New features, significant improvements (auto-incremented for most updates)
- **Patch**: Bug fixes, small improvements
- **Build**: Incremented with every version change

## How to Update Versions

### Using the Update Script (Recommended)

```bash
# Update minor version (most common)
python3 update_version.py minor "Description of changes"

# Update patch version
python3 update_version.py patch "Fixed bug in team balancing"

# Update major version
python3 update_version.py major "Complete rewrite of voice system"

# Update build only
python3 update_version.py build "Small configuration change"
```

### Manual Version Management

```bash
# Show current version
python3 version.py show

# Increment version manually
python3 version.py increment --type minor --description "Your changes"
```

## What Happens When You Update

1. **VERSION.json** is updated with new version numbers
2. **CHANGES.md** is automatically updated with a new entry
3. Both bot and API will display the new version on startup
4. Version appears in `/help` command and admin statistics

## Version Display Locations

### Bot
- Startup console output
- `/help` command embed
- `/guild_stats` admin command
- Error messages and logs

### API
- Startup console output
- `/version` endpoint
- `/health` endpoint
- Root endpoint (`/`)
- FastAPI documentation

## File Structure

```
/
├── VERSION.json          # Central version storage
├── CHANGES.md           # Automatic changelog
├── version.py           # Version management class
├── update_version.py    # Easy update script
├── bot/utils/version.py # Bot version utilities
└── api/utils/version.py # API version utilities
```

## Best Practices

1. **Always use descriptive messages** when updating versions
2. **Use minor updates** for most changes (new features, improvements)
3. **Use patch updates** for bug fixes only
4. **Use major updates** sparingly for breaking changes
5. **Update version after every significant change**

## Examples

```bash
# Adding new command
python3 update_version.py minor "Added /new_command for user management"

# Fixing a bug
python3 update_version.py patch "Fixed team balancing algorithm edge case"

# Major rewrite
python3 update_version.py major "Rewrote voice channel system with new architecture"

# Small config change
python3 update_version.py build "Updated default timeout values"
```

## Automatic Features

- ✅ Automatic changelog generation
- ✅ Timestamp tracking
- ✅ Version display in bot and API
- ✅ Consistent versioning across all components
- ✅ Easy command-line interface

## Integration

The version system is integrated into:
- Bot startup sequence
- API startup sequence
- Discord command responses
- Health check endpoints
- Error reporting
- Admin statistics

This ensures users and administrators always know which version is running.
