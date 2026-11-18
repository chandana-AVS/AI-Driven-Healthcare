"""Application configuration loaded from environment variables / .env file."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    APP_NAME: str = "AI Healthcare Assistant API"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/healthcare_assistant"

    JWT_SECRET_KEY: str = "CHANGE_ME_DEV_ONLY_SECRET_KEY_32_BYTES_MIN"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    MAX_UPLOAD_SIZE_MB: int = 10
    STORAGE_PATH: str = "storage/medical_documents"

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- SMS / phone verification -------------------------------------------------------------
    # "static"  : no SMS is sent and the code is always OTP_STATIC_CODE (temporary, until SMS is integrated).
    # "console" : random code printed in the backend log (development).
    # "twilio"  : random code sent as a real SMS.
    SMS_PROVIDER: str = "static"
    OTP_STATIC_CODE: str = "123456"
    SMS_DEFAULT_COUNTRY_CODE: str = "+91"  # prefixed to numbers saved without a leading "+"
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""
    OTP_LENGTH: int = 6
    OTP_EXPIRE_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 5            # wrong guesses allowed per code
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    OTP_MAX_PER_HOUR: int = 5            # codes sent per account per hour

    # --- AI (Milestone 2): translation, simplification, entity extraction, symptom guidance -------
    # OpenAI API key from https://platform.openai.com/api-keys (starts with "sk-"). repr=False keeps it out of logs.
    OPENAI_API_KEY: str = Field(default="", repr=False)
    AI_MODEL: str = "gpt-4o-mini"         # text translation / simplification / symptoms
    AI_VISION_MODEL: str = "gpt-4o"       # reading uploaded documents; much better at handwriting
    AI_MAX_OUTPUT_TOKENS: int = 16000    # gpt-4o-mini allows at most 16,384 output tokens
    AI_TIMEOUT_SECONDS: int = 300
    AI_DAILY_LIMIT_PER_USER: int = 100   # AI requests per user per 24 hours

    @property
    def ai_api_key(self) -> str:
        return self.OPENAI_API_KEY.strip().strip('"').strip("'")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def storage_dir(self) -> Path:
        path = Path(self.STORAGE_PATH)
        return path if path.is_absolute() else BASE_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
