# tests/test_prescriptions.py
import pytest
import json
import base64
import io
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from PIL import Image

class TestPrescriptions:
    """Test prescription management functionality"""

    def test_create_prescription_success(self, client, authenticated_user, sample_prescription_data):
        """Test successful prescription creation"""
        prescription_payload = {
            "prescription_data": sample_prescription_data,
            "doctor_name": "Dr. Test Smith",
            "doctor_phone": "+1234567890",
            "doctor_email": "dr.smith@test.com",
            "clinic_name": "Test Medical Center",
            "prescription_date": datetime.now().isoformat()
        }

        response = client.post(
            "/prescriptions/",
            json=prescription_payload,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200

        data = response.json()
        assert data["doctor_name"] == "Dr. Test Smith"
        assert data["is_active"] is True
        assert "id" in data

    def test_get_active_prescription(self, client, authenticated_user, sample_prescription_data):
        """Test retrieving active prescription"""
        # Create prescription first
        prescription_payload = {
            "prescription_data": sample_prescription_data,
            "doctor_name": "Dr. Active Test"
        }

        create_response = client.post(
            "/prescriptions/",
            json=prescription_payload,
            headers=authenticated_user["headers"]
        )
        assert create_response.status_code == 200

        # Get active prescription
        response = client.get("/prescriptions/active", headers=authenticated_user["headers"])
        assert response.status_code == 200

        data = response.json()
        assert data["doctor_name"] == "Dr. Active Test"
        assert data["is_active"] is True

    def test_get_active_prescription_not_found(self, client, authenticated_user):
        """Test getting active prescription when none exists"""
        response = client.get("/prescriptions/active", headers=authenticated_user["headers"])
        assert response.status_code == 404
        assert "No active prescription found" in response.json()["detail"]

    def test_get_comprehensive_status(self, client, authenticated_user, sample_prescription_data):
        """Test comprehensive status endpoint"""
        # Create prescription
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])

        # Get status
        response = client.get("/prescriptions/status", headers=authenticated_user["headers"])
        assert response.status_code == 200

        data = response.json()
        assert "current_time" in data
        assert "current_zone" in data
        assert "prescription_data" in data
        assert "today_doses" in data
        assert "meal_options" in data

    def test_questionnaire_template(self, client, authenticated_user, sample_prescription_data):
        """Test questionnaire template endpoint"""
        # Create prescription
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])

        response = client.get("/prescriptions/template", headers=authenticated_user["headers"])
        assert response.status_code == 200

        data = response.json()
        assert "current_time" in data
        assert "current_zone" in data
        assert "template" in data
        assert "instructions" in data
        assert "warnings" in data

    def test_multiple_prescriptions_only_one_active(self, client, authenticated_user, sample_prescription_data):
        """Test that only one prescription can be active at a time"""
        # Create first prescription
        first_prescription = {
            "prescription_data": sample_prescription_data,
            "doctor_name": "Dr. First"
        }
        response1 = client.post("/prescriptions/", json=first_prescription, headers=authenticated_user["headers"])
        assert response1.status_code == 200

        # Create second prescription
        second_prescription = {
            "prescription_data": sample_prescription_data,
            "doctor_name": "Dr. Second"
        }
        response2 = client.post("/prescriptions/", json=second_prescription, headers=authenticated_user["headers"])
        assert response2.status_code == 200

        # Only the second prescription should be active
        active_response = client.get("/prescriptions/active", headers=authenticated_user["headers"])
        assert active_response.status_code == 200
        assert active_response.json()["doctor_name"] == "Dr. Second"

    def test_dose_history(self, client, authenticated_user, sample_prescription_data):
        """Test dose history endpoint"""
        # Create prescription
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])

        # Get dose history
        response = client.get("/prescriptions/doses/history?days=7", headers=authenticated_user["headers"])
        assert response.status_code == 200

        data = response.json()
        assert "period_days" in data
        assert "total_entries" in data
        assert "doses" in data
        assert data["period_days"] == 7

    def test_dose_history_invalid_days(self, client, authenticated_user):
        """Test dose history with invalid days parameter"""
        response = client.get("/prescriptions/doses/history?days=50", headers=authenticated_user["headers"])
        assert response.status_code == 400
        assert "Days must be between 1 and 30" in response.json()["detail"]


