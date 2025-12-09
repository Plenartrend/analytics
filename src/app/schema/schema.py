from typing import Any, Callable, List, Optional

from pipeline.schemas.schema import Config
from pipeline.types import Result
from pydantic import BaseModel, Field


class Speech(BaseModel):
    speechnum: int
    speaker: str
    text: str


class BundestagProtocol(BaseModel):
    title: str
    speeches: List[Speech]


class TopicForRequest(BaseModel):
    topic: str


class StanceResult(BaseModel):
    stance: float = Field(..., description="Value in [-1, 1]")
    explanation: str


class ClassifiedSpeech(BaseModel):
    id: int
    speaker: str
    topics: list[str]
    text: str


class SentimentClassifiedSpeech(ClassifiedSpeech):
    sentiment: list[StanceResult]


class SpeechSplitterConfig(Config):
    chunk_size: int = 1000
    chunk_overlap: int = 200


class TopicEmbedderConfig(Config):
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"


class ClusterTopicsConfig(Config):
    eps: float = (0.3,)
    min_samples: int = 1


class FormatterConfig(Config):
    formatter_function: Callable[[Any], Result[Any, Any]] | Callable[[Any, Any], Result[Any, Any]]
    store_key: Optional[str] = None
