"""
Configuration management for KNCCI API
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    # Database Configuration
    database_url: str
    
    # Email Configuration
    email_host: str = "smtp.gmail.com"
    email_port: int = 587
    email_username: str
    email_password: str
    email_from: str
    email_from_name: str = "KNCCI Internship Program"
    
    # Application Configuration
    app_name: str = "KNCCI QR Form API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Security Configuration
    allowed_origins: list = ["*"]
    
    # Holland Code API Configuration
    # Assessment Database (asyncpg)
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    db_host: str = "localhost"
    db_port: str = "5432"
    db_name: Optional[str] = None
    
    # Internship/Jobs Database (psycopg2)
    in_db_host: Optional[str] = None
    in_db_port: str = "5432"
    in_db_name: Optional[str] = None
    in_db_user: Optional[str] = None
    in_db_password: Optional[str] = None
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = None
    
    @validator('database_url')
    def validate_database_url(cls, v):
        if not v:
            raise ValueError('DATABASE_URL is required')
        return v
    
    @validator('email_username')
    def validate_email_username(cls, v):
        if not v:
            raise ValueError('EMAIL_USERNAME is required')
        return v
    
    @validator('email_password')
    def validate_email_password(cls, v):
        if not v:
            raise ValueError('EMAIL_PASSWORD is required')
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields in .env that aren't defined in the model

# Global settings instance
settings = Settings()