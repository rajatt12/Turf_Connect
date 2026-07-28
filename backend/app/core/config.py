from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Turf"
    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    ENVIRONMENT: str = "development"
    
    # Razorpay configurations
    RAZORPAY_KEY_ID: str = "dummy_key_id"
    RAZORPAY_KEY_SECRET: str = "dummy_key_secret"
    RAZORPAY_WEBHOOK_SECRET: str = "dummy_webhook_secret"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
