from typing import Dict, Union

type LabelValue = Union[str, int, float, bool, None]
type Labels = Dict[str, LabelValue]

type Identity = tuple[str | None, Labels]
