# mypy: ignore-errors
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LLM_SERVICE_URL: str = 'http://llm:8000'
    TURNS_COUNT: int = 4


settings = Settings()
