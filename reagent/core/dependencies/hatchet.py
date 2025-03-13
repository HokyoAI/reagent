from hatchet_sdk import Hatchet

from reagent.core.dependencies.settings import get_settings

config = get_settings()
hatchet = Hatchet()


def get_hatchet():
    global hatchet
    return hatchet