class TestPrescriptionUpload:
    """Test prescription upload functionality"""

    @pytest.fixture
    def sample_image_content(self):
        """Create a sample image for testing"""
        # Create a simple test image
        img = Image.new('RGB', (200, 200), color='white')
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return img_buffer.getvalue()

    @pytest.fixture
    def mock_ocr_response(self):
        """Mock OCR response data"""
        prescription_data = {
            "breakfast": {"insulin": "Humalog", "dose": 8, "type": "rapid"},
            "lunch": {"insulin": "Novolin R", "dose": 12, "type": "short"},
            "dinner": {"insulin": "Lantus", "dose": 18, "type": "long"}
        }
        doctor_info = {
            "doctor_name": "Dr. Jane Smith",
            "doctor_phone": "+1-555-0123",
            "doctor_email": "jane.smith@clinic.com",
            "clinic_name": "Main Street Clinic",
            "date": "2025-09-03"
        }
        return prescription_data, doctor_info

    @patch('routes.consolidated_routes.run_ocr')
    def test_upload_image_success(self, mock_run_ocr, client, authenticated_user, sample_image_content, mock_ocr_response):
        """Test successful image upload and OCR processing"""
        mock_run_ocr.return_value = mock_ocr_response

        files = {"file": ("test_prescription.png", sample_image_content, "image/png")}

        response = client.post(
            "/prescriptions/upload",
            files=files,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200

        data = response.json()
        assert "message" in data
        assert "prescription_id" in data
        assert "extracted_data" in data
        assert "doctor_info" in data
        assert data["extracted_data"]["breakfast"]["insulin"] == "Humalog"

    @patch('routes.consolidated_routes.run_ocr')
    def test_upload_image_no_prescription_found(self, mock_run_ocr, client, authenticated_user, sample_image_content):
        """Test upload when no prescription is found in image"""
        mock_run_ocr.return_value = ({}, {})  # Empty prescription data

        files = {"file": ("test_image.png", sample_image_content, "image/png")}

        response = client.post(
            "/prescriptions/upload",
            files=files,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 400
        assert "No insulin prescriptions found" in response.json()["detail"]

    def test_upload_invalid_file_type(self, client, authenticated_user):
        """Test upload with invalid file type"""
        files = {"file": ("test.txt", b"Invalid content", "text/plain")}

        response = client.post(
            "/prescriptions/upload",
            files=files,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 400
        assert "File must be PDF or image" in response.json()["detail"]

    def test_upload_without_auth(self, client, sample_image_content):
        """Test upload without authentication"""
        files = {"file": ("test.png", sample_image_content, "image/png")}

        response = client.post("/prescriptions/upload", files=files)
        assert response.status_code == 401


class TestQuestionnaireProcessing:
    """Test questionnaire processing functionality"""

    def test_process_questionnaire_success(self, client, authenticated_user, sample_prescription_data, sample_questionnaire_data):
        """Test successful questionnaire processing"""
        # Create prescription first
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])

        # Process questionnaire
        response = client.post(
            "/prescriptions/daily-questionnaire",
            json=sample_questionnaire_data,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200

        data = response.json()
        assert "current_time" in data
        assert "current_zone" in data
        assert "schedule" in data
        assert "warnings" in data
        assert "summary" in data

    def test_process_questionnaire_with_overdose(self, client, authenticated_user, sample_prescription_data):
        """Test questionnaire processing with overdose detection"""
        # Create prescription first
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])

        # Create questionnaire with overdoses
        overdose_data = {
            "responses": {
                "breakfast": {
                    "taken": True,
                    "actual_dose": 25,  # Way higher than prescribed 10
                    "meal_time": "08:00"
                },
                "lunch": {
                    "taken": True,
                    "actual_dose": 30,  # Way higher than prescribed 15
                    "meal_time": "13:00"
                }
            }
        }

        response = client.post(
            "/prescriptions/daily-questionnaire",
            json=overdose_data,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200

        data = response.json()
        assert "critical_warnings" in data
        assert len(data["critical_warnings"]) > 0
        assert data["summary"]["overdoses_detected"] >= 2

    def test_process_questionnaire_no_prescription(self, client, authenticated_user, sample_questionnaire_data):
        """Test questionnaire processing without active prescription"""
        response = client.post(
            "/prescriptions/daily-questionnaire",
            json=sample_questionnaire_data,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 404
        assert "No active prescription found" in response.json()["detail"]

    def test_process_questionnaire_missed_doses(self, client, authenticated_user, sample_prescription_data):
        """Test questionnaire processing with missed doses"""
        # Create prescription first
        prescription_payload = {"prescription_data": sample_prescription_data}
        client.post("/prescriptions/", json=prescription_payload, headers=authenticated_user["headers"])

        # Create questionnaire with missed doses
        missed_dose_data = {
            "responses": {
                "breakfast": {
                    "taken": False,
                    "meal_time": "08:00"
                },
                "lunch": {
                    "taken": False,
                    "meal_time": "13:00"
                }
            }
        }

        response = client.post(
            "/prescriptions/daily-questionnaire",
            json=missed_dose_data,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 200

        data = response.json()
        assert "schedule" in data
        # Check that advice is provided for missed doses
        for item in data["schedule"]:
            if "Missed" in item["status"]:
                assert "advice" in item
                assert len(item["advice"]) > 0


class TestPrescriptionValidation:
    """Test prescription data validation"""

    def test_create_prescription_invalid_data(self, client, authenticated_user):
        """Test prescription creation with invalid data"""
        invalid_prescription = {
            "prescription_data": {},  # Empty prescription data
            "doctor_name": "Dr. Test"
        }

        response = client.post(
            "/prescriptions/",
            json=invalid_prescription,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 400

    def test_create_prescription_missing_required_fields(self, client, authenticated_user):
        """Test prescription creation with missing required fields"""
        invalid_prescription = {
            "prescription_data": {
                "breakfast": {"insulin": "Humalog"}  # Missing dose and type
            }
        }

        response = client.post(
            "/prescriptions/",
            json=invalid_prescription,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 400

    def test_create_prescription_invalid_dose(self, client, authenticated_user):
        """Test prescription creation with invalid dose"""
        invalid_prescription = {
            "prescription_data": {
                "breakfast": {"insulin": "Humalog", "dose": -5, "type": "rapid"}  # Negative dose
            }
        }

        response = client.post(
            "/prescriptions/",
            json=invalid_prescription,
            headers=authenticated_user["headers"]
        )
        assert response.status_code == 400
