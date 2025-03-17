from pydantic import BaseModel, ConfigDict, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class PostgresSettings(BaseModel):

    host: str
    port: str
    user: str
    password: str
    db: str

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @computed_field
    @property
    def conn_url(self) -> URL:
        # uses psycopg V3 dialect, can use for both async and sync engines
        conn_url = URL.create(
            drivername="postgresql+psycopg",
            username=self.user,
            password=self.password,
            host=self.host,
            port=int(self.port),
            database=self.db,
        )
        return conn_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_nested_delimiter="__")

    postgres: PostgresSettings
