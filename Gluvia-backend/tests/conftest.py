# tests/conftest.py
import pytest
import os
import sys
import random
import string
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from typing import Generator, Dict, Any

# Add the parent directory to the Python path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import Base, get_db
from auth import create_user, delete_user

# Test database URL - use a separate test database
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite:///./test_gluvia.db")

# Create test engine
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in TEST_DATABASE_URL else {}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session(test_db):
    """Create a database session for testing"""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db_session):
    """Create a test client with database override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

def generate_random_string(length: int = 8) -> str:
    """Generate random string for testing"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_test_user_data() -> Dict[str, str]:
    """Generate random test user data"""
    username = f"testuser_{generate_random_string()}"
    email = f"test_{generate_random_string()}@example.com"
    password = f"TestPass{generate_random_string(4)}!"
    return {
        "username": username,
        "email": email,
        "password": password
    }

@pytest.fixture
def test_user_data():
    """Generate test user data"""
    return generate_test_user_data()

@pytest.fixture
def authenticated_user(client, db_session, test_user_data):
    """Create and authenticate a test user"""
    # Register user
    response = client.post("/auth/register", json=test_user_data)
    assert response.status_code == 200
    user_data = response.json()

    # Login user
    login_response = client.post(
        "/auth/login",
        data={"username": test_user_data["username"], "password": test_user_data["password"]}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()

    # Return user info and auth headers
    return {
        "user_data": user_data,
        "token": token_data["access_token"],
        "headers": {"Authorization": f"Bearer {token_data['access_token']}"},
        "raw_user_data": test_user_data
    }

@pytest.fixture
def sample_prescription_data():
    """Sample prescription data for testing"""
    return {
        "breakfast": {"insulin": "Humalog", "dose": 10, "type": "rapid", "onset": 15},
        "mid_morning": {"insulin": "Regular", "dose": 8, "type": "short", "onset": 30},
        "lunch": {"insulin": "Novolin N", "dose": 15, "type": "intermediate", "onset": 90},
        "dinner": {"insulin": "Lantus", "dose": 20, "type": "long", "onset": 60},
        "snack": {"insulin": "Mix 70/30", "dose": 12, "type": "mixed", "onset": 30}
    }

@pytest.fixture
def sample_questionnaire_data():
    """Sample questionnaire data for testing"""
    return {
        "responses": {
            "breakfast": {
                "taken": True,
                "actual_dose": 10,
                "meal_time": "08:00"
            },
            "lunch": {
                "taken": False,
                "meal_time": "13:30"
            },
            "dinner": {
                "taken": True,
                "actual_dose": 22,  # Slightly higher dose for testing
                "meal_time": "19:00"
            }
        }
    }

class TestUserManager:
    """Utility class to manage test users"""

    def __init__(self):
        self.created_users = []

    def create_random_user(self, client, prefix="testuser"):
        """Create a random user and track it"""
        user_data = generate_test_user_data()
        user_data["username"] = f"{prefix}_{generate_random_string()}"

        response = client.post("/auth/register", json=user_data)
        if response.status_code == 200:
            user_info = response.json()
            self.created_users.append(user_info["id"])
            return user_data, user_info
        return None, None

    def cleanup_users(self, client, headers):
        """Delete all created test users"""
        for user_id in self.created_users:
            try:
                client.delete(f"/auth/admin/delete-user/{user_id}", headers=headers)
            except:
                pass  # Ignore errors during cleanup
        self.created_users.clear()

@pytest.fixture
def user_manager():
    """Test user manager fixture"""
    return TestUserManager()
