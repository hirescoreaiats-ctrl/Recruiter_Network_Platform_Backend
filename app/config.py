import os
from pathlib import Path


class Settings:
    app_env = os.getenv("APP_ENV", "development")
    database_url = os.getenv("DATABASE_URL", "sqlite:///./recruitment_network.db")
    jwt_secret = os.getenv("JWT_SECRET", "local-only-change-me")
    access_token_minutes = int(os.getenv("ACCESS_TOKEN_MINUTES", "480"))
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads/resumes")).resolve()
    max_resume_bytes = int(os.getenv("MAX_RESUME_MB", "5")) * 1024 * 1024
    profile_picture_dir = Path(os.getenv("PROFILE_PICTURE_DIR", "./uploads/profile-pictures")).resolve()
    max_profile_picture_bytes = int(os.getenv("MAX_PROFILE_PICTURE_MB", "2")) * 1024 * 1024


settings = Settings()
