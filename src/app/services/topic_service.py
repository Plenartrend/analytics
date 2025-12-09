from collections import defaultdict
from typing import Any

from pipeline.pipeline import Pipeline, SubPipeline
from pipeline.schemas.schema import PipelineConfig
from pipeline.types import Err, Ok, Result

from app.modules.cluster_representative_picker import ClusterRepresentativePicker
from app.modules.cluster_topics import ClusterTopics
from app.modules.formatter import Formatter
from app.modules.speech_splitter import SpeechSplitter
from app.modules.topic_embedder import TopicEmbedder
from app.modules.topic_extractor import TopicExtractor
from app.schema.schema import (
    ClassifiedSpeech,
    ClusterTopicsConfig,
    FormatterConfig,
    Speech,
    SpeechSplitterConfig,
    TopicEmbedderConfig,
)


async def run_topic_analysis_pipeline(text: list[Speech]):
    def formatter(speeches: list[Result[dict, Any]]):
        all_topics = []
        speech_topic_map = []

        unpacked = []
        for el in speeches:
            if el.is_ok():
                unpacked.append(el.unwrap())
            else:
                return Err("Error in subpipeline execution")

        for idx, sp in enumerate(unpacked):
            for t in sp["topics"]:
                all_topics.append(t)
                speech_topic_map.append((idx, t))

        return Ok({"speeches": unpacked, "topics": all_topics, "speech_map": speech_topic_map})

    def formatter_final(speeches):
        speech_global_topics = defaultdict(set)
        for (speech_idx, topic), label in zip(speeches["speech_map"], speeches["labels"]):
            representative = speeches["cluster_reps"][label]
            speech_global_topics[speech_idx].add(representative)

        global_speeches = []
        for idx in range(0, len(speeches["speeches"])):
            global_speeches.append(list(speech_global_topics[idx]))

        speeches_to_pydantic = []
        for idx, speech in enumerate(speeches["speeches"]):
            speeches_to_pydantic.append(
                ClassifiedSpeech(
                    id=speech["speechnum"], speaker=speech["speaker"], topics=global_speeches[idx], text=speech["text"]
                )
            )

        return Ok(speeches_to_pydantic)

    pipeline = (
        Pipeline.init(
            input_data=[a.model_dump() for a in text], pipeline_config=PipelineConfig(name="Topic Analysis Pipeline")
        )
        .parallel(
            SubPipeline.init()
            .exec(SpeechSplitter(config=SpeechSplitterConfig()))
            .exec(TopicExtractor(config=None))
            .exec(
                TopicEmbedder(config=TopicEmbedderConfig(embedding_model_name="sentence-transformers/all-MiniLM-L6-v2"))
            )
            .exec(ClusterTopics(config=ClusterTopicsConfig(eps=0.25, min_samples=1)))
            .exec(ClusterRepresentativePicker(config=None))
        )
        .exec(Formatter(config=FormatterConfig(formatter_function=formatter)))
        .exec(TopicEmbedder(config=TopicEmbedderConfig(embedding_model_name="sentence-transformers/all-MiniLM-L6-v2")))
        .exec(ClusterTopics(config=ClusterTopicsConfig(eps=0.25, min_samples=1)))
        .exec(ClusterRepresentativePicker(config=None))
        .exec(Formatter(config=FormatterConfig(formatter_function=formatter_final)))
        .compile()
    )

    return (await pipeline).unwrap()
