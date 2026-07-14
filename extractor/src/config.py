from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    opera_client_id: str
    opera_client_secret: str
    opera_app_key: str
    opera_base_url: str
    opera_token_url: str
    opera_hotel_id: str
    opera_scope: str
    opera_enterprise_id: str
    DATABASE_URL: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    model_config = SettingsConfigDict(env_file=".env")

def get_settings():
    return Settings()

settings = get_settings()
