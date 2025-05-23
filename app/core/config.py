from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "cloudnativepg-demo"
    APP_PORT: int = 8000
    PRIMARY_DB_URL: str
    REPLICA_DB_URL: str
    ENABLE_METRICS: bool = True

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings() 