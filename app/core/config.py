from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    # ✅ إعدادات Pydantic v2 الصحيحة
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # ✅ يتجاهل أي متغيرات زيادة في .env (يحِل extra_forbidden نهائيًا)
    )

    APP_NAME: str = "كنق الاتمته - Chatbot"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 2000
    OPENAI_TEMPERATURE: float = 0.7

    JWT_SECRET_KEY: Optional[str] = None  # اجعلها str لو تبي تفرض وجوده
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    ENCRYPTION_KEY: Optional[str] = None

    POSTGRES_HOST: Optional[str] = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None

    MONGODB_URI: Optional[str] = None
    MONGODB_DB: Optional[str] = "chatbot_db"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # N8N Webhook Configuration
    N8N_WEBHOOK_URL: Optional[str] = None
    N8N_WEBHOOK_ENABLED: bool = False


settings = Settings()
