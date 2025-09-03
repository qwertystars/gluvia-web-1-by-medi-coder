# tests/test_auth.py
import pytest
import random
from fastapi.testclient import TestClient

class TestAuthentication:
    """Test authentication functionality with automated user creation"""

    def test_user_registration_success(self, client, test_user_data):
        """Test successful user registration"""
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 200

        data = response.json()
        assert data["username"] == test_user_data["username"]
        assert data["email"] == test_user_data["email"]
        assert data["is_active"] is True
        assert "id" in data

    def test_user_registration_duplicate_username(self, client, test_user_data):
        """Test registration with duplicate username"""
        # Register first user
        client.post("/auth/register", json=test_user_data)

        # Try to register with same username
        response = client.post("/auth/register", json=test_user_data)
        assert response.status_code == 400
        assert "Username already registered" in response.json()["detail"]

    def test_user_registration_duplicate_email(self, client, test_user_data):
        """Test registration with duplicate email"""
        # Register first user
        client.post("/auth/register", json=test_user_data)

        # Create new user data with different username but same email
        duplicate_email_data = test_user_data.copy()
        duplicate_email_data["username"] = "different_username"

        response = client.post("/auth/register", json=duplicate_email_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    def test_user_login_success(self, client, test_user_data):
        """Test successful user login"""
        # Register user first
        client.post("/auth/register", json=test_user_data)

        # Login
        response = client.post(
            "/auth/login",
            data={"username": test_user_data["username"], "password": test_user_data["password"]}
        )
        assert response.status_code == 200

        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_user_login_invalid_credentials(self, client, test_user_data):
        """Test login with invalid credentials"""
        response = client.post(
            "/auth/login",
            data={"username": "nonexistent", "password": "wrongpassword"}
        )
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token"""
        response = client.get("/prescriptions/active")
        assert response.status_code == 401

    def test_protected_endpoint_with_token(self, client, authenticated_user):
        """Test accessing protected endpoint with valid token"""
        response = client.get("/prescriptions/active", headers=authenticated_user["headers"])
        # Should return 404 since no prescription exists, but not 401
        assert response.status_code == 404

    def test_delete_user_account(self, client, authenticated_user):
        """Test user account deletion"""
        response = client.delete("/auth/delete-account", headers=authenticated_user["headers"])
        assert response.status_code == 204

    def test_admin_delete_user(self, client, authenticated_user, user_manager):
        """Test admin user deletion endpoint"""
        # Create another user to delete
        user_data, user_info = user_manager.create_random_user(client, "victim")
        assert user_info is not None

        # Delete the user using admin endpoint
        response = client.delete(
            f"/auth/admin/delete-user/{user_info['id']}",
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 204

    def test_multiple_user_creation_and_cleanup(self, client, user_manager):
        """Test creating multiple random users and cleaning them up"""
        created_users = []

        # Create 5 random users
        for i in range(5):
            user_data, user_info = user_manager.create_random_user(client, f"batch_{i}")
            assert user_info is not None
            created_users.append((user_data, user_info))

        # Verify all users were created
        assert len(created_users) == 5

        # Test login for each user
        for user_data, user_info in created_users:
            response = client.post(
                "/auth/login",
                data={"username": user_data["username"], "password": user_data["password"]}
            )
            assert response.status_code == 200

    def test_concurrent_user_operations(self, client, user_manager):
        """Test handling multiple user operations"""
        # Create admin user
        admin_data = {
            "username": "admin_user",
            "email": "admin@test.com",
            "password": "AdminPass123!"
        }
        admin_response = client.post("/auth/register", json=admin_data)
        assert admin_response.status_code == 200

        # Login admin
        login_response = client.post(
            "/auth/login",
            data={"username": admin_data["username"], "password": admin_data["password"]}
        )
        admin_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Create multiple users simultaneously
        users = []
        for i in range(3):
            user_data, user_info = user_manager.create_random_user(client, f"concurrent_{i}")
            users.append((user_data, user_info))

        # Delete all users using admin endpoint
        for _, user_info in users:
            response = client.delete(
                f"/auth/admin/delete-user/{user_info['id']}",
                headers=admin_headers
            )
            assert response.status_code == 204
