from typing import Any

from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances
from pipeline.pipeline.step import Step
from pipeline.types.result import Result, Ok
from pipeline.schemas.schema import PipelineModuleConfig, PipelineResponse

from app.schema.schema import ClusterTopicsConfig


class ClusterTopics(Step):
    def __init__(self, *, config: ClusterTopicsConfig):
        self.config = config


    async def run(self, input_data: Result[dict, Any], pipeline_config: PipelineModuleConfig) -> PipelineResponse:
        if input_data.is_err():
            return await pipeline_config.next(input_data, pipeline_config)

        speech = input_data.unwrap()
        embeddings = speech["embeddings"].cpu().numpy()
        cosine_dist = cosine_distances(embeddings)
        labels = DBSCAN(eps=self.config.eps, min_samples=self.config.min_samples, metric="precomputed").fit(cosine_dist).labels_

        return await pipeline_config.next(Ok({**speech, "labels": labels}), pipeline_config)
