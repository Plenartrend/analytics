from typing import Any

from pipeline.pipeline.step import Step
from pipeline.schemas.schema import PipelineModuleConfig, PipelineResponse
from pipeline.types.result import Ok, Result
from sentence_transformers import SentenceTransformer

from app.schema.schema import TopicEmbedderConfig


class TopicEmbedder(Step):
    def __init__(self, *, config: TopicEmbedderConfig):
        self.config = config

    async def run(self, input_data: Result[dict, Any], pipeline_config: PipelineModuleConfig) -> PipelineResponse:
        if input_data.is_err():
            return await pipeline_config.next(input_data, pipeline_config)

        speech = input_data.unwrap()
        topics = speech["topics"]
        embeddings = SentenceTransformer(self.config.embedding_model_name).encode(topics, convert_to_tensor=True)

        return await pipeline_config.next(Ok({**speech, "embeddings": embeddings}), pipeline_config)
