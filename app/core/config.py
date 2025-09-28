from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    To override defaults, define environment variables or use a `.env` file.
    """

    app_name: str = "VibeMoney Stock API"
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"

    # External providers
    alphavantage_api_key: str | None = None

    # Browser Use
    browser_use_api_key: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()


