from pydantic import BaseModel, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PostgresSettings(BaseModel):

    host: str
    port: str
    user: str
    password: str
    db: str

    @computed_field
    @property
    def conn_string(self) -> str:
        # uses psycopg V3 dialect, can use for both async and sync engines
        conn_string = f"postgresql+psycopg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
        return conn_string


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    postgres: PostgresSettings
