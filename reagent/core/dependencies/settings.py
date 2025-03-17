from dotenv import load_dotenv

from reagent.core.models.settings import Settings

load_dotenv(override=True)  # set override to True to make .env the source of truth
settings = Settings()  # pyright: ignore


def get_settings():
    global settings
    return settings
