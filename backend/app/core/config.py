from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "NovaWorks HR Copilot"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./novaworks.db"

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    LLM_PROVIDER: str = "dell_gateway"
    ENVIRONMENT: str = "development"

    OPENAI_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()