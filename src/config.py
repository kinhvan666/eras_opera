from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPERA_CLIENT_ID: str
    OPERA_CLIENT_SECRET: str
    OPERA_APP_KEY: str
    OPERA_BASE_URL: str
    OPERA_TOKEN_URL: str
    OPERA_HOTEL_ID: str
    OPERA_SCOPE: str
    OPERA_ENTERPRISE_ID: str
    DATABASE_URL: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()