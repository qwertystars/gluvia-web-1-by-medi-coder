# database.py
import os
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, Index
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Improved engine configuration with connection pooling
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    echo=False  # Set to True for SQL debugging
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# User model
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships with CASCADE DELETE
    prescriptions = relationship("Prescription", back_populates="user", cascade="all, delete-orphan")
    dose_logs = relationship("DoseLog", back_populates="user", cascade="all, delete-orphan")
    user_sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    questionnaire_responses = relationship("QuestionnaireResponse", back_populates="user", cascade="all, delete-orphan")

    # Add indexes for better query performance
    __table_args__ = (
        Index('idx_user_active_created', 'is_active', 'created_at'),
    )

# Prescription model
class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    doctor_name = Column(String)
    doctor_phone = Column(String)
    doctor_email = Column(String)
    clinic_name = Column(String)
    prescription_date = Column(DateTime, index=True)
    prescription_data = Column(Text)  # JSON string of prescription
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = relationship("User", back_populates="prescriptions")
    dose_logs = relationship("DoseLog", back_populates="prescription", cascade="all, delete-orphan")

    # Composite indexes for common queries
    __table_args__ = (
        Index('idx_prescription_user_active', 'user_id', 'is_active'),
        Index('idx_prescription_active_date', 'is_active', 'prescription_date'),
    )

# Dose log model - stores all dose-related user inputs
class DoseLog(Base):
    __tablename__ = "dose_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    meal_time = Column(String, index=True)  # breakfast, lunch, dinner, bedtime, snack
    insulin_name = Column(String)
    insulin_type = Column(String, index=True)  # rapid, short, intermediate, long, mixed
    prescribed_dose = Column(Float)
    actual_dose = Column(Float, nullable=True)
    scheduled_time = Column(DateTime, index=True)
    actual_time = Column(DateTime, nullable=True, index=True)
    status = Column(String, index=True)  # taken, missed, delayed
    gap_minutes = Column(Integer, default=0)
    adjusted_dose = Column(Float, nullable=True)
    advice = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    user = relationship("User", back_populates="dose_logs")
    prescription = relationship("Prescription", back_populates="dose_logs")

    # Complex indexes for dose tracking queries
    __table_args__ = (
        Index('idx_dose_user_meal_date', 'user_id', 'meal_time', 'created_at'),
        Index('idx_dose_user_status_date', 'user_id', 'status', 'created_at'),
        Index('idx_dose_scheduled_time', 'scheduled_time'),
    )

# User session tracking - stores login/logout activities
class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    login_time = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    logout_time = Column(DateTime, nullable=True, index=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    session_duration_minutes = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True, index=True)

    # Relationships
    user = relationship("User", back_populates="user_sessions")

    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_login_time', 'login_time'),
    )

# Questionnaire responses - stores all user questionnaire inputs
class QuestionnaireResponse(Base):
    __tablename__ = "questionnaire_responses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id", ondelete="CASCADE"), nullable=False, index=True)
    response_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    questionnaire_data = Column(Text)  # JSON string of complete questionnaire responses
    warnings_generated = Column(Text, nullable=True)  # JSON array of warnings
    critical_warnings = Column(Text, nullable=True)  # JSON array of critical warnings
    total_meals_processed = Column(Integer, default=0)
    overdoses_detected = Column(Integer, default=0)
    total_excess_units = Column(Float, default=0.0)
    requires_medical_attention = Column(Boolean, default=False, index=True)
    processing_duration_ms = Column(Integer, nullable=True)  # Time taken to process

    # Relationships
    user = relationship("User", back_populates="questionnaire_responses")

    __table_args__ = (
        Index('idx_questionnaire_user_date', 'user_id', 'response_date'),
        Index('idx_questionnaire_medical_attention', 'requires_medical_attention', 'response_date'),
        Index('idx_questionnaire_overdoses', 'overdoses_detected', 'response_date'),
    )

# System audit log - tracks all user actions for debugging and compliance
class SystemAuditLog(Base):
    __tablename__ = "system_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action_type = Column(String, index=True)  # login, prescription_created, dose_logged, etc.
    endpoint = Column(String, nullable=True)
    request_method = Column(String, nullable=True)
    request_data = Column(Text, nullable=True)  # JSON of request data
    response_status = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    processing_time_ms = Column(Integer, nullable=True)

    __table_args__ = (
        Index('idx_audit_user_action', 'user_id', 'action_type'),
        Index('idx_audit_timestamp', 'timestamp'),
        Index('idx_audit_endpoint', 'endpoint'),
    )

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Create tables
def create_tables():
    Base.metadata.create_all(bind=engine)
