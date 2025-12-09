from dataclasses import dataclass
from typing import List

from ..annotations.classes.lifecycle import Lifecycle
from ..annotations.classes.router import Router


@dataclass
class KadiConfig:
    settings: dict
    topics: list[str]
    routes: List[Router]
    lifecycle: List[Lifecycle]
