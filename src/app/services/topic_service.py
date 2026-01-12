from pipeline.pipeline import Pipeline
from pipeline.schemas.schema import PipelineConfig
from pipeline.types import Ok

from app.modules.cluster_representative_picker import ClusterRepresentativePicker
from app.modules.cluster_topics import ClusterTopics
from app.modules.cluster_topics_global import ClusterTopicsGlobal
from app.modules.formatter import Formatter
from app.modules.speech_splitter import SpeechSplitter
from app.modules.topic_embedder import TopicEmbedder
from app.modules.topic_extractor import TopicExtractor
from app.schema.schema import (
    ClassifiedSpeech,
    ClusterTopicsConfig,
    FormatterConfig,
    SpeechSplitterConfig,
    Topic,
    TopicEmbedderConfig,
)
from app.utils.db import get_db


async def run_topic_analysis_pipeline(id: int, text: str):
    def formatter_final(speech):
        topics = []

        for topic in speech["cluster_topics"]:
            topics.append(Topic(id=topic["topic_id"], name=topic["name"], embedding=topic["embedding"]))

        speeches_to_pydantic = ClassifiedSpeech(id=id, topics=topics, text=text)

        return Ok(speeches_to_pydantic)

    async with get_db() as session:
        pipeline = (
            Pipeline.init(input_data={"text": text}, pipeline_config=PipelineConfig(name="Topic Analysis Pipeline"))
            .exec(SpeechSplitter(config=SpeechSplitterConfig()))
            .exec(TopicExtractor(config=None))
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

    return (await pipeline).unwrap()
