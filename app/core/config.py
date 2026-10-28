import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Union
from pydantic import field_validator

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
        "https://2d-layoutfrontend.vercel.app",
        "https://2d-layoutfrontend-git-main-jayyede93-7431s-projects.vercel.app",
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

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.strip().startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    # Scoped preview origin regex matching only this Vercel project and local/LAN networks
    BACKEND_CORS_ORIGIN_REGEX: str = (
        r"^https://2d-layoutfrontend(-[a-zA-Z0-9_\-]+)?(\.vercel\.app|-jayyede93-7431s-projects\.vercel\.app)$"
        r"|^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+)(:\d+)?$"
    )
    
    # Default Admin
    DEFAULT_ADMIN_USERNAME: str
    DEFAULT_ADMIN_PASSWORD: str
    DEFAULT_ADMIN_EMAIL: str

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

settings = Settings()
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
