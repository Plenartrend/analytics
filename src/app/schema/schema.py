import datetime
from typing import Any, AsyncGenerator, Awaitable, Callable, Optional

from pipeline.schemas.schema import Config
from pipeline.types import Result
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession


class Speech(BaseModel):
    speechnum: int
    speaker: str
    text: str


class PrintedPaper(BaseModel):
    id: int
    activity_ids: list[int]
    title: str
    text: str


class BundestagProtocol(BaseModel):
    id: int
    speech: str
    person_id: int
    protocol_id: int
    speech_date: datetime.datetime


class TopicForRequest(BaseModel):
    topic: str


class StanceResult(BaseModel):
    stance: float = Field(..., description="Value in [-1, 1]")
    explanation: str


class Topic(BaseModel):
    id: int
    name: str
    embedding: Any


class ClassifiedSpeech(BaseModel):
    id: int
    topics: list[Topic]
    text: str


class SentimentClassifiedSpeech(ClassifiedSpeech):
    sentiment: list[StanceResult]


class SpeechSplitterConfig(Config):
    chunk_size: int = 1000
    chunk_overlap: int = 200


class TopicExtractorConfig(Config):
    inject_topics: Optional[list[str]] = None


class TopicEmbedderConfig(Config):
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    persist_embeddings_global: bool = False


class ClusterTopicsConfig(Config):
    eps: float = (0.3,)
    min_samples: int = 1
    commit: bool = True


class FormatterConfig(Config):
    formatter_function: Callable[[Any], Result[Any, Any]] | Callable[[Any, Any], Result[Any, Any]]
    store_key: Optional[str] = None


class State(BaseModel):
    db_session: Callable[[], AsyncGenerator[AsyncSession, None]]
    distributed_key_function: Optional[Callable[[Any], Awaitable[int]]]
