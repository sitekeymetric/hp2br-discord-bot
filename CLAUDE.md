# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Discord team balancing bot project for creating balanced teams in competitive gameplay. The system uses skill ratings (Glicko-2), region balancing, and comprehensive match tracking with database persistence.

## Project Status

This is currently in the planning phase. The repository contains detailed project documentation but no implementation code yet.

## Architecture

The planned architecture follows a multi-service approach:

### Core Components
- **Discord Bot** (`bot/`): Discord.py-based bot with cogs for modular functionality
- **REST API** (`api/`): FastAPI/Flask service for database operations
- **Database** (`database/`): SQLite3 with SQLAlchemy ORM
- **Testing** (`tests/`): pytest-based testing framework

### Key Systems
1. **Skill Rating System**: Glicko-2 algorithm with μ (mu), σ (sigma), and τ (tau) parameters
2. **Team Balancing**: Algorithm that minimizes team skill variance while considering region distribution
3. **Voice Management**: Automated voice channel creation and player movement
4. **Match Tracking**: Complete match history with rating updates

## Planned Technology Stack

- **Discord Bot**: discord.py 2.3+
- **API Framework**: FastAPI or Flask-RESTful
- **Database**: SQLite3 with SQLAlchemy ORM
- **Testing**: pytest
- **Code Style**: Black formatter, flake8 linting
- **Task Queue**: Optional Redis for background tasks

## Development Phases

The project is planned in 7 phases:
1. Database & API Foundation (Critical)
2. Core Discord Bot Framework (Critical)
3. Team Balancing Algorithm (High Priority)
4. User Interface & Interaction (High Priority)
5. Voice Channel Management (High Priority)
6. Match Recording & Results (Medium Priority)
7. Advanced Features & Polish (Low Priority)

## Key Database Schema

- **Users**: guild_id, user_id, username, region_code, rating_mu, rating_sigma, rating_tau
- **Matches**: match_id, guild_id, match_type, start_time, end_time, status
- **Match_Teams**: team_id, match_id, team_name, avg_rating_mu, combined_rating_sigma
- **Match_Players**: match_id, team_id, user_id, rating changes (before/after)
- **Match_Results**: match_id, winning_team_id, result_type

## Glicko-2 Rating System

The bot uses the Glicko-2 rating system with:
- **μ (mu)**: Player's estimated skill level (initial: 1500)
- **σ (sigma)**: Rating deviation/uncertainty (initial: 350)
- **τ (tau)**: Volatility measure for rating changes
- **Team Rating**: Average μ with combined σ for uncertainty
- **Rating Decay**: Inactive players have increased σ over time

## Development Standards

- Guild-based data isolation for multi-server support
- Comprehensive error handling and logging
- 80%+ test coverage target
- Input validation and permission checks
- Environment variable configuration for tokens/secrets

## Current State

The repository contains comprehensive planning documentation but no implementation code. When beginning development, start with Phase 1 (Database & API Foundation) as outlined in PROJECT_PLAN.md.