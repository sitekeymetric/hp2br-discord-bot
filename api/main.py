from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.connection import create_tables
from routes import users, matches
from utils.version import get_version_string, get_version_dict, print_startup_version

# Get dynamic version
version_info = get_version_dict()

# Create FastAPI app
app = FastAPI(
    title="Discord Team Balance Bot API",
    description="REST API for team balancing and match tracking",
    version=version_info["version"]
)

# CORS middleware for Discord bot integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables on startup
@app.on_event("startup")
def startup_event():
    print_startup_version()  # Display version info at startup
    create_tables()

# Include routers
app.include_router(users.router)
app.include_router(matches.router)

# Advanced Rating System v3.0.0
from routes import advanced_matches
app.include_router(advanced_matches.router)

# OpenSkill Parallel Rating System
from routes import openskill_routes
app.include_router(openskill_routes.router)

# Team Composition Analysis
from routes import team_composition_routes
app.include_router(team_composition_routes.router)

@app.get("/")
def root():
    return {
        "message": "Discord Team Balance Bot API", 
        "status": "running",
        "version": get_version_string()
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "version": get_version_string(),
        "service": "HP2BR Discord Bot API"
    }

@app.get("/version")
def get_version():
    """Get API version information"""
    return get_version_dict()