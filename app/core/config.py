"""
Application Configuration
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Digital Twin"
    
    # Database
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/FYP"
    
    # Docker Database Configuration (optional)
    POSTGRES_DB: str = "FYP"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_HOST: str = "localhost"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    
    # Webhook Configuration
    WEBHOOK_BASE_URL: str = "http://localhost:8000"
    
    # Meeting Platforms
    ZOOM_CLIENT_ID: str = ""
    ZOOM_CLIENT_SECRET: str = ""
    TEAMS_CLIENT_ID: str = ""
    TEAMS_CLIENT_SECRET: str = ""
    
    # Recall AI
    RECALL_API_KEY: str = ""
    RECALL_BASE_URL: str = ""
    
    # Voice Settings
    VOICE_MODEL_PATH: str = "models/voice/"
    RECORDING_PATH: str = "recordings/"
    
    # RAG Settings
    VECTOR_DB_PATH: str = "data/vectordb/"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    model_config = ConfigDict(env_file=".env")


settings = Settings()