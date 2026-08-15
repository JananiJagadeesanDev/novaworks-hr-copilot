from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "NovaWorks HR Copilot"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./novaworks.db"

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    LLM_PROVIDER: str = "google"
    ENVIRONMENT: str = "development"

    # Google AI Studio
    GOOGLE_API_KEY: str = ""

    # RAG / Vector store settings
    EMBEDDING_MODEL: str = "models/gemini-embedding-2"
    LLM_MODEL: str = "gemini-3.1-flash-lite"
    QDRANT_PATH: str = "./qdrant_data"
    POLICY_COLLECTION: str = "hr_policies"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

settings = Settings()