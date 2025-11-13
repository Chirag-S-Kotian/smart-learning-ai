from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Smart LMS"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    @property
    def debug(self) -> bool:
        return self.DEBUG
    
    # API Settings
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Supabase Configuration
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str
    
    @property
    def supabase_url(self) -> str:
        return self.SUPABASE_URL

    @property
    def supabase_key(self) -> str:
        return self.SUPABASE_KEY

    @property
    def supabase_service_role_key(self) -> str:
        return self.SUPABASE_SERVICE_ROLE_KEY
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    GOOGLE_REDIRECT_URI: str
    
    # Gemini AI Configuration
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    
    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@smartlms.com"
    
    # Twilio Configuration
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""
    
    # Storage
    STORAGE_BUCKET: str = "lms-storage"
    MAX_FILE_SIZE: int = 524288000  # 500MB for video uploads
    CERTIFICATE_STORAGE_PATH: str = "certificates/"
    CERTIFICATE_TEMPLATE_PATH: str = "templates/certificate_template.html"
    
    # Database (optional direct connection string)
    SUPERBASE_DB_STRING: Optional[str] = None
    
    # CORS Settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    @property
    def host(self) -> str:
        return self.HOST

    @property
    def port(self) -> int:
        return self.PORT
    
    # DodoPay Payment Gateway
    DODOPAY_PUBLIC_KEY: str = ""
    DODOPAY_SECRET_KEY: str = ""
    DODOPAY_API_URL: str = "https://api.dodopayments.com/v1"
    DODOPAY_WEBHOOK_SECRET: str = ""
    
    # Frontend URL (for certificate verification links)
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Currency - Indian Rupees only
    DEFAULT_CURRENCY: str = "INR"
    SUPPORTED_CURRENCIES: List[str] = ["INR"]
    UPI_ENABLED: bool = True
    
    # Proctoring Settings
    PROCTORING_SNAPSHOT_INTERVAL: int = 30  # seconds
    PROCTORING_FACE_DETECTION_CONFIDENCE: float = 0.5
    MAX_PROCTORING_ALERTS: int = 10
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


