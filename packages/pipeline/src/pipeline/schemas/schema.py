from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, Optional, TypeVar

from pydantic import BaseModel

from pipeline.types.result import Result


class BaseConfig(BaseModel):
    class Config:
        from_attributes = True
        arbitrary_types_allowed = True


class PipelineConfig(BaseConfig):
    name: Optional[str] = None


class PipelineModuleConfig(PipelineConfig):
    next: Callable[[Any, "PipelineModuleConfig"], Awaitable[PipelineResponse[Any, Any]]]
    cache: dict[str, Any] = {}


class Config(BaseConfig):
    pass


K = TypeVar("K")
V = TypeVar("V")


@dataclass
class PipelineResponse(Generic[K, V]):
    data: Result[K, V]
    pipeline_config: PipelineModuleConfig


@dataclass
class ErrorResponse:
    msg: str
