"""
Centralized application configuration, loaded from environment variables.

Using pydantic-settings means config values are validated at startup
(e.g. if DATABASE_URL is missing, the app fails immediately with a clear
error instead of failing later at first query time).
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql://user:password@localhost:5432/ai_sql_analyst"
    readonly_database_url: str = "postgresql://ai_sql_readonly:readonly_pw_change_me@localhost:5432/ai_sql_analyst"
    app_env: str = "development"
    gemini_api_key: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()