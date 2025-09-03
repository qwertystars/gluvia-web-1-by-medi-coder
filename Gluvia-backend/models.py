# models.py
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any, List
from datetime import datetime

class User(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Prescription models
class PrescriptionCreate(BaseModel):
    prescription_data: Dict[str, Any]  # The prescription dictionary from OCR
    doctor_name: Optional[str] = None
    doctor_phone: Optional[str] = None
    doctor_email: Optional[str] = None
    clinic_name: Optional[str] = None
    prescription_date: Optional[datetime] = None

class PrescriptionResponse(BaseModel):
    id: int
    user_id: int
    doctor_name: Optional[str]
    doctor_phone: Optional[str]
    doctor_email: Optional[str]
    clinic_name: Optional[str]
    prescription_date: Optional[datetime]
    prescription_data: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# Dose tracking models
class DoseInput(BaseModel):
    meal_time: str  # breakfast, lunch, dinner, bedtime, snack
    status: str  # taken, missed
    actual_dose: Optional[float] = None
    actual_time: Optional[datetime] = None

class DoseResponse(BaseModel):
    id: int
    meal_time: str
    insulin_name: str
    insulin_type: str
    prescribed_dose: float
    actual_dose: Optional[float]
    scheduled_time: datetime
    actual_time: Optional[datetime]
    status: str
    gap_minutes: int
    adjusted_dose: Optional[float]
    advice: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# Dose-related models
class DoseTableResponse(BaseModel):
    meal: str
    insulin: str
    prescribed_dose: float
    status_advice: str
    actual_dose: Optional[float] = None
    gap_minutes: Optional[int] = None

class QuestionnaireResponse(BaseModel):
    meal: str
    insulin: str
    prescribed_dose: float
    status: str
    advice: str
    adjusted_dose: Optional[float] = None

class DailyScheduleResponse(BaseModel):
    current_time: str
    current_zone: str
    schedule: List[QuestionnaireResponse]

# New models for questionnaire functionality
class MealQuestionnaireInput(BaseModel):
    meal_time: str
    taken: bool
    actual_dose: Optional[float] = None
    meal_scheduled_time: Optional[str] = None  # HH:MM format

class EnhancedDoseInput(BaseModel):
    meal_time: str
    taken: bool
    actual_dose: Optional[float] = None
    meal_scheduled_time: Optional[str] = None  # When they actually had the meal (HH:MM)

class BulkQuestionnaireInput(BaseModel):
    responses: List[MealQuestionnaireInput]

# Questionnaire input models
class MealDoseInput(BaseModel):
    taken: bool
    actual_dose: Optional[float] = None
    meal_time: Optional[str] = None  # HH:MM format

class QuestionnaireInput(BaseModel):
    responses: Dict[str, MealDoseInput]  # meal_name -> dose_input
