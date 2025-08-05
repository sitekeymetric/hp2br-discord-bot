import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base
from database.connection import get_db
from main import app

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def test_create_user():
    response = client.post("/users/", json={
        "guild_id": 123456789,
        "user_id": 987654321,
        "username": "TestUser",
        "region_code": "NA"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "TestUser"
    assert data["region_code"] == "NA"
    assert data["rating_mu"] == 1500.0
    assert data["rating_sigma"] == 350.0

def test_create_duplicate_user():
    # Create user first
    client.post("/users/", json={
        "guild_id": 123456789,
        "user_id": 987654322,
        "username": "TestUser2"
    })
    
    # Try to create same user again
    response = client.post("/users/", json={
        "guild_id": 123456789,
        "user_id": 987654322,
        "username": "TestUser2"
    })
    assert response.status_code == 400
    assert "User already exists" in response.json()["detail"]

def test_get_user():
    # Create user first
    client.post("/users/", json={
        "guild_id": 123456789,
        "user_id": 987654323,
        "username": "TestUser3"
    })
    
    # Get user
    response = client.get("/users/123456789/987654323")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == 987654323
    assert data["username"] == "TestUser3"

def test_get_nonexistent_user():
    response = client.get("/users/123456789/999999999")
    assert response.status_code == 404
    assert "User not found" in response.json()["detail"]

def test_update_user():
    # Create user first
    client.post("/users/", json={
        "guild_id": 123456789,
        "user_id": 987654324,
        "username": "TestUser4"
    })
    
    # Update user
    response = client.put("/users/123456789/987654324", json={
        "username": "UpdatedUser4",
        "region_code": "EU"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "UpdatedUser4"
    assert data["region_code"] == "EU"

def test_get_guild_users():
    # Create multiple users in the same guild
    client.post("/users/", json={
        "guild_id": 555555555,
        "user_id": 111111111,
        "username": "GuildUser1"
    })
    client.post("/users/", json={
        "guild_id": 555555555,
        "user_id": 111111112,
        "username": "GuildUser2"
    })
    
    # Get guild users
    response = client.get("/users/555555555")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    usernames = [user["username"] for user in data]
    assert "GuildUser1" in usernames
    assert "GuildUser2" in usernames

def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"