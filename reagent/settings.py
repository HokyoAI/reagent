from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    api_key: str
    api_base: str
