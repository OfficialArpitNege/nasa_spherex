import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "SPHEREx Moving Object Explorer"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"
    
    # Centralized CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]
    
    # IRSA SPHEREx Service Endpoint
    IRSA_TAP_URL: str = "https://irsa.ipac.caltech.edu/TAP/sync"
    
    # Cache directory path
    CACHE_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cache")
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
