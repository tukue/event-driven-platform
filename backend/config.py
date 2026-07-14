from pydantic_settings import BaseSettings
from typing import Optional
import os
from pathlib import Path

class Settings(BaseSettings):
    redis_host: str
    redis_port: int = 6379
    redis_username: Optional[str] = None
    redis_password: str = ""
    redis_db: int = 0
    cors_allow_origins: str = "http://localhost:5173,http://localhost:3000"
    kafka_bootstrap_servers: Optional[str] = None
    kafka_topic: str = "orders"
    
    class Config:
        env_file = Path(__file__).parent / ".env"
        env_file_encoding = 'utf-8'

settings = Settings()
