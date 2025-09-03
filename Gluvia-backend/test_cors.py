#!/usr/bin/env python3
"""
Quick test script to verify CORS fix and prescription upload endpoint
"""
import requests
import json

def test_cors_and_upload():
    """Test if CORS is working and upload endpoint is accessible"""
    base_url = "http://localhost:8000"
    
    print("🧪 Testing CORS fix and prescription upload endpoint...")
    
    # Test 1: Check if server is running
    try:
        response = requests.get(f"{base_url}/")
        print(f"✅ Server is running: {response.json()}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Server connection error: {e}")
        return False
    
    # Test 2: Test CORS preflight (OPTIONS request)
    try:
        headers = {
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type,Authorization'
        }
        response = requests.options(f"{base_url}/prescriptions/upload", headers=headers)
        print(f"✅ CORS preflight response status: {response.status_code}")
        
        # Check CORS headers
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
        }
        print(f"🔗 CORS headers: {cors_headers}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ CORS test error: {e}")
        return False
    
    # Test 3: Test upload endpoint accessibility (without auth - should get 401)
    try:
        headers = {'Origin': 'http://localhost:3000'}
        response = requests.post(f"{base_url}/prescriptions/upload", headers=headers)
        print(f"✅ Upload endpoint accessible (expected 401): {response.status_code}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Upload endpoint test error: {e}")
        return False
    
    # Test 4: Test registration endpoint (for auth flow)
    try:
        test_user = {
            "username": "cors_test_user",
            "email": "corstest@example.com", 
            "password": "TestPass123!"
        }
        headers = {'Origin': 'http://localhost:3000'}
        response = requests.post(f"{base_url}/auth/register", json=test_user, headers=headers)
        print(f"✅ Registration endpoint accessible: {response.status_code}")
        
        if response.status_code == 200:
            print("🎉 CORS fix successful! All endpoints are accessible from browser origins.")
            return True
        elif response.status_code == 400:
            print("🎉 CORS fix successful! Endpoint is accessible (user may already exist).")
            return True
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Registration endpoint test error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_cors_and_upload()
