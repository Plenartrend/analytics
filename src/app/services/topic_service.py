from typing import Optional

from pipeline.pipeline import Pipeline
from pipeline.schemas.schema import PipelineConfig
from pipeline.types import Ok
from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from ..modules.cluster_representative_picker import ClusterRepresentativePicker
from ..modules.cluster_topics import ClusterTopics
from ..modules.cluster_topics_global import ClusterTopicsGlobal
from ..modules.formatter import Formatter
from ..modules.speech_splitter import SpeechSplitter
from ..modules.topic_embedder import TopicEmbedder
from ..modules.topic_extractor import TopicExtractor
from ..schema.schema import (
    ClassifiedSpeech,
    ClusterTopicsConfig,
    FormatterConfig,
    SpeechSplitterConfig,
    Topic,
    TopicEmbedderConfig,
    TopicExtractorConfig,
)
from ..utils.db import get_db


async def run_topic_analysis_protocol_pipeline(id: int, text: str, transaction: AsyncSession = None):
    def formatter_final(speech):
        topics = []

        for topic in speech["cluster_topics"]:
            topics.append(Topic(id=topic["topic_id"], name=topic["name"], embedding=topic["embedding"]))

        speeches_to_pydantic = ClassifiedSpeech(id=id, topics=topics, text=text)

        return Ok(speeches_to_pydantic)

    async with get_db() as session:
        if transaction:
            session = transaction

        pipeline = (
            Pipeline.init(
                input_data={"text": text}, pipeline_config=PipelineConfig(name="Protocol Topic Analysis Pipeline")
            )
            .exec(SpeechSplitter(config=SpeechSplitterConfig()))
            .exec(TopicExtractor(config=TopicExtractorConfig()))
            .exec(
                TopicEmbedder(config=TopicEmbedderConfig(embedding_model_name="sentence-transformers/all-MiniLM-L6-v2"))
            )
            .exec(ClusterTopics(config=ClusterTopicsConfig(eps=0.25, min_samples=1)))
            .exec(ClusterRepresentativePicker(config=None))
            .exec(
                TopicEmbedder(config=TopicEmbedderConfig(embedding_model_name="sentence-transformers/all-MiniLM-L6-v2"))
            )
            .exec(ClusterTopicsGlobal(config=ClusterTopicsConfig(eps=0.25, min_samples=1), session=session))
            .exec(Formatter(config=FormatterConfig(formatter_function=formatter_final)))
            .compile()
        )

        if not transaction:
            await session.commit()

    return (await pipeline).unwrap()


async def run_topic_analysis_printed_paper_pipeline(
    id: int, title: str, text: str, transaction: Optional[AsyncSessionTransaction] = None
):
    def formatter_final(speech):
        topics = []

        for topic in speech["cluster_topics"]:
            topics.append(Topic(id=topic["topic_id"], name=topic["name"], embedding=topic["embedding"]))

        speeches_to_pydantic = ClassifiedSpeech(id=id, topics=topics, text=text)

        return Ok(speeches_to_pydantic)

    async with get_db() as session:
        if transaction:
            session = transaction

        pipeline = (
            Pipeline.init(
                input_data={"text": text}, pipeline_config=PipelineConfig(name="Printed Paper Topic Analysis Pipeline")
            )
            .exec(SpeechSplitter(config=SpeechSplitterConfig(chunk_size=10000, chunk_overlap=200)))
            .exec(TopicExtractor(config=TopicExtractorConfig(inject_topics=[title])))
            .exec(
                TopicEmbedder(config=TopicEmbedderConfig(embedding_model_name="sentence-transformers/all-MiniLM-L6-v2"))
            )
            .exec(ClusterTopics(config=ClusterTopicsConfig(eps=0.5, min_samples=1)))
            .exec(ClusterRepresentativePicker(config=None))
            .exec(
                TopicEmbedder(config=TopicEmbedderConfig(embedding_model_name="sentence-transformers/all-MiniLM-L6-v2"))
            )
            .exec(ClusterTopicsGlobal(config=ClusterTopicsConfig(eps=0.5, min_samples=1), session=session))
            .exec(Formatter(config=FormatterConfig(formatter_function=formatter_final)))
            .compile()
        )

        if not transaction:
            await session.commit()

    return (await pipeline).unwrap()
