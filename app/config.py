import os
from pathlib import Path


class Settings:
    app_env = os.getenv("APP_ENV", "development")
    auto_migrate = os.getenv("AUTO_MIGRATE", "true" if app_env == "production" else "false").lower() in {"1", "true", "yes"}
    database_url = os.getenv("DATABASE_URL", "sqlite:///./recruitment_network.db")
    jwt_secret = os.getenv("JWT_SECRET", "local-only-change-me")
    access_token_minutes = int(os.getenv("ACCESS_TOKEN_MINUTES", "480"))
    upload_dir = Path(os.getenv("UPLOAD_DIR", "./uploads/resumes")).resolve()
    max_resume_bytes = int(os.getenv("MAX_RESUME_MB", "5")) * 1024 * 1024
    profile_picture_dir = Path(os.getenv("PROFILE_PICTURE_DIR", "./uploads/profile-pictures")).resolve()
    max_profile_picture_bytes = int(os.getenv("MAX_PROFILE_PICTURE_MB", "2")) * 1024 * 1024
    twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
    twilio_from_number = os.getenv("TWILIO_FROM_NUMBER", "")


settings = Settings()
