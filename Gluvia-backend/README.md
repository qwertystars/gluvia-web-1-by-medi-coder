# Gluvia - Insulin Management System

A FastAPI-based application for managing insulin prescriptions and dose tracking.

## Features

- User authentication with JWT tokens
- Prescription OCR processing
- Insulin dose tracking and management
- Daily questionnaire for dose compliance
- Enhanced dose calculation with insulin onset times
- PostgreSQL database integration

## Setup

### Prerequisites
- Python 3.11+
- PostgreSQL database
- OpenRouter API key (for OCR functionality)

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd Gluvia
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Environment Setup
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Database Setup
```bash
python setup/setup_db.py
```

6. Run the application
```bash
uvicorn main:app --reload
```

## API Documentation

Once running, visit:
- API Docs: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

## Security Notes

- Never commit `.env` files to version control
- Rotate API keys regularly
- Use strong, randomly generated SECRET_KEY
- Enable database SSL in production

## Testing

Run the enhanced tester:
```bash
python enhanced_prescription_tester.py
```

## License

[Add your license here]
