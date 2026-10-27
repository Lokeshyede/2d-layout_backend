import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "RETAILFIX Store Survey & 2D CAD Platform"
    API_V1_STR: str = "/api"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Database: Async PostgreSQL required
    DATABASE_URL: str
    
    # Uploads
    UPLOAD_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
        "http://192.168.29.238:5173",
        "http://192.168.29.238:3000",
        "http://192.168.1.104:5173",
        "http://192.168.1.104:3000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://192.168.29.238:8001",
        "http://192.168.1.104:8001",
    ]
    
    # Default Admin
    DEFAULT_ADMIN_USERNAME: str
    DEFAULT_ADMIN_PASSWORD: str
    DEFAULT_ADMIN_EMAIL: str

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
