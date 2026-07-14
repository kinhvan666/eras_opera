# extractor/src/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # OPERA Cloud API
    opera_client_id: str
    opera_client_secret: str
    opera_app_key: str
    opera_base_url: str
    opera_token_url: str
    opera_hotel_id: str
    opera_scope: str = ""
    opera_enterprise_id: str = ""

    # PostgreSQL
    database_url: str
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_db: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="allow"
    )

settings = Settings()