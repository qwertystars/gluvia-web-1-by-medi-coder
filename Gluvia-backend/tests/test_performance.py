# tests/test_performance.py
import pytest
import time
import threading
import concurrent.futures
from datetime import datetime
from fastapi.testclient import TestClient

class TestPerformance:
    """Test performance and concurrency of the application"""

    def test_single_user_response_time(self, client, authenticated_user, sample_prescription_data):
        """Test response time for single user operations"""
        # Create prescription
        prescription_payload = {"prescription_data": sample_prescription_data}

        start_time = time.time()
        response = client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])
        create_time = time.time() - start_time

        assert response.status_code == 200
        assert create_time < 2.0  # Should complete within 2 seconds

        # Get active prescription
        start_time = time.time()
        response = client.get("/prescriptions/active", headers=authenticated_user["headers"])
        get_time = time.time() - start_time

        assert response.status_code == 200
        assert get_time < 1.0  # Should complete within 1 second

        # Get status
        start_time = time.time()
        response = client.get("/prescriptions/status", headers=authenticated_user["headers"])
        status_time = time.time() - start_time

        assert response.status_code == 200
        assert status_time < 1.5  # Should complete within 1.5 seconds

    def test_concurrent_user_registrations(self, client, user_manager):
        """Test concurrent user registrations"""
        def register_user(index):
            user_data = {
                "username": f"concurrent_user_{index}_{int(time.time())}",
                "email": f"concurrent_{index}_{int(time.time())}@test.com",
                "password": f"TestPass{index}!"
            }
            response = client.post("/auth/register", json=user_data)
            return response.status_code == 200, user_data

        # Run 10 concurrent registrations
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(register_user, i) for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All registrations should succeed
        success_count = sum(1 for success, _ in results if success)
        assert success_count == 10

    def test_concurrent_logins(self, client, user_manager):
        """Test concurrent user logins"""
        # First create users
        users = []
        for i in range(5):
            user_data = {
                "username": f"login_user_{i}_{int(time.time())}",
                "email": f"login_{i}_{int(time.time())}@test.com",
                "password": f"LoginPass{i}!"
            }
            response = client.post("/auth/register", json=user_data)
            assert response.status_code == 200
            users.append(user_data)

        def login_user(user_data):
            response = client.post(
                "/auth/login",
                data={"username": user_data["username"], "password": user_data["password"]}
            )
            return response.status_code == 200

        # Run concurrent logins
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(login_user, user) for user in users]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All logins should succeed
        success_count = sum(results)
        assert success_count == 5

    def test_concurrent_prescription_creation(self, client, sample_prescription_data):
        """Test concurrent prescription creation by different users"""
        # Create users first
        users = []
        for i in range(3):
            user_data = {
                "username": f"prescription_user_{i}_{int(time.time())}",
                "email": f"prescription_{i}_{int(time.time())}@test.com",
                "password": f"PrescPass{i}!"
            }
            # Register user
            client.post("/auth/register", json=user_data)

            # Login user
            login_response = client.post(
                "/auth/login",
                data={"username": user_data["username"], "password": user_data["password"]}
            )
            token = login_response.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            users.append((user_data, headers))

        def create_prescription(user_headers):
            prescription_payload = {
                "prescription_data": sample_prescription_data,
                "doctor_name": f"Dr. Test {int(time.time())}"
            }
            response = client.post("/prescriptions/", json=prescription_payload, headers=user_headers)
            return response.status_code == 200

        # Run concurrent prescription creations
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_prescription, headers) for _, headers in users]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All prescription creations should succeed
        success_count = sum(results)
        assert success_count == 3

    def test_questionnaire_processing_performance(self, client, authenticated_user, sample_prescription_data):
        """Test questionnaire processing performance"""
        # Create prescription
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])

        # Create complex questionnaire data
        questionnaire_data = {
            "responses": {
                "breakfast": {"taken": True, "actual_dose": 10, "meal_time": "08:00"},
                "mid_morning": {"taken": True, "actual_dose": 8, "meal_time": "10:30"},
                "lunch": {"taken": True, "actual_dose": 15, "meal_time": "13:00"},
                "dinner": {"taken": True, "actual_dose": 20, "meal_time": "19:00"},
                "snack": {"taken": False, "meal_time": "16:00"}
            }
        }

        # Test processing time
        start_time = time.time()
        response = client.post(
            "/prescriptions/daily-questionnaire",
            json=questionnaire_data,
            headers=authenticated_user["headers"]
        )
        processing_time = time.time() - start_time

        assert response.status_code == 200
        assert processing_time < 3.0  # Should complete within 3 seconds

    def test_multiple_questionnaire_submissions(self, client, authenticated_user, sample_prescription_data):
        """Test multiple questionnaire submissions in sequence"""
        # Create prescription
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])

        # Submit multiple questionnaires
        processing_times = []
        for i in range(5):
            questionnaire_data = {
                "responses": {
                    "breakfast": {"taken": True, "actual_dose": 10 + i, "meal_time": "08:00"},
                    "lunch": {"taken": True, "actual_dose": 15 + i, "meal_time": "13:00"}
                }
            }

            start_time = time.time()
            response = client.post(
                "/prescriptions/daily-questionnaire",
                json=questionnaire_data,
                headers=authenticated_user["headers"]
            )
            processing_time = time.time() - start_time
            processing_times.append(processing_time)

            assert response.status_code == 200

        # Average processing time should be reasonable
        avg_time = sum(processing_times) / len(processing_times)
        assert avg_time < 2.0  # Average should be under 2 seconds

    def test_dose_history_retrieval_performance(self, client, authenticated_user, sample_prescription_data):
        """Test dose history retrieval performance"""
        # Create prescription
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])

        # Create some dose history by submitting questionnaires
        for i in range(3):
            questionnaire_data = {
                "responses": {
                    "breakfast": {"taken": True, "actual_dose": 10, "meal_time": "08:00"},
                    "lunch": {"taken": True, "actual_dose": 15, "meal_time": "13:00"}
                }
            }
            client.post(
                "/prescriptions/daily-questionnaire",
                json=questionnaire_data,
                headers=authenticated_user["headers"]
            )

        # Test dose history retrieval time
        start_time = time.time()
        response = client.get("/prescriptions/doses/history?days=7", headers=authenticated_user["headers"])
        retrieval_time = time.time() - start_time

        assert response.status_code == 200
        assert retrieval_time < 1.0  # Should complete within 1 second

    def test_memory_usage_stability(self, client, authenticated_user, sample_prescription_data):
        """Test that repeated operations don't cause memory leaks"""
        import psutil
        import os

        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss

        # Create prescription
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])

        # Perform many operations
        for i in range(20):
            # Get status
            client.get("/prescriptions/status", headers=authenticated_user["headers"])

            # Get template
            client.get("/prescriptions/template", headers=authenticated_user["headers"])

            # Process questionnaire
            questionnaire_data = {
                "responses": {
                    "breakfast": {"taken": True, "actual_dose": 10, "meal_time": "08:00"}
                }
            }
            client.post(
                "/prescriptions/daily-questionnaire",
                json=questionnaire_data,
                headers=authenticated_user["headers"]
            )

        # Check final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024  # 50MB limit

    def test_concurrent_questionnaire_processing(self, client, sample_prescription_data):
        """Test concurrent questionnaire processing by multiple users"""
        # Create multiple users with prescriptions
        users = []
        for i in range(3):
            user_data = {
                "username": f"questionnaire_user_{i}_{int(time.time())}",
                "email": f"questionnaire_{i}_{int(time.time())}@test.com",
                "password": f"QuestPass{i}!"
            }
            # Register and login
            client.post("/auth/register", json=user_data)
            login_response = client.post(
                "/auth/login",
                data={"username": user_data["username"], "password": user_data["password"]}
            )
            headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

            # Create prescription
            prescription_payload = {"prescription_data": sample_prescription_data}
            client.post("/prescriptions/", json=prescription_payload, headers=headers)

            users.append(headers)

        def process_questionnaire(headers):
            questionnaire_data = {
                "responses": {
                    "breakfast": {"taken": True, "actual_dose": 10, "meal_time": "08:00"},
                    "lunch": {"taken": True, "actual_dose": 15, "meal_time": "13:00"}
                }
            }
            response = client.post(
                "/prescriptions/daily-questionnaire",
                json=questionnaire_data,
                headers=headers
            )
            return response.status_code == 200

        # Run concurrent questionnaire processing
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_questionnaire, headers) for headers in users]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All questionnaire processing should succeed
        success_count = sum(results)
        assert success_count == 3

    def test_load_spike_handling(self, client, authenticated_user, sample_prescription_data):
        """Test application behavior under sudden load spike"""
        # Create prescription
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])

        def make_request():
            response = client.get("/prescriptions/status", headers=authenticated_user["headers"])
            return response.status_code == 200

        # Simulate sudden spike with 20 concurrent requests
        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        total_time = time.time() - start_time

        # Most requests should succeed (allow some failures under extreme load)
        success_count = sum(results)
        assert success_count >= 18  # At least 90% success rate

        # Should handle the load spike reasonably quickly
        assert total_time < 10.0  # Should complete within 10 seconds
