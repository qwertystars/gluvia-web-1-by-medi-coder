# ocr.py
import os
import re
import json
import base64
from io import BytesIO
import pymupdf
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(override=True)

client = OpenAI(
    base_url=os.getenv("OPENROUTER_API_BASE_URL"),
    api_key=os.getenv("OPENROUTER_API_KEY")
)

def process_pdf_to_base64(pdf_content: bytes, max_pages: int = 3) -> list[str]:
    """
    Convert PDF pages to base64 encoded images
    Args:
        pdf_content: PDF file content as bytes
        max_pages: Maximum number of pages to process (default: 3)
    Returns:
        List of base64 encoded image strings
    """
    images_base64 = []
    doc = pymupdf.open(stream=pdf_content, filetype="pdf")
    
    # Process only first 3 pages or less if document has fewer pages
    for page_num in range(min(max_pages, len(doc))):
        page = doc[page_num]
        pix = page.get_pixmap()
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        encoded = base64.b64encode(buffer.read()).decode("utf-8")
        images_base64.append(encoded)
    
    doc.close()
    return images_base64

def process_image_to_base64(image_content: bytes) -> str:
    """
    Convert image content to base64 string
    Args:
        image_content: Image file content as bytes
    Returns:
        Base64 encoded image string
    """
    return base64.b64encode(image_content).decode("utf-8")

def run_ocr(base64_images: list[str]):
    """
    Send a list of base64-encoded images to the AI
    and return structured prescription JSON.
    """
    image_parts = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{img}"},
        }
        for img in base64_images
    ]

    prompt = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": """You are an OCR and prescription extraction assistant.

Extract ONLY insulin prescriptions from the image(s) and return them in **strict JSON** format like this:

{
    "breakfast": {"insulin": "Humalog", "dose": 10, "type": "rapid"},
    "lunch": {"insulin": "Novolin R", "dose": 15, "type": "short"},
    "dinner": {"insulin": "NPH", "dose": 20, "type": "intermediate"},
    "bedtime": {"insulin": "Glargine", "dose": 34, "type": "long"},
    "snack": {"insulin": "Mix 70/30", "dose": 18, "type": "mixed"}
}

⚠️ Rules:
- Ignore all non-insulin medicines.
- If a meal is missing in the prescription, leave it out of the JSON.
- If a unit is missing in the prescription, leave it out of the JSON.
- Use the closest matching insulin type (rapid, long, short, mixed).
- Dose must be a number (units of insulin).
- Output only valid JSON (no explanation).
""",
            },
            *image_parts,
        ],
    }

    completion = client.chat.completions.create(
        model="meta-llama/llama-4-maverick:free",
        messages=[prompt],
    )

    output_str = completion.choices[0].message.content.strip()
    clean_str = re.sub(r"^```json\s*|\s*```$", "", output_str, flags=re.DOTALL)
    prescription = json.loads(clean_str)

    prompt = {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": """You are an OCR and prescription extraction assistant.
    Extract ONLY doctor name, clinic name, doctor's phone number (not for appointment), doctor's email, and date from the image(s) and return them in **strict JSON** format like this:
    {
        "doctor_name": "Dr. John Smith",
        "doctor_phone": "91+1234567890",
        "doctor_email": "john.smith@example.com"
        "clinic_name": "Health Clinic",
        "date": "2023-10-05"
    }
    If any field is missing, leave it out of the JSON.
    Output only valid JSON (no explanation).""",
            },
            *image_parts,
        ],
    }

    completion = client.chat.completions.create(
        model="meta-llama/llama-4-maverick:free",
        messages=[prompt],
    )
    output_str = completion.choices[0].message.content.strip()
    clean_str = re.sub(r"^```json\s*|\s*```$", "", output_str, flags=re.DOTALL)
    info = json.loads(clean_str)

    return prescription, info