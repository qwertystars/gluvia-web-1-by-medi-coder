# test_integration_auth.py
"""
Integration tests for authentication system using pytest and test client
"""

import pytest
import time
from datetime import datetime
from fastapi.testclient import TestClient

class TestIntegrationAuth:
    """Integration tests for complete authentication and prescription workflows"""

    def test_complete_user_journey(self, client, sample_prescription_data):
        """Test complete user journey from registration to prescription management"""
        # Step 1: Register user
        user_data = {
            "username": f"integration_user_{int(time.time())}",
            "email": f"integration_{int(time.time())}@test.com",
            "password": "IntegrationPass123!"
        }

        register_response = client.post("/auth/register", json=user_data)
        assert register_response.status_code == 200
        user_info = register_response.json()
        assert user_info["username"] == user_data["username"]
        assert user_info["email"] == user_data["email"]

        # Step 2: Login user
        login_response = client.post(
            "/auth/login",
            data={"username": user_data["username"], "password": user_data["password"]}
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data

        headers = {"Authorization": f"Bearer {token_data['access_token']}"}

        # Step 3: Get profile
        profile_response = client.get("/auth/profile", headers=headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["username"] == user_data["username"]

        # Step 4: Try to get active prescription (should fail - none exists)
        prescription_response = client.get("/prescriptions/active", headers=headers)
        assert prescription_response.status_code == 404

        # Step 5: Create prescription
        prescription_payload = {
            "prescription_data": sample_prescription_data,
            "doctor_name": "Dr. Integration Test",
            "doctor_phone": "+1234567890",
            "clinic_name": "Integration Clinic"
        }

        create_prescription_response = client.post(
            "/prescriptions/",
            json=prescription_payload,
            headers=headers
        )
        assert create_prescription_response.status_code == 200
        prescription_info = create_prescription_response.json()
        assert prescription_info["doctor_name"] == "Dr. Integration Test"
        assert prescription_info["is_active"] is True

        # Step 6: Get active prescription (should succeed now)
        active_prescription_response = client.get("/prescriptions/active", headers=headers)
        assert active_prescription_response.status_code == 200
        active_prescription = active_prescription_response.json()
        assert active_prescription["id"] == prescription_info["id"]

        # Step 7: Get comprehensive status
        status_response = client.get("/prescriptions/status", headers=headers)
        assert status_response.status_code == 200
        status_data = status_response.json()
        assert "current_time" in status_data
        assert "current_zone" in status_data
        assert "prescription_data" in status_data

        # Step 8: Get questionnaire template
        template_response = client.get("/prescriptions/template", headers=headers)
        assert template_response.status_code == 200
        template_data = template_response.json()
        assert "template" in template_data
        assert "instructions" in template_data

        # Step 9: Process questionnaire
        questionnaire_data = {
            "responses": {
                "breakfast": {
                    "taken": True,
                    "actual_dose": 10,
                    "meal_time": "08:00"
                },
                "lunch": {
                    "taken": True,
                    "actual_dose": 15,
                    "meal_time": "13:00"
                }
            }
        }

        questionnaire_response = client.post(
            "/prescriptions/daily-questionnaire",
            json=questionnaire_data,
            headers=headers
        )
        assert questionnaire_response.status_code == 200
        questionnaire_result = questionnaire_response.json()
        assert "schedule" in questionnaire_result
        assert "summary" in questionnaire_result

        # Step 10: Get dose history
        history_response = client.get("/prescriptions/doses/history?days=7", headers=headers)
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert "doses" in history_data
        assert history_data["period_days"] == 7

        # Step 11: Delete account
        delete_response = client.delete("/auth/delete-account", headers=headers)
        assert delete_response.status_code == 204

        # Step 12: Verify account is deleted (profile should fail)
        deleted_profile_response = client.get("/auth/profile", headers=headers)
        assert deleted_profile_response.status_code == 401

    def test_multiple_users_concurrent_workflow(self, client, sample_prescription_data):
        """Test multiple users going through workflows concurrently"""
        import concurrent.futures

        def user_workflow(user_index):
            # Create unique user
            user_data = {
                "username": f"concurrent_flow_user_{user_index}_{int(time.time())}",
                "email": f"concurrent_flow_{user_index}_{int(time.time())}@test.com",
                "password": f"ConcurrentPass{user_index}!"
            }

            # Register
            register_response = client.post("/auth/register", json=user_data)
            if register_response.status_code != 200:
                return False

            # Login
            login_response = client.post(
                "/auth/login",
                data={"username": user_data["username"], "password": user_data["password"]}
            )
            if login_response.status_code != 200:
                return False

            headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

            # Create prescription
            prescription_payload = {
                "prescription_data": sample_prescription_data,
                "doctor_name": f"Dr. Concurrent {user_index}"
            }

            prescription_response = client.post("/prescriptions/", json=prescription_payload, headers=headers)
            if prescription_response.status_code != 200:
                return False

            # Process questionnaire
            questionnaire_data = {
                "responses": {
                    "breakfast": {"taken": True, "actual_dose": 10, "meal_time": "08:00"}
                }
            }

            questionnaire_response = client.post(
                "/prescriptions/daily-questionnaire",
                json=questionnaire_data,
                headers=headers
            )

            return questionnaire_response.status_code == 200

        # Run 5 concurrent user workflows
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(user_workflow, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # All workflows should succeed
        success_count = sum(results)
        assert success_count == 5

    def test_prescription_lifecycle(self, client, sample_prescription_data):
        """Test complete prescription lifecycle"""
        # Create user and login
        user_data = {
            "username": f"prescription_lifecycle_{int(time.time())}",
            "email": f"prescription_lifecycle_{int(time.time())}@test.com",
            "password": "LifecyclePass123!"
        }

        client.post("/auth/register", json=user_data)
        login_response = client.post(
            "/auth/login",
            data={"username": user_data["username"], "password": user_data["password"]}
        )
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Create first prescription
        first_prescription = {
            "prescription_data": sample_prescription_data,
            "doctor_name": "Dr. First Version",
            "clinic_name": "First Clinic"
        }

        first_response = client.post("/prescriptions/", json=first_prescription, headers=headers)
        assert first_response.status_code == 200
        first_prescription_id = first_response.json()["id"]

        # Verify it's active
        active_response = client.get("/prescriptions/active", headers=headers)
        assert active_response.status_code == 200
        assert active_response.json()["id"] == first_prescription_id

        # Create second prescription (should deactivate first)
        second_prescription = {
            "prescription_data": {
                "breakfast": {"insulin": "NewHumalog", "dose": 12, "type": "rapid"},
                "dinner": {"insulin": "NewLantus", "dose": 25, "type": "long"}
            },
            "doctor_name": "Dr. Second Version",
            "clinic_name": "Second Clinic"
        }

        second_response = client.post("/prescriptions/", json=second_prescription, headers=headers)
        assert second_response.status_code == 200
        second_prescription_id = second_response.json()["id"]

        # Verify second is now active
        active_response = client.get("/prescriptions/active", headers=headers)
        assert active_response.status_code == 200
        active_prescription = active_response.json()
        assert active_prescription["id"] == second_prescription_id
        assert active_prescription["doctor_name"] == "Dr. Second Version"

        # Test questionnaire with new prescription
        questionnaire_data = {
            "responses": {
                "breakfast": {"taken": True, "actual_dose": 12, "meal_time": "08:00"},
                "dinner": {"taken": True, "actual_dose": 25, "meal_time": "19:00"}
            }
        }

        questionnaire_response = client.post(
            "/prescriptions/daily-questionnaire",
            json=questionnaire_data,
            headers=headers
        )
        assert questionnaire_response.status_code == 200

    def test_error_handling_integration(self, client):
        """Test error handling in integrated workflows"""
        # Create user and login
        user_data = {
            "username": f"error_test_{int(time.time())}",
            "email": f"error_test_{int(time.time())}@test.com",
            "password": "ErrorPass123!"
        }

        client.post("/auth/register", json=user_data)
        login_response = client.post(
            "/auth/login",
            data={"username": user_data["username"], "password": user_data["password"]}
        )
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Test questionnaire without prescription
        questionnaire_data = {
            "responses": {
                "breakfast": {"taken": True, "actual_dose": 10, "meal_time": "08:00"}
            }
        }

        questionnaire_response = client.post(
            "/prescriptions/daily-questionnaire",
            json=questionnaire_data,
            headers=headers
        )
        assert questionnaire_response.status_code == 404
        assert "No active prescription found" in questionnaire_response.json()["detail"]

        # Test invalid prescription creation
        invalid_prescription = {
            "prescription_data": {},  # Invalid empty data
            "doctor_name": "Dr. Invalid"
        }

        invalid_response = client.post("/prescriptions/", json=invalid_prescription, headers=headers)
        assert invalid_response.status_code == 400

        # Test unauthorized access
        unauthorized_response = client.get("/prescriptions/active")
        assert unauthorized_response.status_code == 401

    def test_safety_validation_integration(self, client, sample_prescription_data):
        """Test safety validation in complete workflow"""
        # Create user and prescription
        user_data = {
            "username": f"safety_test_{int(time.time())}",
            "email": f"safety_test_{int(time.time())}@test.com",
            "password": "SafetyPass123!"
        }

        client.post("/auth/register", json=user_data)
        login_response = client.post(
            "/auth/login",
            data={"username": user_data["username"], "password": user_data["password"]}
        )
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Create prescription
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=headers)

        # Test questionnaire with overdoses
        dangerous_questionnaire = {
            "responses": {
                "breakfast": {"taken": True, "actual_dose": 25, "meal_time": "08:00"},  # Overdose
                "lunch": {"taken": True, "actual_dose": 30, "meal_time": "13:00"},     # Overdose
                "dinner": {"taken": True, "actual_dose": 35, "meal_time": "19:00"}    # Overdose
            }
        }

        danger_response = client.post(
            "/prescriptions/daily-questionnaire",
            json=dangerous_questionnaire,
            headers=headers
        )
        assert danger_response.status_code == 200

        danger_data = danger_response.json()
        assert "critical_warnings" in danger_data
        assert len(danger_data["critical_warnings"]) > 0
        assert danger_data["summary"]["overdoses_detected"] >= 3
        assert danger_data["summary"]["requires_medical_attention"] is True

    def test_data_persistence_integration(self, client, sample_prescription_data):
        """Test data persistence across sessions"""
        # Create user and prescription
        user_data = {
            "username": f"persistence_test_{int(time.time())}",
            "email": f"persistence_test_{int(time.time())}@test.com",
            "password": "PersistencePass123!"
        }

        client.post("/auth/register", json=user_data)
        login_response = client.post(
            "/auth/login",
            data={"username": user_data["username"], "password": user_data["password"]}
        )
        headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

        # Create prescription
        prescription_payload = {
            "prescription_data": sample_prescription_data,
            "doctor_name": "Dr. Persistence Test"
        }
        prescription_response = client.post("/prescriptions/", json=prescription_payload, headers=headers)
        prescription_id = prescription_response.json()["id"]

        # Submit questionnaire
        questionnaire_data = {
            "responses": {
                "breakfast": {"taken": True, "actual_dose": 10, "meal_time": "08:00"},
                "lunch": {"taken": True, "actual_dose": 15, "meal_time": "13:00"}
            }
        }
        client.post("/prescriptions/daily-questionnaire", json=questionnaire_data, headers=headers)

        # Simulate new session - login again
        login_response2 = client.post(
            "/auth/login",
            data={"username": user_data["username"], "password": user_data["password"]}
        )
        headers2 = {"Authorization": f"Bearer {login_response2.json()['access_token']}"}

        # Verify prescription still exists and is active
        active_response = client.get("/prescriptions/active", headers=headers2)
        assert active_response.status_code == 200
        assert active_response.json()["id"] == prescription_id

        # Verify dose history is preserved
        history_response = client.get("/prescriptions/doses/history?days=7", headers=headers2)
        assert history_response.status_code == 200
        history_data = history_response.json()
        assert history_data["total_entries"] > 0
