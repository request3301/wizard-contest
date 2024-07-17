from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    GROQ_API_KEY: str
    TOKEN: str
    model_config = SettingsConfigDict(env_file='.env')
