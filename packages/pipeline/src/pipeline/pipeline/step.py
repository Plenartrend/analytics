from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Tuple

from ..schemas.schema import Config, PipelineConfig


class Step(ABC):
    @abstractmethod
    def __init__(self, *, config: Config | None = None):
        raise NotImplementedError("This method should be overridden by subclasses")

    @abstractmethod
    def run(
        self,
        input_data: Dict[str, str] | Tuple[Dict[str, str]] | None,
        pipeline_config: PipelineConfig,
    ) -> Any:
        raise NotImplementedError("This method should be overridden by subclasses")
