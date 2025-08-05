from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database.connection import create_tables
from routes import users, matches

# Create FastAPI app
app = FastAPI(
    title="Discord Team Balance Bot API",
    description="REST API for team balancing and match tracking",
    version="1.0.0"
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
    create_tables()

# Include routers
app.include_router(users.router)
app.include_router(matches.router)

@app.get("/")
def root():
    return {"message": "Discord Team Balance Bot API", "status": "running"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}