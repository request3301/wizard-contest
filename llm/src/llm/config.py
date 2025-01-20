# mypy: ignore-errors
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

file = Path(__file__)
env_file = file.parent.parent.parent / '.env'

print(env_file)


class Settings(BaseSettings):
    GROQ_API_KEY: str

    model_config = SettingsConfigDict(env_file=env_file)


settings = Settings()
