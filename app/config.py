from pydantic import BaseModel
import os

class Settings(BaseModel):
    app_name: str = "Mock Jury Agent"
    database_url: str = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/mockjury")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4.1")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    max_rounds: int = int(os.getenv("MAX_ROUNDS", "4"))
    juror_count: int = int(os.getenv("JUROR_COUNT", "12"))
    cors_origins: list[str] = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    llm_max_retries: int = int(os.getenv("LLM_MAX_RETRIES", "3"))
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    run_timeout_seconds: int = int(os.getenv("RUN_TIMEOUT_SECONDS", "300"))

settings = Settings()