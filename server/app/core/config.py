from functools import lru_cache
from typing import List

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = 'Excellent App Backend'
    app_env: str = 'development'
    app_host: str = '0.0.0.0'
    app_port: int = 8000
    app_debug: bool = True
    secret_key: str = 'change-me'
    jwt_expire_minutes: int = 1440
    access_token_expire_minutes: int = 1440

    mysql_host: str = '127.0.0.1'
    mysql_port: int = 3306
    mysql_user: str = 'root'
    mysql_password: str = '123456'
    mysql_db: str = 'excellent_app'
    mysql_pool_size: int = 10
    mysql_max_overflow: int = 20

    redis_host: str = '127.0.0.1'
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ''

    celery_broker_url: str = 'redis://127.0.0.1:6379/1'
    celery_result_backend: str = 'redis://127.0.0.1:6379/2'

    cors_origins: str = 'http://localhost:5173,http://localhost:5174'
    log_level: str = 'INFO'

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore',
    )

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f'mysql+pymysql://{self.mysql_user}:{self.mysql_password}'
            f'@{self.mysql_host}:{self.mysql_port}/{self.mysql_db}?charset=utf8mb4'
        )

    @computed_field
    @property
    def parsed_cors_origins(self) -> List[str]:
        return [item.strip() for item in self.cors_origins.split(',') if item.strip()]

    @computed_field
    @property
    def redis_url(self) -> str:
        auth = f':{self.redis_password}@' if self.redis_password else ''
        return f'redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}'


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
