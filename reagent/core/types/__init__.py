from typing import Dict, Union

from pydantic import BaseModel

type AM = BaseModel  # shorthand for BaseModel

# type JsonValue = List[JsonValue] | Dict[
#     str, JsonValue
# ] | str | bool | int | float | bytes | None

type LabelValue = Union[str, int, float, bool, None]
type Labels = Dict[str, LabelValue]
