from pydantic_settings import BaseSettings
from typing import Optional
class Settings(BaseSettings):
    """Application settings and configuration."""
    
    # Groq AI Settings (FREE)
    GROQ_API_KEY: str
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    
    # Pexels Settings (FREE)
    PEXELS_API_KEY: str
    
    # Qdrant Settings (Local)
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "presentations"
    
    # Server Settings
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:8501"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    PROJECT_NAME: str = "EduSlide AI"
    PROJECT_VERSION: str = "1.0.0"
    
        # CORS Settings
    ALLOWED_ORIGINS: list[str] = ["*"]

    
    class Config:
        env_file = ".env"
        case_sensitive = True
# Create global settings instance
settings = Settings()