from pydantic_settings import BaseSettings
from typing import Optional, List
import os
from pathlib import Path

class Settings(BaseSettings):
    # Redis Configuration
    redis_host: str
    redis_port: int = 6379
    redis_username: Optional[str] = None
    redis_password: str = ""
    redis_db: int = 0
    
    # CORS Configuration
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000"
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Convert comma-separated CORS origins to list"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    class Config:
        # Look for .env in backend directory
        env_file = Path(__file__).parent / ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
