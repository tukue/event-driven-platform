from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    redis_host: str
    redis_port: int = 6379
    redis_username: Optional[str] = None
    redis_password: str = ""
    redis_db: int = 0
    
    class Config:
        env_file = ".env"

settings = Settings()
