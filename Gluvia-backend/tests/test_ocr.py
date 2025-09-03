# tests/test_ocr.py
import pytest
import json
import base64
import io
from unittest.mock import patch, MagicMock
from PIL import Image
import pymupdf

from ocr import process_pdf_to_base64, process_image_to_base64, run_ocr

class TestOCRFunctionality:
    """Test OCR and image processing functionality"""

    @pytest.fixture
    def sample_image_bytes(self):
        """Create sample image bytes for testing"""
        img = Image.new('RGB', (200, 300), color='white')
        # Add some text-like elements to make it look like a prescription
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer.getvalue()

    @pytest.fixture
    def sample_pdf_bytes(self):
        """Create minimal PDF bytes for testing"""
        # Create a minimal PDF structure
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test Prescription) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000185 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
280
%%EOF"""
        return pdf_content

    def test_process_image_to_base64(self, sample_image_bytes):
        """Test converting image to base64"""
        base64_string = process_image_to_base64(sample_image_bytes)

        assert isinstance(base64_string, str)
        assert len(base64_string) > 0

        # Verify it's valid base64
        try:
            decoded = base64.b64decode(base64_string)
            assert len(decoded) == len(sample_image_bytes)
        except Exception as e:
            pytest.fail(f"Invalid base64 string: {e}")

    @patch('pymupdf.open')
    def test_process_pdf_to_base64(self, mock_pdf_open, sample_pdf_bytes):
        """Test converting PDF to base64 images"""
        # Mock PDF document
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        
        # Configure mocks
        mock_pdf_open.return_value = mock_doc
        mock_doc.__len__.return_value = 2  # 2 pages
        mock_doc.__getitem__.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pixmap

        # Mock pixmap properties
        mock_pixmap.width = 200
        mock_pixmap.height = 300
        # Create fake image data
        fake_image_data = b'\x00' * (200 * 300 * 3)  # RGB data
        mock_pixmap.samples = fake_image_data

        # Test the function
        base64_images = process_pdf_to_base64(sample_pdf_bytes, max_pages=2)

        assert isinstance(base64_images, list)
        assert len(base64_images) == 2  # Should process 2 pages

        for img_b64 in base64_images:
            assert isinstance(img_b64, str)
            assert len(img_b64) > 0

    @patch('pymupdf.open')
    def test_process_pdf_to_base64_max_pages(self, mock_pdf_open, sample_pdf_bytes):
        """Test PDF processing with max pages limit"""
        # Mock PDF with 5 pages
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        
        mock_pdf_open.return_value = mock_doc
        mock_doc.__len__.return_value = 5  # 5 pages
        mock_doc.__getitem__.return_value = mock_page
        mock_page.get_pixmap.return_value = mock_pixmap

        mock_pixmap.width = 100
        mock_pixmap.height = 100
        mock_pixmap.samples = b'\x00' * (100 * 100 * 3)
        
        # Test with max_pages=3
        base64_images = process_pdf_to_base64(sample_pdf_bytes, max_pages=3)

        assert len(base64_images) == 3  # Should only process 3 pages

    @patch('ocr.client.chat.completions.create')
    def test_run_ocr_success(self, mock_openai_create):
        """Test successful OCR processing"""
        # Mock OpenAI responses
        mock_prescription_response = MagicMock()
        mock_prescription_response.choices = [MagicMock()]
        mock_prescription_response.choices[0].message.content = json.dumps({
            "breakfast": {"insulin": "Humalog", "dose": 10, "type": "rapid"},
            "lunch": {"insulin": "Novolin R", "dose": 15, "type": "short"}
        })

        mock_doctor_response = MagicMock()
        mock_doctor_response.choices = [MagicMock()]
        mock_doctor_response.choices[0].message.content = json.dumps({
            "doctor_name": "Dr. John Smith",
            "clinic_name": "Health Clinic",
            "doctor_phone": "+1234567890",
            "doctor_email": "doctor@clinic.com",
            "date": "2025-09-03"
        })

        # Configure mock to return different responses for each call
        mock_openai_create.side_effect = [mock_prescription_response, mock_doctor_response]

        # Test data
        base64_images = ["fake_base64_image_data"]

        # Run OCR
        prescription_data, doctor_info = run_ocr(base64_images)

        # Verify results
        assert isinstance(prescription_data, dict)
        assert isinstance(doctor_info, dict)

        assert "breakfast" in prescription_data
        assert prescription_data["breakfast"]["insulin"] == "Humalog"
        assert prescription_data["breakfast"]["dose"] == 10

        assert doctor_info["doctor_name"] == "Dr. John Smith"
        assert doctor_info["clinic_name"] == "Health Clinic"

        # Verify OpenAI was called twice (prescription + doctor info)
        assert mock_openai_create.call_count == 2

    @patch('ocr.client.chat.completions.create')
    def test_run_ocr_with_json_wrapper(self, mock_openai_create):
        """Test OCR processing with JSON wrapper removal"""
        # Mock response with JSON wrapper
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''```json
{
    "breakfast": {"insulin": "Humalog", "dose": 12, "type": "rapid"}
}
```'''

        mock_doctor_response = MagicMock()
        mock_doctor_response.choices = [MagicMock()]
        mock_doctor_response.choices[0].message.content = '''```json
{
    "doctor_name": "Dr. Jane Doe"
}
```'''

        mock_openai_create.side_effect = [mock_response, mock_doctor_response]

        base64_images = ["fake_image"]
        prescription_data, doctor_info = run_ocr(base64_images)

        assert prescription_data["breakfast"]["dose"] == 12
        assert doctor_info["doctor_name"] == "Dr. Jane Doe"

    @patch('ocr.client.chat.completions.create')
    def test_run_ocr_invalid_json(self, mock_openai_create):
        """Test OCR processing with invalid JSON response"""
        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Invalid JSON response"
        
        mock_openai_create.return_value = mock_response

        base64_images = ["fake_image"]

        # Should raise JSONDecodeError
        with pytest.raises(json.JSONDecodeError):
            run_ocr(base64_images)

    @patch('ocr.client.chat.completions.create')
    def test_run_ocr_empty_prescription(self, mock_openai_create):
        """Test OCR processing with empty prescription data"""
        # Mock empty prescription response
        mock_prescription_response = MagicMock()
        mock_prescription_response.choices = [MagicMock()]
        mock_prescription_response.choices[0].message.content = "{}"

        mock_doctor_response = MagicMock()
        mock_doctor_response.choices = [MagicMock()]
        mock_doctor_response.choices[0].message.content = "{}"

        mock_openai_create.side_effect = [mock_prescription_response, mock_doctor_response]

        base64_images = ["fake_image"]
        prescription_data, doctor_info = run_ocr(base64_images)

        assert prescription_data == {}
        assert doctor_info == {}

    @patch('ocr.client.chat.completions.create')
    def test_run_ocr_multiple_images(self, mock_openai_create):
        """Test OCR processing with multiple images"""
        # Mock successful response
        mock_prescription_response = MagicMock()
        mock_prescription_response.choices = [MagicMock()]
        mock_prescription_response.choices[0].message.content = json.dumps({
            "breakfast": {"insulin": "Humalog", "dose": 8, "type": "rapid"},
            "dinner": {"insulin": "Lantus", "dose": 20, "type": "long"}
        })

        mock_doctor_response = MagicMock()
        mock_doctor_response.choices = [MagicMock()]
        mock_doctor_response.choices[0].message.content = json.dumps({
            "doctor_name": "Dr. Multi Page",
            "clinic_name": "Multi Page Clinic"
        })

        mock_openai_create.side_effect = [mock_prescription_response, mock_doctor_response]

        # Multiple base64 images
        base64_images = ["image1_base64", "image2_base64", "image3_base64"]

        prescription_data, doctor_info = run_ocr(base64_images)

        assert len(prescription_data) == 2
        assert "breakfast" in prescription_data
        assert "dinner" in prescription_data
        assert doctor_info["doctor_name"] == "Dr. Multi Page"

    def test_process_image_to_base64_empty_data(self):
        """Test processing empty image data"""
        with pytest.raises(Exception):
            process_image_to_base64(b"")

    @patch('pymupdf.open')
    def test_process_pdf_to_base64_empty_pdf(self, mock_pdf_open):
        """Test processing empty PDF"""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 0  # No pages
        mock_pdf_open.return_value = mock_doc

        result = process_pdf_to_base64(b"fake_pdf_data")
        assert result == []

    @patch('ocr.client.chat.completions.create')
    def test_run_ocr_partial_data(self, mock_openai_create):
        """Test OCR with partial prescription data"""
        # Mock response with only some meals
        mock_prescription_response = MagicMock()
        mock_prescription_response.choices = [MagicMock()]
        mock_prescription_response.choices[0].message.content = json.dumps({
            "lunch": {"insulin": "Regular", "dose": 14, "type": "short"}
        })

        mock_doctor_response = MagicMock()
        mock_doctor_response.choices = [MagicMock()]
        mock_doctor_response.choices[0].message.content = json.dumps({
            "doctor_name": "Dr. Partial"
        })

        mock_openai_create.side_effect = [mock_prescription_response, mock_doctor_response]

        base64_images = ["partial_image"]
        prescription_data, doctor_info = run_ocr(base64_images)

        assert len(prescription_data) == 1
        assert "lunch" in prescription_data
        assert prescription_data["lunch"]["dose"] == 14
