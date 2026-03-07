import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = os.getenv("DATABASE_URL", "postgresql://user:pass@host:5432/dbname")
    secret_key: str = os.getenv("SECRET_KEY", "random-32-chars-default")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "Ancora2026!")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    upload_dir: str = os.getenv("UPLOAD_DIR", "/app/uploads")

    class Config:
        env_file = ".env"

settings = Settings()
