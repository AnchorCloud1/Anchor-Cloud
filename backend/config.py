# ============================================================
# config.py — Anchor Cloud Application Settings
# Loads all environment variables and exposes a typed Settings
# object. Import `settings` anywhere in the project.
# ============================================================

import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Central settings object. All values sourced from .env"""

    # --- App ---
    APP_NAME: str            = os.getenv("APP_NAME", "Anchor Cloud")
    APP_ENV: str             = os.getenv("APP_ENV", "development")
    APP_PORT: int            = int(os.getenv("APP_PORT", 8000))
    SECRET_KEY: str          = os.getenv("SECRET_KEY", "dev-secret-change-in-production")
    ALGORITHM: str           = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MIN: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

    # --- MySQL ---
    MYSQL_HOST: str     = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT: int     = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER: str     = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "anchor_cloud")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
            f"?charset=utf8mb4"
        )

    # --- Storage ---
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./vault_storage")

    # --- Google OAuth ---
    GOOGLE_CLIENT_ID: str     = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT_URI: str  = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")

    # --- Encryption ---
    MASTER_SALT: str = os.getenv("MASTER_SALT", "dev-salt-change-in-production-00000000000000")

    # --- CORS ---
    FRONTEND_ORIGIN: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:8000")


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached Settings instance."""
    return Settings()


# Convenience singleton
settings = get_settings()