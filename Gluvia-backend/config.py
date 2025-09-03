# config.py
import os
from typing import Optional
from pydantic import BaseSettings, validator
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Database
    database_url: str

    # Security
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # External APIs
    openrouter_api_key: str
    openrouter_api_base_url: str

    # Application
    app_name: str = "Gluvia"
    debug: bool = False

    # Security validations
    @validator('secret_key')
    def secret_key_must_be_strong(cls, v):
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v

    @validator('database_url')
    def database_url_must_be_valid(cls, v):
        if not v.startswith(('postgresql://', 'sqlite://')):
            raise ValueError('Database URL must be PostgreSQL or SQLite')
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
