# test_auth.py
"""
Test script to verify the authentication system is working properly
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_registration():
    """Test user registration"""
    print("🔧 Testing user registration...")

    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpass123"
    }

    response = requests.post(f"{BASE_URL}/register", json=user_data)

    if response.status_code == 200:
        print("✅ User registration successful")
        print(f"   User: {response.json()}")
        return True
    else:
        print(f"❌ Registration failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return False

def test_login(username="admin", password="admin123"):
    """Test user login"""
    print(f"🔐 Testing login with {username}...")

    login_data = {
        "username": username,
        "password": password
    }

    response = requests.post(f"{BASE_URL}/login", data=login_data)

    if response.status_code == 200:
        token_data = response.json()
        print("✅ Login successful")
        print(f"   Token: {token_data['access_token'][:50]}...")
        return token_data['access_token']
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return None

def test_protected_endpoint(token):
    """Test accessing protected upload endpoint"""
    print("🔒 Testing protected endpoint...")

    headers = {"Authorization": f"Bearer {token}"}

    # Test without file (should get validation error, not auth error)
    response = requests.post(f"{BASE_URL}/upload", headers=headers)

    if response.status_code == 422:  # Validation error (missing file)
        print("✅ Authentication successful (validation error expected)")
        return True
    elif response.status_code == 401:
        print("❌ Authentication failed")
        print(f"   Error: {response.text}")
        return False
    else:
        print(f"🤔 Unexpected response: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def main():
    print("🚀 Testing Gluvia Authentication System")
    print("=" * 50)

    # Test admin login
    admin_token = test_login("admin", "admin123")
    if admin_token:
        test_protected_endpoint(admin_token)

    print("\n" + "-" * 30)

    # Test user registration
    if test_registration():
        # Test login with new user
        user_token = test_login("testuser", "testpass123")
        if user_token:
            test_protected_endpoint(user_token)

    print("\n🎉 Authentication tests completed!")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on http://127.0.0.1:8000")
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
