from typing import Dict, List, Literal

type LessonType = Literal["strategy", "skill", "verification"]

type JsonValue = List[JsonValue] | Dict[
    str, JsonValue
] | str | bool | int | float | bytes | None
