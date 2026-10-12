from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CARDEX_", env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./cardex.db"
    pokemontcg_api_key: str | None = None
    pokemontcg_base_url: str = "https://api.carddex.dev/compat/pokemontcg/v2"


@lru_cache
def get_settings() -> Settings:
    return Settings()
