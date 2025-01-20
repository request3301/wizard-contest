# mypy: ignore-errors

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

env_file = Path(__file__).parent.parent.parent / '.env'


class Settings(BaseSettings):
    PROD_TOKEN: str
    DEV_TOKEN: str
    DB_OUT_HOST: str
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str

    @property
    def TOKEN(self) -> str:
        if os.environ.get('DEPLOY'):
            return self.PROD_TOKEN
        else:
            return self.DEV_TOKEN

    @property
    def DATABASE_URL(self) -> str:
        if os.environ.get('DEPLOY'):
            return (
                f'postgresql+asyncpg://'
                f'{self.DB_USER}:'
                f'{self.DB_PASS}@'
                f'{self.DB_HOST}:'
                f'{self.DB_PORT}/'
                f'{self.DB_NAME}'
            )
        else:
            return (
                f'postgresql+asyncpg://'
                f'{self.DB_USER}:'
                f'{self.DB_PASS}@'
                f'{self.DB_OUT_HOST}:'
                f'{self.DB_PORT}/'
                f'{self.DB_NAME}'
            )

    @property
    def CONTEST_SERVICE_URL(self) -> str:
        if os.environ.get('DEPLOY'):
            return 'http://contest:8000'
        else:
            return 'http://localhost:5001'

    @property
    def COORDINATOR_SERVICE_URL(self) -> str:
        if os.environ.get('DEPLOY'):
            return 'http://coordinator:8000'
        else:
            return 'http://localhost:5002'

    @property
    def LLM_SERVICE_URL(self) -> str:
        if os.environ.get('DEPLOY'):
            return 'http://llm:8080'
        else:
            return 'http://localhost:5003'

    model_config = SettingsConfigDict(env_file=env_file)


settings = Settings()
